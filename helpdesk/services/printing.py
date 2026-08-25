from PIL import Image, ImageDraw, ImageFont


class TicketPrintingService:
    def __init__(self, ticket, printer, dpi=360):
        self.ticket = ticket
        self.printer = printer
        self.dpi = dpi

    def mm_to_px(self, mm):
        return int(mm * self.dpi / 25.4)

    def label_text(self):
        request_type = getattr(self.ticket, "request_type", "")
        if request_type in {"VTEI", "VISSI", "VISSI & VTEI"}:
            return f"{request_type} #{self.ticket.pk}"
        return f"#{self.ticket.pk}"

    def ticket_number_label(self):
        label_h_px = self.mm_to_px(12)
        text = self.label_text()
        font_size = self.mm_to_px(6)
        min_font_size = self.mm_to_px(3)
        max_label_w_px = self.mm_to_px(60)
        padding_x = self.mm_to_px(3)

        while font_size >= min_font_size:
            font = ImageFont.truetype("fonts/Barlow-Black.ttf", font_size)
            bbox = font.getbbox(text)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            label_w_px = min(max_label_w_px, text_w + padding_x * 2)
            if text_w <= label_w_px - padding_x * 2 and text_h <= label_h_px - self.mm_to_px(2):
                break
            font_size -= 1

        label_img = Image.new("RGB", (label_w_px, label_h_px), color="white")
        draw = ImageDraw.Draw(label_img)
        text_x = (label_w_px - text_w) // 2
        text_y = (label_h_px - text_h) // 2 - bbox[1]
        draw.text((text_x, text_y), text, font=font, fill="black")
        return label_img

    def print_ticket_number_label(self):
        img = self.ticket_number_label()
        self.printer.print(type="12", images=[img.rotate(90, expand=True)])
        return f"Ticket label #{self.ticket.pk} sent to printer {self.printer.name}."
