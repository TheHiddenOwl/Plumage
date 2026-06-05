import numpy as np
from PIL import Image
from scipy.fft import dct, idct
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

    w, h = y.size
    # Force alignment to 8x8 blocks
    w_aligned = (w // 8) * 8
    h_aligned = (h // 8) * 8

    y = y.crop((0, 0, w_aligned, h_aligned))
    cb = cb.crop((0, 0, w_aligned, h_aligned))
    cr = cr.crop((0, 0, w_aligned, h_aligned))

    y_data = np.array(y).astype(np.float32)
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
        dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')

        bit = int(bits[bit_idx])

        # Use QIM (Quantization Index Modulation) for better robustness and less artifacts
        q_step = 20.0
        val = dct_block[1, 1]
        n = np.floor(val / q_step)

        if bit == 1:
            if n % 2 == 0:
                new_val = (n + 1) * q_step + q_step / 2
            else:
                new_val = n * q_step + q_step / 2
        else:
            if n % 2 == 0:
                new_val = n * q_step + q_step / 2
            else:
                new_val = (n - 1) * q_step + q_step / 2

        dct_block[1, 1] = new_val

        y_data[row:row+8, col:col+8] = idct(idct(dct_block.T, norm='ortho').T, norm='ortho')
        bit_idx += 1

    y_final = Image.fromarray(np.clip(y_data, 0, 255).astype(np.uint8))
    return Image.merge('YCbCr', (y_final, cb, cr)).convert('RGB')

def extract_dct_image(img: Image.Image, passphrase: str) -> bytes:
    img_ycbcr = img.convert('YCbCr')
    y, _, _ = img_ycbcr.split()

    w, h = y.size
    w_aligned = (w // 8) * 8
    h_aligned = (h // 8) * 8
    y = y.crop((0, 0, w_aligned, h_aligned))

    y_data = np.array(y).astype(np.float32)
    h, w = y_data.shape

    num_blocks_h = h // 8
    num_blocks_w = w // 8
    total_blocks = num_blocks_h * num_blocks_w

    indices = get_shuffled_indices(total_blocks, passphrase)

    # We first need to find the length. 32 bits = 32 blocks.
    len_bits = []
    for i in range(32):
        b_idx = indices[i]
        row = (b_idx // num_blocks_w) * 8
        col = (b_idx % num_blocks_w) * 8
        block = y_data[row:row+8, col:col+8]
        dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')

        val = dct_block[1, 1]
        q_step = 20.0

        # Check for ambiguity
        dist_from_center = abs(val % q_step - q_step / 2)
        if dist_from_center > q_step * 0.4:
            raise ValueError(
                f"Ambiguous DCT coefficient ({val:.1f}) at block {b_idx}. "
                "Image may be corrupted or wrong passphrase."
            )

        n = np.floor(val / q_step)
        bit = int(n % 2)
        len_bits.append(bit)

    payload_len = 0
    for bit in len_bits:
        payload_len = (payload_len << 1) | bit

    if payload_len > (total_blocks - 32) // 8 or payload_len < 0:
        raise ValueError("Invalid DCT payload length. Wrong passphrase or image corrupted.")

    payload_bits = []
    for i in range(32, 32 + (payload_len * 8)):
        b_idx = indices[i]
        row = (b_idx // num_blocks_w) * 8
        col = (b_idx % num_blocks_w) * 8
        block = y_data[row:row+8, col:col+8]
        dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')

        val = dct_block[1, 1]
        q_step = 20.0

        # Check for ambiguity
        dist_from_center = abs(val % q_step - q_step / 2)
        if dist_from_center > q_step * 0.4:
            raise ValueError(
                f"Ambiguous DCT coefficient ({val:.1f}) at block {b_idx}. "
                "Image may be corrupted or wrong passphrase."
            )

        n = np.floor(val / q_step)
        bit = int(n % 2)
        payload_bits.append(bit)

    encrypted_payload = bits_to_bytes(payload_bits)
    return decrypt(encrypted_payload, passphrase)
