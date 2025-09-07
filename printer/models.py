from django.db import models

from brother_label import BrotherLabel
from brother_label.devices import BrotherDeviceManager

class Printer(models.Model):
    name = models.CharField(max_length=100, unique=True)

    # device choices ophalen
    device_manager = BrotherDeviceManager()
    device_choices = [(k, k) for k in dict(device_manager).keys()]
    device = models.CharField(max_length=50, choices=device_choices)

    location = models.CharField(max_length=200, blank=True)
    ip = models.GenericIPAddressField(protocol='both', unpack_ipv4=False)

    BACKEND_CHOICES = [
        ('network', 'Network'),
        ('linux_kernel', 'Linux Kernel'),
        ('usb', 'USB'),
    ]
    backend = models.CharField(max_length=20, choices=BACKEND_CHOICES, default='network')


    def __str__(self):
        return f"{self.name} ({self.device})"


    def print(self, type, images, **kwargs):

    	# Initialize BrotherLabel with the printer settings
	    printer = BrotherLabel(
	        device=self.device,
	        target=self.ip,
	        backend=self.backend
	    )

	    if not isinstance(images, list):
	    	images = [images]     

	    return printer.print(type=type, images=images, **kwargs)