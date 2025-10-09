from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
import qrcode
import barcode
from barcode.writer import ImageWriter


def image2black_and_white(img):
    result_img = img.convert("L")
    result_img = ImageEnhance.Contrast(result_img).enhance(5.0)
    #result_img = ImageEnhance.Brightness(result_img).enhance(1.5)
    #result_img = result_img.point(lambda p: 0 if p < 180 else 255, '1')
    return result_img


def map_grayscale_to_colors(gray_img: Image.Image, color_dark=(255, 255, 255), color_light=(0, 0, 255)) -> Image.Image:
    """
    Map a grayscale image to two colors.
    
    Parameters:
    - gray_img: PIL.Image in "L" mode (grayscale)
    - color_dark: RGB tuple for the pixels that are dark (e.g. black -> white)
    - color_light: RGB tuple for the pixels that are light (e.g. white -> blue)
    
    Returns:
    - PIL.Image in RGB mode
    """
    # invert the grayscale image to use as a mask
    # dark pixels will become white, light pixels will become black
    inverted = ImageOps.invert(gray_img.convert("L"))
    
    # create a new image filled with the 'light' color (background)
    new_img = Image.new("RGB", gray_img.size, color_light)
    
    # paste the 'dark' color where the mask (inverted) is white
    new_img.paste(color_dark, mask=inverted)
    
    return new_img


class ImageGenerator:

    def __init__(self, radio, dpi=360):
        self.radio = radio
        self.dpi = dpi

    def mm_to_px(self, mm):
        return int(mm * self.dpi / 25.4)

    def mm_to_pt(self, mm):
        return mm * 72 / 25.4

    def add_padding(self, img, target_width):
        """Add white padding left and right to reach target width"""
        if img.width >= target_width:
            return img  # already wide enough

        new_img = Image.new("RGB", (target_width, img.height), "white")
        left_padding = (target_width - img.width) // 2
        new_img.paste(img, (left_padding, 0))
        return new_img

    


    def qr_image(self, color_dark=(0, 0, 0), color_light=(255, 255, 255)):

        if not self.radio.fireplan_id:
            raise Exception(f"Radio with TEI {self.radio.TEI} has no Fireplan ID") 

        url = f"https://infoscan.firebru.brussels?data=1,1,{self.radio.fireplan_id},1010"

        qr = qrcode.QRCode(version=4, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=70, border=0)
        qr.add_data(url)
        qr.make(fit=True)

        qr_px = 234 - self.mm_to_px(1.5)

        img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((qr_px, qr_px))

        img_qr_padded = self.add_padding(img_qr, 234)

        return map_grayscale_to_colors(img_qr_padded.convert("L"), color_dark, color_light)


    def portable_radio_tei_label(self, color_dark=(0, 0, 0), color_light=(255, 255, 255)):
        label_w_px = self.mm_to_px(30-2)
        label_h_px = 150

        logo_img = image2black_and_white(Image.open("logo.png"))

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
            "dpi": self.dpi
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

        return map_grayscale_to_colors(label_img, color_dark, color_light)


    def mobile_radio_label(self, color_dark=(0, 0, 0), color_light=(255, 255, 255)):

        label_h_px = 150  # label height in pixels (12 mm)

        # logo on the left, full height
        logo_img = image2black_and_white(Image.open("logo.png"))
        aspect_ratio = logo_img.width / logo_img.height
        logo_h_px = label_h_px
        logo_w_px = int(logo_h_px * aspect_ratio)
        logo_img = logo_img.resize((logo_w_px, logo_h_px))

        # set font
        font = ImageFont.truetype("fonts/Barlow-Bold.ttf", self.mm_to_px(4.5))

        # text strings
        issi_text = f"ISSI: {self.radio.ISSI}"
        alias_text = f"Alias: {self.radio.alias}"

        # calculate text width
        text_width_issi = font.getbbox(issi_text)[2]  # x1 of bbox
        text_width_alias = font.getbbox(alias_text)[2] if self.radio.alias else 0
        text_width = max(text_width_issi, text_width_alias)

        # total label width = logo + padding + text + extra padding
        label_w_px = logo_w_px + self.mm_to_px(3) + text_width + self.mm_to_px(1)

        # create new blank label
        label_img = Image.new("L", (label_w_px, label_h_px), color=255)
        draw = ImageDraw.Draw(label_img)

        # paste logo on the left
        label_img.paste(logo_img, (0, 0))

        # draw text next to logo
        text_x = logo_w_px + self.mm_to_px(3)
        if self.radio.alias:
            # draw ISSI on top
            draw.text((text_x, 0), issi_text, font=font, fill=0)
            # draw alias in middle
            draw.text((text_x, int(label_h_px/2)), alias_text, font=font, fill=0)
        else:
            # center ISSI vertically if no alias
            bbox = font.getbbox(issi_text)
            text_height = bbox[3] - bbox[1]
            text_y = (label_h_px - text_height) // 2 - bbox[1]
            draw.text((text_x, text_y), issi_text, font=font, fill=0)

        # map grayscale to the requested colors
        return map_grayscale_to_colors(label_img, color_dark, color_light)