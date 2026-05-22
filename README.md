# Plumage

Plumage is an advanced steganography CLI tool designed to embed encrypted payloads or sensitive logs within standard image and audio files. It is specifically built to bypass deep packet inspection (DPI) and provide "living off the land" extraction capabilities on Windows systems.

## Key Features

- **Advanced Stealth**: Uses a passphrase-seeded Pseudo-Random Number Generator (PRNG) to shuffle bit placement, making the payload look like white noise.
- **Cross-Platform Extraction**: Generates a standalone PowerShell 5.1 script for lossless formats, enabling extraction on Windows without Python.
- **AES-256-CBC Encryption**: All payloads are encrypted with industry-standard AES-256-CBC using PBKDF2-HMAC-SHA256 key derivation.
- **Metadata Stripping**: Automatically removes EXIF, tags, and other metadata from carrier files.
- **Multi-Format Support**:
    - **Lossless Images**: PNG, BMP (LSB)
    - **Lossless Audio**: WAV (LSB)
    - **Lossy Images**: JPG/JPEG (DCT-domain)
    - **Lossy Audio**: MP3 (Time-domain)

## How It Works

### Steganography Methods

1.  **Least Significant Bit (LSB)**: For lossless formats like PNG and WAV, Plumage modifies the last bit of raw pixel or audio samples. Because these formats are lossless, the data remains intact.
2.  **Discrete Cosine Transform (DCT)**: For JPG files, Plumage hides data in the frequency domain coefficients. This is more resilient to JPEG compression than standard LSB.
3.  **PRNG Shuffle**: Instead of hiding data sequentially (which is easy to detect), Plumage uses a 32-bit Linear Congruential Generator (LCG) seeded by your passphrase to scatter the bits throughout the entire file. Without the password, the bits are indistinguishable from natural file noise.

## Installation

### Prerequisites

- Python 3.8+
- `ffmpeg` (required for MP3/Audio processing)

### Setup

```bash
pip install Pillow cryptography numpy pydub
```

## Usage Guide

### 1. Embedding a Payload

To hide a file inside an image and generate a PowerShell extraction script:

```bash
python3 plumage.py embed -i carrier.png -p secret.txt -o stego.png -pass "YourStrongPassword" --ps1
```

- `-i`: The original image/audio file.
- `-p`: The file you want to hide.
- `-o`: The output file name.
- `-pass`: The passphrase used for encryption and shuffling.
- `--ps1`: (Optional) Generates a `.ps1` script for Windows users.

### 2. Extracting a Payload (Python)

To recover the hidden file using Plumage:

```bash
python3 plumage.py extract -i stego.png -o recovered.txt -pass "YourStrongPassword"
```

### 3. Extracting a Payload (PowerShell)

If you generated a `.ps1` script during the embedding phase, a Windows user can extract the payload without having Python installed:

1.  Open PowerShell.
2.  Run the generated script:
    ```powershell
    .\stego.png.extract.ps1 -InputFile .\stego.png -OutputFile .\recovered.txt -Passphrase "YourStrongPassword"
    ```
    *Note: If script execution is restricted, use `PowerShell.exe -ExecutionPolicy Bypass -File .\script.ps1`*

## Important Notes on Lossy Formats (JPG/MP3)

Hiding data in JPG or MP3 is inherently fragile because these formats use lossy compression.
- **JPG**: Plumage uses high-quality settings (Quality 100, no subsampling) to preserve hidden bits. Extraction may fail if the image is resized or re-compressed by a third-party tool.
- **MP3**: Steganography in MP3 is highly sensitive. For best results, use high-bitrate carriers (320kbps) and avoid further re-encoding.
- **PowerShell Extraction**: Due to the complexity of decoding DCT/Huffman layers in a script, PowerShell extraction is only supported for **PNG, BMP, and WAV**.

## Security Disclaimer

Plumage is intended for privacy and security research. Always ensure you have the right to use carrier files and follow local regulations regarding encryption.
