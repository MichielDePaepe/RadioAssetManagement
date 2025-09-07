from brother_label import BrotherLabel
from PIL import Image
import qrcode

# Printer instellen
printer = BrotherLabel(
    device="PT-P900W",
    target="172.20.132.63",
    backend="network"
)

# QR-code genereren
qr = qrcode.QRCode(
    version=4,
    error_correction=qrcode.constants.ERROR_CORRECT_M,
    box_size=10,
    border=0  # geen extra wit
)
qr.add_data("https://infoscan.firebru.brussels?data=1,1,482,1010")
qr.make(fit=True)
img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGB")

# Schaal QR naar exact tape formaat 18x18 mm
tape_size = 1800  # pixels bij jouw resolutie
img_qr = img_qr.resize((tape_size, tape_size))

# Plaats QR op label zonder marges
img = Image.new("RGB", (tape_size, tape_size), "white")
img.paste(img_qr, (0, 0))

# Printen zonder marges/snedes
printer.print(
    type='18',
    images=[img],
    autocut=False,
    halfcut=False
)
