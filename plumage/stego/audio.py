import numpy as np
from pydub import AudioSegment
from plumage.utils import get_shuffled_indices
from plumage.crypto import encrypt, decrypt
from plumage.stego.lsb import bytes_to_bits, bits_to_bytes
import io

def embed_lsb_audio(audio: AudioSegment, payload: bytes, passphrase: str) -> AudioSegment:
    """
    Embeds payload into the LSB of audio samples using a PRNG shuffle.
    Works for WAV.
    """
    encrypted_payload = encrypt(payload, passphrase)
    payload_len = len(encrypted_payload)
    full_payload = payload_len.to_bytes(4, byteorder='big') + encrypted_payload
    bits = bytes_to_bits(full_payload)

    samples = np.array(audio.get_array_of_samples())

    if len(bits) > len(samples):
        raise ValueError(f"Payload too large for carrier. Payload: {len(bits)} bits, Carrier: {len(samples)} samples.")

    indices = get_shuffled_indices(len(samples), passphrase)

    # Audio samples can be signed, so we need to be careful with bitwise ops
    for i, bit in enumerate(bits):
        idx = indices[i]
        # Clear LSB and set it to bit
        val = int(samples[idx])
        # For signed 16-bit, we need to handle negative values correctly for LSB
        if val < 0:
             new_val = (val & ~1) | int(bit)
             # Map back to signed 16-bit range if needed
             if new_val > 32767: new_val -= 65536
        else:
             new_val = (val & ~1) | int(bit)

        samples[idx] = new_val

    new_audio = audio._spawn(samples.tobytes())
    return new_audio

def extract_lsb_audio(audio: AudioSegment, passphrase: str) -> bytes:
    """
    Extracts payload from the LSB of audio samples using a PRNG shuffle.
    """
    samples = np.array(audio.get_array_of_samples())
    indices = get_shuffled_indices(len(samples), passphrase)

    # 1. Extract length
    len_bits = ""
    for i in range(32):
        idx = indices[i]
        len_bits += str(int(samples[idx]) & 1)

    payload_len = int(len_bits, 2)

    if payload_len > (len(samples) - 32) // 8 or payload_len < 0:
        raise ValueError("Extracted length is impossibly large. Likely wrong passphrase.")

    # 2. Extract encrypted payload
    payload_bits = ""
    for i in range(32, 32 + (payload_len * 8)):
        idx = indices[i]
        payload_bits += str(int(samples[idx]) & 1)

    encrypted_payload = bits_to_bytes(payload_bits)
    return decrypt(encrypted_payload, passphrase)

def embed_lsb_mp3(audio: AudioSegment, payload: bytes, passphrase: str) -> AudioSegment:
    """
    For MP3, we use LSB on the raw samples.
    Extraction is only reliable if the resulting MP3 is very high bitrate.
    """
    return embed_lsb_audio(audio, payload, passphrase)

def extract_lsb_mp3(audio: AudioSegment, passphrase: str) -> bytes:
    return extract_lsb_audio(audio, passphrase)
