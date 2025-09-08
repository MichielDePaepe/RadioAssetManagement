from PIL import Image
import barcode
from barcode.writer import ImageWriter

# Conversion function
dpi = 300
mm_to_px = lambda mm: int(mm * dpi / 25.4)
mm_to_pt = lambda mm: mm * 72 / 25.4

px_to_mm = lambda px: px * 25.4 / dpi


# Label dimensions (mm)
label_w, label_h = 30, 12  


label_w_px = mm_to_px(label_w)
label_h_px = mm_to_px(label_h)
label_h_px = 150

# Open and resize logo
logo = Image.open("logo.png").convert("L")
aspect_ratio = logo.width / logo.height
logo_h_px = mm_to_px(7)
logo_w_px = int(logo_h_px * aspect_ratio)
logo_resized = logo.resize((logo_w_px, logo_h_px))

# Generate barcode
tei = "000353060008560"

code128 = barcode.get("code128", tei, writer=ImageWriter())
barcode_img = code128.render(writer_options={
    "module_height": 2.75,
    "module_width": 25 / len(tei) / 8.932,
    "quiet_zone": 0,
    "font_size": mm_to_pt(2.5),
    "text_distance": 2.75
}).convert("L")


# Resize barcode to exactly 20x3 mm
#barcode_resized = barcode_img.resize((barcode_widht_px, barcode_height_px))
barcode_resized = barcode_img


# Create blank label image
label_img = Image.new("L", (label_w_px, label_h_px), color=255)

# logo position
logo_x = int((label_w_px - logo_resized.width) / 2)
logo_y = 0

# barcode position
barcode_x = int((label_w_px - barcode_resized.width) / 2)
barcode_y = logo_y + logo_resized.height - mm_to_px(1)

label_img.paste(barcode_resized, (barcode_x, barcode_y))
label_img.paste(logo_resized, (logo_x, logo_y))


label_img.show()

from brother_label import BrotherLabel
printer = BrotherLabel(
    device="PT-P900W",
    target="172.20.132.63",
    backend="network"
)

printer.print(type="12", images=[label_img.rotate(90, expand=True)])


