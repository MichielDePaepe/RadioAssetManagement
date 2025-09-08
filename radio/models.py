from django.db import models
from PIL import Image
import qrcode
import barcode
from barcode.writer import ImageWriter


class Radio(models.Model):
    TEI = models.BigIntegerField(primary_key=True)
    fireplan_id = models.IntegerField(null=True, blank=True)
    model = models.ForeignKey('RadioModel', null=True, blank=True, on_delete=models.PROTECT)

    @property
    def ISSI(self):
        return self.subscription.issi.number if hasattr(self, 'subscription') else None

    @property
    def tei_str(self):
        return f"{self.TEI:014d}"

    @property
    def tei_15_str(self):
        return f"{self.tei_str}0"

    @property
    def alias(self):
        return self.subscription.issi.alias if hasattr(self, 'subscription') else None

    @property
    def is_active(self):
        return self.subscription.active if hasattr(self, 'subscription') else False

    def save(self, *args, **kwargs):
        matching_range = TEIRange.objects.filter(min_tei__lte=self.TEI, max_tei__gte=self.TEI).first()
        if not matching_range:
            raise ValueError(f"Geen RadioModel gevonden voor TEI {self.TEI}")
        self.model = matching_range.model
        super().save(*args, **kwargs)

    def print_qr(self, printer, copies=1):
        mm_to_px = lambda mm: int(mm * printer.dpi / 25.4)
        if not self.fireplan_id:
                raise Exception(f"Radio with TEI {self.TEI} has no Fireplan ID") 

        url = f"https://infoscan.firebru.brussels?data=1,1,{self.fireplan_id},1010"
        qr = qrcode.QRCode(version=4, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=70, border=0)
        qr.add_data(url)
        qr.make(fit=True)

        tape_px = mm_to_px(18-2)
        img_qr = qr.make_image(fill_color="black", back_color="white").convert("RGB").resize((tape_px, tape_px))

        printer.print(type="18", images=[img_qr] * int(copies))

        return f"{copies} QR code(s) sent to printer {printer.name}."

    def print_tei(self, printer):
        mm_to_px = lambda mm: int(mm * printer.dpi / 25.4)
        mm_to_pt = lambda mm: mm * 72 / 25.4

        label_w_px = mm_to_px(30-2)
        label_h_px = 150

        logo_img = Image.open("logo.png").convert("L")
        aspect_ratio = logo_img.width / logo_img.height
        logo_h_px = int(label_h_px / 2)
        logo_w_px = int(logo_h_px * aspect_ratio)
        logo_img = logo_img.resize((logo_w_px, logo_h_px))

        tei = self.tei_15_str
        code128 = barcode.get("code128", tei, writer=ImageWriter())
        barcode_img = code128.render(writer_options={
            "module_height": 2.75,
            "module_width": 25 / len(tei) / 8.932,
            "quiet_zone": 0,
            "font_size": mm_to_pt(2.5),
            "text_distance": 2.75,
            "dpi": printer.dpi
        }).convert("L")        

        # logo position
        logo_x = int((label_w_px - logo_img.width) / 2)
        logo_y = 0

        # barcode position
        barcode_x = int((label_w_px - barcode_img.width) / 2)
        barcode_y = logo_y + logo_img.height - mm_to_px(1)

        # create image
        label_img = Image.new("L", (label_w_px, label_h_px), color=255)
        label_img.paste(barcode_img, (barcode_x, barcode_y))
        label_img.paste(logo_img, (logo_x, logo_y))

        printer.print(type="12", images=[label_img.rotate(90, expand=True)])

        return f"TEI label has been send to printer {printer.name}."



    def __str__(self):
        tei = f"{self.TEI:014d}"
        if hasattr(self, 'subscription'):
            return "%s - %s" % (tei, str(self.subscription.issi))
        return tei

class RadioModel(models.Model):
    name = models.CharField(max_length=100, blank=True)
    is_atex = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class TEIRange(models.Model):
    model = models.ForeignKey(RadioModel, on_delete=models.CASCADE)
    min_tei = models.BigIntegerField()
    max_tei = models.BigIntegerField()

    def __str__(self):
        return f"{self.model.name}: {self.min_tei} - {self.max_tei}"



class ISSI(models.Model):
    number = models.BigIntegerField(primary_key=True) 
    alias = models.CharField(max_length=12, blank=True)
    customer = models.ForeignKey('Customer', null=True, blank=True, on_delete=models.CASCADE)
    discipline = models.ForeignKey('Discipline', null=True, blank=True, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        matching_range = ISSICustomerRange.objects.filter(min_issi__lte=self.number, max_issi__gte=self.number).first()
        if matching_range:
            self.customer = matching_range.customer
        else:
            self.customer = None

        matching_range = ISSIDisciplineRange.objects.filter(min_issi__lte=self.number, max_issi__gte=self.number).first()
        if matching_range:
            self.discipline = matching_range.discipline
        else:
            self.discipline = None

        super().save(*args, **kwargs)

    def __str__(self):
        if self.alias:
            return f"{self.number} ({self.alias})"
        return str(self.number)


class Customer(models.Model):
    name = models.CharField(max_length=100)
    owner = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class ISSICustomerRange(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE)
    min_issi = models.BigIntegerField()
    max_issi = models.BigIntegerField()

    def __str__(self):
        return f"{self.customer.name}: {self.min_issi} - {self.max_issi}"


class Discipline(models.Model):
    name = models.CharField(max_length=100)
    bootstrap_class = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return self.name


class ISSIDisciplineRange(models.Model):
    discipline = models.ForeignKey('Discipline', on_delete=models.CASCADE)
    min_issi = models.BigIntegerField()
    max_issi = models.BigIntegerField()

    def __str__(self):
        return f"{self.discipline.name}: {self.min_issi} - {self.max_issi}"


class Subscription(models.Model):
    radio = models.OneToOneField(Radio, on_delete=models.CASCADE, related_name="subscription")
    issi = models.OneToOneField(ISSI, on_delete=models.CASCADE, related_name="subscription")
    astrid_alias = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('radio', 'issi')


