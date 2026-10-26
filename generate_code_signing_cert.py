import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CERTS_DIR = BASE_DIR / "certs"
PFX_PATH = CERTS_DIR / "RawView_CodeSign.pfx"
CER_PATH = CERTS_DIR / "RawView_RootCA.cer"
CERT_PASSWORD = "RawView2026"

def generate_certificate(force: bool = False) -> bool:
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    if PFX_PATH.exists() and CER_PATH.exists() and not force:
        print(f"[+] Code signing certificate already exists at: {PFX_PATH}")
        return True

    print("[*] Generating 2048-bit Authenticode Code Signing Certificate for RawView...")
    pfx_win = str(PFX_PATH).replace('/', '\\')
    cer_win = str(CER_PATH).replace('/', '\\')

    ps_script = f"""
    $ErrorActionPreference = 'Stop'
    $cert = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject "CN=RawView Software, O=BlackBox THC, OU=Release Signing, C=BD" `
        -KeyAlgorithm RSA `
        -KeyLength 2048 `
        -KeyUsage DigitalSignature `
        -CertStoreLocation "Cert:\\CurrentUser\\My" `
        -NotAfter (Get-Date).AddYears(10) `
        -FriendlyName "RawView Official Release Certificate"

    Write-Host "[+] Certificate created with thumbprint: $($cert.Thumbprint)"

    # Export PFX (with password)
    $pwd = ConvertTo-SecureString '{CERT_PASSWORD}' -AsPlainText -Force
    Export-PfxCertificate -Cert $cert -FilePath "{pfx_win}" -Password $pwd | Out-Null
    Write-Host "[+] Exported PFX: {pfx_win}"

    # Export Public CER
    Export-Certificate -Cert $cert -FilePath "{cer_win}" | Out-Null
    Write-Host "[+] Exported Public Root CER: {cer_win}"
    """

    res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script], capture_output=True, text=True)
    if res.returncode == 0:
        print(res.stdout)
        print("[+] Code signing certificate generated successfully!")
        return True
    else:
        print(f"[!] Certificate generation failed: {res.stderr or res.stdout}")
        return False

if __name__ == "__main__":
    force_gen = "--force" in sys.argv
    success = generate_certificate(force=force_gen)
    sys.exit(0 if success else 1)
