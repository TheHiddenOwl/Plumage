import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# AES-256-CBC configuration for PowerShell 5.1 compatibility
KEY_SIZE = 32  # 256 bits
BLOCK_SIZE = 16 # 128 bits
SALT_SIZE = 16
ITERATIONS = 100000

def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derives a 256-bit key from a passphrase and salt using PBKDF2."""
    if not passphrase:
        raise ValueError("Passphrase must not be empty.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=ITERATIONS
    )
    return kdf.derive(passphrase.encode())

def encrypt(data: bytes, passphrase: str) -> bytes:
    """Encrypts data using AES-256-CBC with PKCS7 padding."""
    salt = os.urandom(SALT_SIZE)
    key = derive_key(passphrase, salt)
    iv = os.urandom(BLOCK_SIZE)

    # Padding
    padder = padding.PKCS7(BLOCK_SIZE * 8).padder()
    padded_data = padder.update(data) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # Return concatenation: salt (16) + iv (16) + ciphertext
    return salt + iv + ciphertext

def decrypt(encrypted_bundle: bytes, passphrase: str) -> bytes:
    """Decrypts data using AES-256-CBC."""
    if len(encrypted_bundle) < SALT_SIZE + BLOCK_SIZE:
        raise ValueError("Encrypted data is too short.")

    salt = encrypted_bundle[:SALT_SIZE]
    iv = encrypted_bundle[SALT_SIZE:SALT_SIZE + BLOCK_SIZE]
    ciphertext = encrypted_bundle[SALT_SIZE + BLOCK_SIZE:]

    key = derive_key(passphrase, salt)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ciphertext) + decryptor.finalize()

    # Unpadding
    unpadder = padding.PKCS7(BLOCK_SIZE * 8).unpadder()
    try:
        data = unpadder.update(padded_data) + unpadder.finalize()
    except ValueError:
        raise ValueError("Invalid passphrase or corrupted data (padding error).")

    return data
