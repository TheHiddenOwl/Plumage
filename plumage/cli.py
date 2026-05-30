import argparse
import sys
import os
import logging
import getpass
from PIL import Image
from pydub import AudioSegment
from plumage.stego.lsb import embed_lsb_image, extract_lsb_image
from plumage.stego.dct import embed_dct_image, extract_dct_image
from plumage.stego.audio import embed_lsb_audio, extract_lsb_audio, embed_lsb_mp3, extract_lsb_mp3
from plumage.stego.powershell import generate_powershell_script
from plumage.utils import rebuild_image_from_pixels

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Plumage - Advanced Steganography CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Embed command
    embed_parser = subparsers.add_parser("embed", help="Embed a payload into a carrier file")
    embed_parser.add_argument("-i", "--input", required=True, help="Carrier file (image or audio)")
    embed_parser.add_argument("-p", "--payload", required=True, help="Payload file to hide")
    embed_parser.add_argument("-o", "--output", required=True, help="Output stego file")
    embed_parser.add_argument("-pass", "--passphrase", help="Passphrase for encryption")
    embed_parser.add_argument("-m", "--method", choices=['lsb', 'dct'], default='lsb', help="Embedding method (default: lsb)")
    embed_parser.add_argument("--ps1", action="store_true", help="Generate a PowerShell extraction script")
    embed_parser.add_argument("--force", action="store_true", help="Force operation (e.g. for MP3)")

    # Extract command
    extract_parser = subparsers.add_parser("extract", help="Extract a payload from a stego file")
    extract_parser.add_argument("-i", "--input", required=True, help="Stego file")
    extract_parser.add_argument("-o", "--output", required=True, help="Output payload file")
    extract_parser.add_argument("-pass", "--passphrase", help="Passphrase for decryption")

    args = parser.parse_args()

    if args.command == "embed":
        if not args.passphrase:
            args.passphrase = os.environ.get("PLUMAGE_PASSPHRASE") or getpass.getpass("Passphrase: ")
        handle_embed(args)
    elif args.command == "extract":
        if not args.passphrase:
            args.passphrase = os.environ.get("PLUMAGE_PASSPHRASE") or getpass.getpass("Passphrase: ")
        handle_extract(args)
    else:
        parser.print_help()

def handle_embed(args):
    if not os.path.isfile(args.input):
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
    if os.path.exists(args.output):
        logger.error(f"Output file already exists: {args.output}")
        sys.exit(1)

    input_ext = os.path.splitext(args.input)[1].lower()
    output_ext = os.path.splitext(args.output)[1].lower()

    try:
        with open(args.payload, 'rb') as f:
            payload_data = f.read()
    except Exception as e:
        logger.error(f"Failed to read payload file: {e}")
        sys.exit(1)

    logger.info(f"Embedding payload into {args.input}...")

    save_kwargs = {}
    if output_ext in ('.png', '.jpg', '.jpeg'):
        save_kwargs['exif'] = b''

    try:
        if input_ext in ['.png', '.bmp', '.jpg', '.jpeg']:
            img = Image.open(args.input).convert('RGB')
            img = rebuild_image_from_pixels(img)

            if args.method == 'lsb':
                if input_ext in ['.jpg', '.jpeg']:
                    logger.error("LSB embedding is not supported for JPG due to lossy compression. Use a lossless format (PNG/BMP).")
                    sys.exit(1)
                stego_img = embed_lsb_image(img, payload_data, args.passphrase)
            else: # dct
                if output_ext in ['.jpg', '.jpeg']:
                    logger.error("DCT embedding does not survive JPEG re-encoding. Please save as PNG or BMP even when using a JPG carrier.")
                    sys.exit(1)
                stego_img = embed_dct_image(img, payload_data, args.passphrase)

            stego_img.save(args.output, **save_kwargs)
            if args.ps1:
                if args.method == 'lsb':
                    write_ps1(args.output, args.passphrase, 'image')
                else:
                    logger.warning("PowerShell extraction is not supported for DCT.")

        elif input_ext == '.wav':
            audio = AudioSegment.from_file(args.input, format="wav")
            stego_audio = embed_lsb_audio(audio, payload_data, args.passphrase)
            stego_audio.export(args.output, format="wav")
            if args.ps1:
                write_ps1(args.output, args.passphrase, 'audio')

        elif input_ext == '.mp3':
            if not args.force:
                logger.error("MP3 steganography is highly unreliable due to lossy re-encoding. Use --force to proceed anyway.")
                sys.exit(1)
            audio = AudioSegment.from_file(args.input, format="mp3")
            logger.warning("MP3 steganography is highly unreliable due to lossy re-encoding.")
            stego_audio = embed_lsb_mp3(audio, payload_data, args.passphrase)
            # High bitrate for robustness, and strip tags
            stego_audio.export(args.output, format="mp3", bitrate="320k", tags={})
            if args.ps1:
                logger.warning("PowerShell extraction is not supported for MP3.")

        else:
            logger.error(f"Unsupported input format: {input_ext}")
            sys.exit(1)

        logger.info(f"Successfully embedded payload in {args.output}")

    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        sys.exit(1)

def handle_extract(args):
    if not os.path.isfile(args.input):
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
    if os.path.exists(args.output):
        logger.error(f"Output file already exists: {args.output}")
        sys.exit(1)

    input_ext = os.path.splitext(args.input)[1].lower()
    logger.info(f"Extracting payload from {args.input}...")

    try:
        if input_ext in ['.png', '.bmp', '.jpg', '.jpeg']:
            img = Image.open(args.input).convert('RGB')
            try:
                data = extract_lsb_image(img, args.passphrase)
            except Exception:
                data = extract_dct_image(img, args.passphrase)
        elif input_ext == '.wav':
            audio = AudioSegment.from_file(args.input, format="wav")
            data = extract_lsb_audio(audio, args.passphrase)
        elif input_ext == '.mp3':
            audio = AudioSegment.from_file(args.input, format="mp3")
            data = extract_lsb_mp3(audio, args.passphrase)
        else:
            logger.error(f"Unsupported input format: {input_ext}")
            sys.exit(1)

        with open(args.output, 'wb') as f:
            f.write(data)
        logger.info(f"Successfully extracted payload to {args.output}")

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        sys.exit(1)

def write_ps1(output_file, passphrase, file_type):
    ps1_content = generate_powershell_script(passphrase, file_type)
    ps1_filename = output_file + ".extract.ps1"
    with open(ps1_filename, 'w') as f:
        f.write(ps1_content)
    logger.info(f"PowerShell extraction script generated: {ps1_filename}")

if __name__ == "__main__":
    main()
