import pytest
from plumage.crypto import encrypt, decrypt
from plumage.utils import get_shuffled_indices, rebuild_image_from_pixels
from PIL import Image
import numpy as np

def test_crypto_roundtrip():
    passphrase = "testpassword"
    data = b"Hello, World!"
    encrypted = encrypt(data, passphrase)
    decrypted = decrypt(encrypted, passphrase)
    assert decrypted == data

def test_crypto_invalid_passphrase():
    passphrase = "correctpassword"
    wrong_passphrase = "wrongpassword"
    data = b"Sensitive information"
    encrypted = encrypt(data, passphrase)
    with pytest.raises(ValueError):
        decrypt(encrypted, wrong_passphrase)

def test_shuffled_indices_deterministic():
    size = 100
    passphrase = "secret"
    indices1 = get_shuffled_indices(size, passphrase)
    indices2 = get_shuffled_indices(size, passphrase)
    assert indices1 == indices2
    assert len(set(indices1)) == size

def test_shuffled_indices_different_passphrases():
    size = 100
    indices1 = get_shuffled_indices(size, "pass1")
    indices2 = get_shuffled_indices(size, "pass2")
    assert indices1 != indices2

def test_rebuild_image_removes_metadata():
    # Create an image with some metadata
    img = Image.new('RGB', (10, 10), color='red')
    img.info['test_meta'] = 'should be gone'

    clean_img = rebuild_image_from_pixels(img)
    assert 'test_meta' not in clean_img.info
    assert clean_img.size == img.size
    assert clean_img.mode == img.mode
    assert list(clean_img.getdata()) == list(img.getdata())
