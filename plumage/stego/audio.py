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
    if audio.sample_width not in (1, 2):
        raise ValueError(f"Unsupported sample width: {audio.sample_width} bytes. Only 8-bit and 16-bit audio is supported.")

    encrypted_payload = encrypt(payload, passphrase)
    payload_len = len(encrypted_payload)
    full_payload = payload_len.to_bytes(4, byteorder='big') + encrypted_payload
    bits = bytes_to_bits(full_payload)

    samples = np.array(audio.get_array_of_samples())

    if len(bits) > len(samples):
        raise ValueError(f"Payload too large for carrier. Payload: {len(bits)} bits, Carrier: {len(samples)} samples.")

    indices = get_shuffled_indices(len(samples), passphrase)

    # Audio samples can be signed, but Python's integer model handles it.
    # Numpy's assignment will handle truncation to the original dtype.
    for i, bit in enumerate(bits):
        idx = indices[i]
        val = samples[idx]
        samples[idx] = (val & ~1) | bit

    new_audio = AudioSegment(
        data=samples.tobytes(),
        sample_width=audio.sample_width,
        frame_rate=audio.frame_rate,
        channels=audio.channels,
    )
    return new_audio

def extract_lsb_audio(audio: AudioSegment, passphrase: str) -> bytes:
    """
    Extracts payload from the LSB of audio samples using a PRNG shuffle.
    """
    if audio.sample_width not in (1, 2):
        raise ValueError(f"Unsupported sample width: {audio.sample_width} bytes. Only 8-bit and 16-bit audio is supported.")

    samples = np.array(audio.get_array_of_samples())
    indices = get_shuffled_indices(len(samples), passphrase)

    # 1. Extract length
    len_bits = []
    for i in range(32):
        idx = indices[i]
        len_bits.append(samples[idx] & 1)

    payload_len = 0
    for bit in len_bits:
        payload_len = (payload_len << 1) | int(bit)

    max_possible = (len(samples) - 32) // 8
    if not (0 < payload_len <= max_possible):
        raise ValueError("Extracted length is invalid. Likely wrong passphrase.")

    # 2. Extract encrypted payload
    payload_bits = []
    for i in range(32, 32 + (payload_len * 8)):
        idx = indices[i]
        payload_bits.append(samples[idx] & 1)

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
