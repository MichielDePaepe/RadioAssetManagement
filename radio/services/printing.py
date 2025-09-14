from PIL import Image, ImageDraw, ImageFont
import qrcode
import barcode
from barcode.writer import ImageWriter


class RadioPrintingService:
    def __init__(self, radio, printer):
        self.radio = radio
        self.printer = printer

    def mm_to_px(self, mm):
        return int(mm * self.printer.dpi / 25.4)

    def mm_to_pt(self, mm):
        return mm * 72 / 25.4

    def add_padding(self, img, target_height):
        """Add white padding above and below to reach target height"""
        if img.height >= target_height:
            return img  # already tall enough

        new_img = Image.new("RGB", (img.width, target_height), "white")
        top_padding = (target_height - img.height) // 2
        new_img.paste(img, (0, top_padding))
        return new_img

    def print_qr(self, copies=1):
        if not self.radio.fireplan_id:
            raise Exception(f"Radio with TEI {self.radio.TEI} has no Fireplan ID") 

        url = f"https://infoscan.firebru.brussels?data=1,1,{self.radio.fireplan_id},1010"
        qr = qrcode.QRCode(version=4, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=70, border=0)
        qr.add_data(url)
        qr.make(fit=True)

        qr_px = self.mm_to_px(18-2)

        img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((qr_px, qr_px))

        img_qr_padded = self.add_padding(img_qr, 234)

        img_qr_padded.show()
        print(img_qr_padded.height)
        self.printer.print(type="18", images=[img_qr_padded] * int(copies))

        return f"{copies} QR code(s) sent to printer {self.printer.name}."

    def print_tei(self, copies=1):
        label_w_px = self.mm_to_px(30-2)
        label_h_px = 150

        logo_img = Image.open("logo.png").convert("L")
        aspect_ratio = logo_img.width / logo_img.height
        logo_h_px = int(label_h_px / 2)
        logo_w_px = int(logo_h_px * aspect_ratio)
        logo_img = logo_img.resize((logo_w_px, logo_h_px))

        tei = self.radio.tei_15_str
        code128 = barcode.get("code128", tei, writer=ImageWriter())
        barcode_img = code128.render(writer_options={
            "module_height": 2.75,
            "module_width": 25 / len(tei) / 8.932,
            "quiet_zone": 0,
            "font_size": self.mm_to_pt(2.5),
            "text_distance": 2.75,
            "dpi": self.printer.dpi
        }).convert("L")        

        # logo position
        logo_x = int((label_w_px - logo_img.width) / 2)
        logo_y = 0

        # barcode position
        barcode_x = int((label_w_px - barcode_img.width) / 2)
        barcode_y = logo_y + logo_img.height - self.mm_to_px(1)

        # create image
        label_img = Image.new("L", (label_w_px, label_h_px), color=255)
        label_img.paste(barcode_img, (barcode_x, barcode_y))
        label_img.paste(logo_img, (logo_x, logo_y))

        label_img.show()
        self.printer.print(type="12", images=[label_img.rotate(90, expand=True)] * int(copies))

        return f"TEI label has been send to printer {self.printer.name}."

    def print_mobile_label(self, copies=1):

        label_w_px = self.mm_to_px(70-2)
        label_h_px = 150 # 12mm label

        # logo links, volle hoogte
        logo_img = Image.open("logo.png").convert("L")
        aspect_ratio = logo_img.width / logo_img.height
        logo_h_px = label_h_px
        logo_w_px = int(logo_h_px * aspect_ratio)
        logo_img = logo_img.resize((logo_w_px, logo_h_px))

        # nieuwe lege label
        label_img = Image.new("L", (label_w_px, label_h_px), color=255)
        draw = ImageDraw.Draw(label_img)

        # logo links plakken
        label_img.paste(logo_img, (0, 0))

        # font
        font = ImageFont.truetype("fonts/Barlow-Bold.ttf", self.mm_to_px(4.5))

        # tekst links naast logo
        text_x = logo_img.width + self.mm_to_px(3)
        text_y = 0

        draw.text((text_x, text_y), f"ISSI: {self.radio.ISSI}", font=font, fill=0)
        if self.radio.alias:
            draw.text((text_x, int(label_h_px/2)), f"Alias: {self.radio.alias}", font=font, fill=0)

        label_img.show()
        self.printer.print(type="12", images=[label_img.rotate(90, expand=True)] * int(copies))

        return f"Mobile radio label has been send to printer {self.printer.name}."