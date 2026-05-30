import numpy as np
from PIL import Image
from plumage.utils import get_shuffled_indices
from plumage.crypto import encrypt, decrypt

def bytes_to_bits(data: bytes) -> list[int]:
    result = []
    for byte in data:
        for shift in range(7, -1, -1):
            result.append((byte >> shift) & 1)
    return result

def bits_to_bytes(bits: list[int]) -> bytes:
    result = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i:i+8]:
            byte = (byte << 1) | bit
        result.append(byte)
    return bytes(result)

def embed_lsb_image(img: Image.Image, payload: bytes, passphrase: str) -> Image.Image:
    """
    Embeds payload into the LSB of image pixels using a PRNG shuffle.
    """
    # Payload format: [4 bytes length] + [encrypted data]
    # We encrypt the whole thing including a magic marker maybe?
    # Actually, we already have a robust encrypted bundle from crypto.py

    encrypted_payload = encrypt(payload, passphrase)
    payload_len = len(encrypted_payload)
    # 4 bytes for length (32 bits) + the payload itself
    full_payload = payload_len.to_bytes(4, byteorder='big') + encrypted_payload
    bits = bytes_to_bits(full_payload)

    pixels = np.array(img)
    flat_pixels = pixels.flatten()

    if len(bits) > len(flat_pixels):
        raise ValueError(f"Payload too large for carrier. Payload: {len(bits)} bits, Carrier: {len(flat_pixels)} bits.")

    indices = get_shuffled_indices(len(flat_pixels), passphrase)

    for i, bit in enumerate(bits):
        idx = indices[i]
        flat_pixels[idx] = (flat_pixels[idx] & 0xFE) | bit

    new_pixels = flat_pixels.reshape(pixels.shape)
    return Image.fromarray(new_pixels.astype('uint8'), img.mode)

def extract_lsb_image(img: Image.Image, passphrase: str) -> bytes:
    """
    Extracts payload from the LSB of image pixels using a PRNG shuffle.
    """
    pixels = np.array(img)
    flat_pixels = pixels.flatten()
    indices = get_shuffled_indices(len(flat_pixels), passphrase)

    # 1. Extract the length (32 bits)
    len_bits = []
    for i in range(32):
        idx = indices[i]
        len_bits.append(flat_pixels[idx] & 1)

    payload_len = 0
    for bit in len_bits:
        payload_len = (payload_len << 1) | bit

    # Safety check
    max_possible = (len(flat_pixels) - 32) // 8
    if not (0 < payload_len <= max_possible):
        raise ValueError("Extracted length is invalid. Likely wrong passphrase.")

    # 2. Extract the encrypted payload
    payload_bits = []
    for i in range(32, 32 + (payload_len * 8)):
        idx = indices[i]
        payload_bits.append(flat_pixels[idx] & 1)

    encrypted_payload = bits_to_bytes(payload_bits)
    return decrypt(encrypted_payload, passphrase)
