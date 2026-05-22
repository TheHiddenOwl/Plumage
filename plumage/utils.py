import hashlib
import random
from typing import List

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

def strip_metadata_image(image):
    """
    Strips metadata from a PIL Image object.
    """
    image_without_exif = image.copy()
    image_without_exif.info = {}
    return image_without_exif
