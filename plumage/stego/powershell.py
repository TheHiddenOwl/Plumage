import os

def generate_powershell_script(passphrase: str, file_type: str) -> str:
    """
    Generates a PowerShell 5.1 compatible script to extract LSB-encoded data.
    file_type should be 'image' or 'audio'.
    """
    ps_script = f"""
Param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile,
    [Parameter(Mandatory=$true)]
    [string]$OutputFile,
    [Parameter(Mandatory=$true)]
    [string]$Passphrase
)

# Helper function to get SHA256 for seeding
function Get-Seed($p) {{
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $hash = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($p))
    # Use first 4 bytes for a 32-bit unsigned seed
    return [BitConverter]::ToUInt32($hash, 0)
}}

# 32-bit LCG to match Python implementation
function Get-NextRandom([ref]$state) {{
    $a = [uint32]1664525
    $c = [uint32]1013904223
    # Use bitwise mask to simulate 32-bit wrapping in PowerShell
    $val = ([long]$a * [long]$state.Value + [long]$c) -band 0xFFFFFFFF
    $state.Value = [uint32]$val
    return $state.Value
}}

function Get-ShuffledIndices($size, $seed) {{
    $indices = New-Object int[] $size
    for ($i = 0; $i -lt $size; $i++) {{ $indices[$i] = $i }}
    $state = $seed
    for ($i = $size - 1; $i -gt 0; $i--) {{
        $r = (Get-NextRandom ([ref]$state)) % ($i + 1)
        $tmp = $indices[$i]
        $indices[$i] = $indices[$r]
        $indices[$r] = $tmp
    }}
    return $indices
}}

# AES-256-CBC Decryption (PowerShell 5.1 compatible)
function Decrypt-Data($encryptedBundle, $passphrase) {{
    $salt = $encryptedBundle[0..15]
    $iv = $encryptedBundle[16..31]
    $ciphertext = $encryptedBundle[32..($encryptedBundle.Length - 1)]

    $iter = 100000
    $kdf = New-Object System.Security.Cryptography.Rfc2898DeriveBytes $passphrase, $salt, $iter
    $key = $kdf.GetBytes(32)

    $aes = [System.Security.Cryptography.Aes]::Create()
    $aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
    $aes.Padding = [System.Security.Cryptography.PaddingMode]::PKCS7
    $aes.Key = $key
    $aes.IV = $iv

    $decryptor = $aes.CreateDecryptor()
    $ms = New-Object System.IO.MemoryStream @(,$ciphertext)
    $cs = New-Object System.Security.Cryptography.CryptoStream $ms, $decryptor, [System.Security.Cryptography.CryptoStreamMode]::Read

    $data = New-Object byte[] $ciphertext.Length
    $read = $cs.Read($data, 0, $data.Length)
    return $data[0..($read-1)]
}}

Write-Host "Reading $InputFile..."
"""
    if file_type == 'image':
        ps_script += """
# Load image and get raw bytes
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap $InputFile
$rect = New-Object System.Drawing.Rectangle 0, 0, $bmp.Width, $bmp.Height
$bmpData = $bmp.LockBits($rect, [System.Drawing.Imaging.ImageLockMode]::ReadOnly, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
$stride = [Math]::Abs($bmpData.Stride)
$byteCount = $stride * $bmp.Height
$pixels = New-Object byte[] $byteCount
[System.Runtime.InteropServices.Marshal]::Copy($bmpData.Scan0, $pixels, 0, $byteCount)
$bmp.UnlockBits($bmpData)
$bmp.Dispose()
"""
    else: # audio
        ps_script += """
# Load WAV and get raw bytes
function Get-WavDataChunk($bytes) {
    # Find 'data' chunk
    for ($i = 0; $i -lt ($bytes.Length - 4); $i++) {
        if ($bytes[$i] -eq 100 -and $bytes[$i+1] -eq 97 -and $bytes[$i+2] -eq 116 -and $bytes[$i+3] -eq 97) {
            $dataSize = [BitConverter]::ToInt32($bytes, $i + 4)
            return $bytes[($i + 8)..($i + 8 + $dataSize - 1)]
        }
    }
    return $null
}

$rawFile = [System.IO.File]::ReadAllBytes($InputFile)
$pixels = Get-WavDataChunk $rawFile
if ($null -eq $pixels) {
    Write-Error "Could not find data chunk in WAV file."
    exit
}
"""

    ps_script += """
$seed = Get-Seed $Passphrase
Write-Host "Generating indices (this may take a moment for large files)..."
$indices = Get-ShuffledIndices $pixels.Length $seed

# 1. Extract length (32 bits)
$lenBits = ""
for ($i = 0; $i -lt 32; $i++) {
    $idx = $indices[$i]
    $lenBits += ($pixels[$idx] -band 1).ToString()
}
$payloadLen = [Convert]::ToInt32($lenBits, 2)
Write-Host "Found encrypted payload length: $payloadLen bytes"

if ($payloadLen -le 0 -or $payloadLen -gt $pixels.Length) {
    Write-Error "Invalid payload length extracted. Wrong passphrase?"
    exit
}

# 2. Extract encrypted bundle
$bundleBits = ""
for ($i = 32; $i -lt (32 + $payloadLen * 8); $i++) {
    $idx = $indices[$i]
    $bundleBits += ($pixels[$idx] -band 1).ToString()
}

$encryptedBundle = New-Object byte[] $payloadLen
for ($i = 0; $i -lt $payloadLen; $i++) {
    $byteStr = $bundleBits.Substring($i * 8, 8)
    $encryptedBundle[$i] = [Convert]::ToByte($byteStr, 2)
}

Write-Host "Decrypting..."
try {
    $decrypted = Decrypt-Data $encryptedBundle $Passphrase
    [System.IO.File]::WriteAllBytes($OutputFile, $decrypted)
    Write-Host "Success! Extracted to $OutputFile"
} catch {
    Write-Error "Decryption failed. Wrong passphrase?"
}
"""
    return ps_script
