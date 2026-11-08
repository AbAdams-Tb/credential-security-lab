"""Create a local QR code for Sarah's fictional MFA account."""
import pyotp
import qrcode
from server import BASE, mfa_secret

uri = pyotp.TOTP(mfa_secret).provisioning_uri(
    name="sarah@example.com", issuer_name="Credential Security Lab"
)
path = BASE / "mfa_qr.png"
qrcode.make(uri).save(path)
print(f"Open and scan: {path}")
print("Do not commit this QR image or the .mfa_sarah_secret file.")
