import hashlib
import random
from typing import List
from PIL import Image

def get_shuffled_indices(size: int, passphrase: str) -> List[int]:
    """
    Generates a deterministic shuffled list of indices based on a passphrase.
    Uses a 32-bit LCG to ensure consistency with PowerShell and avoid overflow issues.
    """
    indices = list(range(size))

    # Get a 32-bit seed from the passphrase
    seed_hash = hashlib.sha256(passphrase.encode()).digest()
    state = int.from_bytes(seed_hash[:4], byteorder='little')

    def lcg_next():
        nonlocal state
        # Standard LCG parameters (numerical recipes)
        # Using 32-bit arithmetic to avoid PowerShell issues
        a = 1664525
        c = 1013904223
        state = (a * state + c) & 0xFFFFFFFF
        return state

    for i in range(size - 1, 0, -1):
        r = lcg_next() % (i + 1)
        indices[i], indices[r] = indices[r], indices[i]

    return indices

def rebuild_image_from_pixels(image: Image.Image) -> Image.Image:
    """
    Rebuilds an image from raw pixel data to guarantee no metadata survives.
    """
    data = list(image.getdata())
    clean = Image.new(image.mode, image.size)
    clean.putdata(data)
    return clean
