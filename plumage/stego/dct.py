import numpy as np
from PIL import Image
import scipy.fftpack as fft
from plumage.crypto import encrypt, decrypt
from plumage.stego.lsb import bytes_to_bits, bits_to_bytes
from plumage.utils import get_shuffled_indices

# For simplicity and robustness in this CLI tool, we'll implement a
# DCT-based LSB embedding on the Y (luminance) channel.
# This is more resilient to JPEG compression than simple LSB.

def embed_dct_image(img: Image.Image, payload: bytes, passphrase: str) -> Image.Image:
    """
    Hides data in the DCT coefficients of the luminance channel.
    """
    encrypted_payload = encrypt(payload, passphrase)
    payload_len = len(encrypted_payload)
    full_payload = payload_len.to_bytes(4, byteorder='big') + encrypted_payload
    bits = bytes_to_bits(full_payload)

    # Convert to YCbCr
    img_ycbcr = img.convert('YCbCr')
    y, cb, cr = img_ycbcr.split()
    y_data = np.array(y).astype(np.float32)

    h, w = y_data.shape
    # Force alignment to 8x8 blocks
    y_data = y_data[:(h // 8) * 8, :(w // 8) * 8]
    h, w = y_data.shape

    # Number of 8x8 blocks
    num_blocks_h = h // 8
    num_blocks_w = w // 8
    total_blocks = num_blocks_h * num_blocks_w

    if len(bits) > total_blocks:
         raise ValueError("Payload too large for DCT embedding in this image.")

    indices = get_shuffled_indices(total_blocks, passphrase)

    bit_idx = 0
    for b_idx in indices:
        if bit_idx >= len(bits):
            break

        row = (b_idx // num_blocks_w) * 8
        col = (b_idx % num_blocks_w) * 8

        block = y_data[row:row+8, col:col+8]
        dct_block = fft.dct(fft.dct(block.T, norm='ortho').T, norm='ortho')

        bit = int(bits[bit_idx])

        if bit == 1:
            dct_block[1, 1] = 300.0
        else:
            dct_block[1, 1] = -300.0

        y_data[row:row+8, col:col+8] = fft.idct(fft.idct(dct_block.T, norm='ortho').T, norm='ortho')
        bit_idx += 1

    y_final = Image.fromarray(np.clip(y_data, 0, 255).astype(np.uint8))
    return Image.merge('YCbCr', (y_final, cb, cr)).convert('RGB')

def extract_dct_image(img: Image.Image, passphrase: str) -> bytes:
    img_ycbcr = img.convert('YCbCr')
    y, _, _ = img_ycbcr.split()
    y_data = np.array(y).astype(np.float32)

    h, w = y_data.shape
    # Force alignment to 8x8 blocks
    y_data = y_data[:(h // 8) * 8, :(w // 8) * 8]
    h, w = y_data.shape

    num_blocks_h = h // 8
    num_blocks_w = w // 8
    total_blocks = num_blocks_h * num_blocks_w

    indices = get_shuffled_indices(total_blocks, passphrase)

    # We first need to find the length. 32 bits = 32 blocks.
    len_bits = ""
    for i in range(32):
        b_idx = indices[i]
        row = (b_idx // num_blocks_w) * 8
        col = (b_idx % num_blocks_w) * 8
        block = y_data[row:row+8, col:col+8]
        dct_block = fft.dct(fft.dct(block.T, norm='ortho').T, norm='ortho')

        val = dct_block[1, 1]
        if val > 50:
             len_bits += "1"
        elif val < -50:
             len_bits += "0"
        else:
             len_bits += "1" if val >= 0 else "0"

    payload_len = int(len_bits, 2)

    if payload_len > (total_blocks - 32) // 8 or payload_len < 0:
        raise ValueError("Invalid DCT payload length. Wrong passphrase or image corrupted.")

    payload_bits = ""
    for i in range(32, 32 + (payload_len * 8)):
        b_idx = indices[i]
        row = (b_idx // num_blocks_w) * 8
        col = (b_idx % num_blocks_w) * 8
        block = y_data[row:row+8, col:col+8]
        dct_block = fft.dct(fft.dct(block.T, norm='ortho').T, norm='ortho')

        val = dct_block[1, 1]
        if val > 50:
             payload_bits += "1"
        elif val < -50:
             payload_bits += "0"
        else:
             payload_bits += "1" if val >= 0 else "0"

    encrypted_payload = bits_to_bytes(payload_bits)
    return decrypt(encrypted_payload, passphrase)
