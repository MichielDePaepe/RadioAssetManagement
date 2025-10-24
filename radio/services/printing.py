from PIL import Image, ImageDraw, ImageFont
import qrcode
import barcode
from barcode.writer import ImageWriter
from .image_service import ImageGenerator

class RadioPrintingService:
    def __init__(self, radio, printer):
        self.radio = radio
        self.printer = printer
        self.image_generator = ImageGenerator(self.radio)

    def print_qr(self, copies=1):
        img = self.image_generator.qr_image()

        self.printer.print(type="18", images=[img] * int(copies))

        return f"{copies} QR code(s) sent to printer {self.printer.name}."

    def print_tei(self, copies=1):
        img = self.image_generator.portable_radio_tei_label()

        self.printer.print(type="12", images=[img.rotate(90, expand=True)] * int(copies))

        return f"TEI label has been send to printer {self.printer.name}."

    def print_mobile_label(self, copies=1):
        img = self.image_generator.mobile_radio_label()        

        self.printer.print(type="12", images=[img.rotate(90, expand=True)] * int(copies))

        return f"Mobile radio label has been send to printer {self.printer.name}."