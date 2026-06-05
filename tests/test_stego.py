import pytest
from PIL import Image
import numpy as np
import io
from plumage.stego.lsb import embed_lsb_image, extract_lsb_image
from plumage.stego.dct import embed_dct_image, extract_dct_image

def test_lsb_image_roundtrip_png():
    passphrase = "password"
    payload = b"Hidden Message"
    img = Image.new('RGB', (100, 100), color=(127, 127, 127))

    stego_img = embed_lsb_image(img, payload, passphrase)

    # Simulate saving and loading (lossless)
    buf = io.BytesIO()
    stego_img.save(buf, format='PNG')
    buf.seek(0)
    loaded_stego = Image.open(buf)

    extracted = extract_lsb_image(loaded_stego, passphrase)
    assert extracted == payload

def test_lsb_image_roundtrip_bmp():
    passphrase = "password"
    payload = b"Hidden BMP"
    img = Image.new('RGB', (50, 50), color=(10, 20, 30))

    stego_img = embed_lsb_image(img, payload, passphrase)

    buf = io.BytesIO()
    stego_img.save(buf, format='BMP')
    buf.seek(0)
    loaded_stego = Image.open(buf)

    extracted = extract_lsb_image(loaded_stego, passphrase)
    assert extracted == payload

def test_dct_image_roundtrip_jpg():
    passphrase = "password"
    payload = b"DCT payload"
    # DCT requires at least 8x8 blocks, let's use a larger image to be safe
    img = Image.new('RGB', (200, 200), color=(100, 150, 200))

    stego_img = embed_dct_image(img, payload, passphrase)

    # Save as JPEG with high quality as recommended
    buf = io.BytesIO()
    stego_img.save(buf, format='JPEG', quality=100, subsampling=0)
    buf.seek(0)
    loaded_stego = Image.open(buf)

    extracted = extract_dct_image(loaded_stego, passphrase)
    assert extracted == payload

def test_lsb_image_capacity_error():
    passphrase = "p"
    img = Image.new('RGB', (2, 2)) # 4 pixels * 3 channels = 12 bits capacity
    payload = b"Too long payload for 12 bits"
    with pytest.raises(ValueError, match="Payload too large"):
        embed_lsb_image(img, payload, passphrase)
