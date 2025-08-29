from django.db import models

class Radio(models.Model):
    TEI = models.BigIntegerField(primary_key=True)
    fireplan_id = models.IntegerField(null=True, blank=True)
    model = models.ForeignKey('RadioModel', null=True, blank=True, on_delete=models.PROTECT)

    @property
    def ISSI(self):
        return self.subscription.issi.number if hasattr(self, 'subscription') else None

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

    def __str__(self):
        tei = str(self.TEI).zfill(14)
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


