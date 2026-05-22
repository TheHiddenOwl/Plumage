import argparse
import sys
import os
from PIL import Image
from pydub import AudioSegment
from plumage.stego.lsb import embed_lsb_image, extract_lsb_image
from plumage.stego.dct import embed_dct_image, extract_dct_image
from plumage.stego.audio import embed_lsb_audio, extract_lsb_audio, embed_lsb_mp3, extract_lsb_mp3
from plumage.stego.powershell import generate_powershell_script
from plumage.utils import strip_metadata_image

def main():
    parser = argparse.ArgumentParser(description="Plumage - Advanced Steganography CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Embed command
    embed_parser = subparsers.add_parser("embed", help="Embed a payload into a carrier file")
    embed_parser.add_argument("-i", "--input", required=True, help="Carrier file (image or audio)")
    embed_parser.add_argument("-p", "--payload", required=True, help="Payload file to hide")
    embed_parser.add_argument("-o", "--output", required=True, help="Output stego file")
    embed_parser.add_argument("-pass", "--passphrase", required=True, help="Passphrase for encryption")
    embed_parser.add_argument("--ps1", action="store_true", help="Generate a PowerShell extraction script")

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract a payload from a stego file")
    extract_parser.add_argument("-i", "--input", required=True, help="Stego file")
    extract_parser.add_argument("-o", "--output", required=True, help="Output payload file")
    extract_parser.add_argument("-pass", "--passphrase", required=True, help="Passphrase for decryption")

    args = parser.parse_args()

    if args.command == "embed":
        handle_embed(args)
    elif args.command == "extract":
        handle_extract(args)
    else:
        parser.print_help()

def handle_embed(args):
    input_ext = os.path.splitext(args.input)[1].lower()
    output_ext = os.path.splitext(args.output)[1].lower()

    with open(args.payload, 'rb') as f:
        payload_data = f.read()

    print(f"[*] Embedding payload into {args.input}...")

    if input_ext in ['.png', '.bmp']:
        img = Image.open(args.input).convert('RGB')
        img = strip_metadata_image(img)
        stego_img = embed_lsb_image(img, payload_data, args.passphrase)
        # Ensure metadata is stripped during save
        stego_img.save(args.output, exif=b'')
        if args.ps1:
            write_ps1(args.output, args.passphrase, 'image')

    elif input_ext == '.jpg' or input_ext == '.jpeg':
        img = Image.open(args.input).convert('RGB')
        img = strip_metadata_image(img)
        print("[!] Warning: JPG steganography is lossy and may fail to extract if the image is re-compressed.")
        stego_img = embed_dct_image(img, payload_data, args.passphrase)
        # Force saving without any lossy compression if possible
        stego_img.save(args.output, format='JPEG', quality=100, subsampling=0, exif=b'')
        if args.ps1:
            print("[!] PowerShell extraction is not supported for JPG (DCT).")

    elif input_ext == '.wav':
        audio = AudioSegment.from_file(args.input, format="wav")
        stego_audio = embed_lsb_audio(audio, payload_data, args.passphrase)
        stego_audio.export(args.output, format="wav")
        if args.ps1:
            write_ps1(args.output, args.passphrase, 'audio')

    elif input_ext == '.mp3':
        audio = AudioSegment.from_file(args.input, format="mp3")
        print("[!] Warning: MP3 steganography is highly unreliable due to lossy re-encoding.")
        stego_audio = embed_lsb_mp3(audio, payload_data, args.passphrase)
        # High bitrate for robustness, and strip tags
        stego_audio.export(args.output, format="mp3", bitrate="320k", tags={})
        if args.ps1:
            print("[!] PowerShell extraction is not supported for MP3.")

    else:
        print(f"[-] Unsupported input format: {input_ext}")
        return

    print(f"[+] Successfully embedded payload in {args.output}")

def handle_extract(args):
    input_ext = os.path.splitext(args.input)[1].lower()
    print(f"[*] Extracting payload from {args.input}...")

    try:
        if input_ext in ['.png', '.bmp']:
            img = Image.open(args.input)
            data = extract_lsb_image(img, args.passphrase)
        elif input_ext in ['.jpg', '.jpeg']:
            img = Image.open(args.input)
            try:
                data = extract_lsb_image(img, args.passphrase)
            except:
                data = extract_dct_image(img, args.passphrase)
        elif input_ext == '.wav':
            audio = AudioSegment.from_file(args.input, format="wav")
            data = extract_lsb_audio(audio, args.passphrase)
        elif input_ext == '.mp3':
            audio = AudioSegment.from_file(args.input, format="mp3")
            data = extract_lsb_mp3(audio, args.passphrase)
        else:
            print(f"[-] Unsupported input format: {input_ext}")
            return

        with open(args.output, 'wb') as f:
            f.write(data)
        print(f"[+] Successfully extracted payload to {args.output}")

    except Exception as e:
        print(f"[-] Extraction failed: {e}")

def write_ps1(output_file, passphrase, file_type):
    ps1_content = generate_powershell_script(passphrase, file_type)
    ps1_filename = output_file + ".extract.ps1"
    with open(ps1_filename, 'w') as f:
        f.write(ps1_content)
    print(f"[*] PowerShell extraction script generated: {ps1_filename}")

if __name__ == "__main__":
    main()
