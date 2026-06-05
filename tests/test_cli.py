import os
import subprocess
import pytest
from PIL import Image

def test_cli_lsb_png():
    carrier = "test_carrier.png"
    payload = "test_payload.txt"
    stego = "test_stego.png"
    recovered = "test_recovered.txt"
    passphrase = "mysecretpassword"

    # Create carrier
    img = Image.new('RGB', (100, 100), color='blue')
    img.save(carrier)

    # Create payload
    with open(payload, 'w') as f:
        f.write("This is a secret message.")

    try:
        # Embed
        subprocess.run([
            "python3", "plumage.py", "embed",
            "-i", carrier,
            "-p", payload,
            "-o", stego,
            "-pass", passphrase
        ], check=True)

        assert os.path.exists(stego)

        # Extract
        subprocess.run([
            "python3", "plumage.py", "extract",
            "-i", stego,
            "-o", recovered,
            "-pass", passphrase
        ], check=True)

        assert os.path.exists(recovered)
        with open(recovered, 'r') as f:
            assert f.read() == "This is a secret message."

    finally:
        # Cleanup
        for f in [carrier, payload, stego, recovered]:
            if os.path.exists(f):
                os.remove(f)

def test_cli_dct_to_png():
    # DCT embedding but saving as PNG (as required by CLI logic)
    carrier = "test_carrier_jpg.jpg"
    payload = "test_payload.txt"
    stego = "test_stego_from_dct.png"
    recovered = "test_recovered_dct.txt"
    passphrase = "dctpassword"

    img = Image.new('RGB', (200, 200), color='green')
    img.save(carrier)

    with open(payload, 'w') as f:
        f.write("DCT hidden data")

    try:
        # Embed using DCT
        subprocess.run([
            "python3", "plumage.py", "embed",
            "-i", carrier,
            "-p", payload,
            "-o", stego,
            "-pass", passphrase,
            "-m", "dct"
        ], check=True)

        # Extract
        subprocess.run([
            "python3", "plumage.py", "extract",
            "-i", stego,
            "-o", recovered,
            "-pass", passphrase
        ], check=True)

        with open(recovered, 'r') as f:
            assert f.read() == "DCT hidden data"

    finally:
        for f in [carrier, payload, stego, recovered]:
            if os.path.exists(f):
                os.remove(f)

def test_cli_ps1_generation():
    carrier = "test_carrier.png"
    payload = "test_payload.txt"
    stego = "test_stego_ps1.png"
    ps1_script = stego + ".extract.ps1"
    passphrase = "ps1password"

    img = Image.new('RGB', (100, 100), color='red')
    img.save(carrier)

    with open(payload, 'w') as f:
        f.write("PS1 test")

    try:
        subprocess.run([
            "python3", "plumage.py", "embed",
            "-i", carrier,
            "-p", payload,
            "-o", stego,
            "-pass", passphrase,
            "--ps1"
        ], check=True)

        assert os.path.exists(ps1_script)
        with open(ps1_script, 'r') as f:
            content = f.read()
            assert "$Passphrase" in content
            assert "AES" in content

    finally:
        for f in [carrier, payload, stego, ps1_script]:
            if os.path.exists(f):
                os.remove(f)
