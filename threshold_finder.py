import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageEnhance
import os, django

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "RadioAssetManagement.settings")
django.setup()

from radio.models import Radio
from radio.services.image_service import ImageGenerator

# pak een test-radio uit je DB
radio = Radio.objects.first()
ig = ImageGenerator(radio)
original = ig.portable_radio_tei_label().convert("L")

def pil_to_tk(img, maxsize=(200, 200)):
    """Converteer PIL image naar Tk image met behoud aspect ratio."""
    copy = img.copy()
    copy.thumbnail(maxsize, Image.LANCZOS)
    return ImageTk.PhotoImage(copy)

def update_images(*args):
    contrast_val = contrast_slider.get()
    brightness_val = brightness_slider.get()
    threshold_val = threshold_slider.get()

    # stap 1: origineel grijs
    img1 = original

    # stap 2: contrast
    img2 = ImageEnhance.Contrast(img1).enhance(contrast_val)

    # stap 3: brightness
    img3 = ImageEnhance.Brightness(img2).enhance(brightness_val)

    # stap 4: threshold
    img4 = img3.point(lambda p: 0 if p < threshold_val else 255, "1")

    # naar Tk images
    tk_img1 = pil_to_tk(img1)
    tk_img2 = pil_to_tk(img2)
    tk_img3 = pil_to_tk(img3)
    tk_img4 = pil_to_tk(img4)

    # labels updaten
    label1.config(image=tk_img1); label1.image = tk_img1
    label2.config(image=tk_img2); label2.image = tk_img2
    label3.config(image=tk_img3); label3.image = tk_img3
    label4.config(image=tk_img4); label4.image = tk_img4

root = tk.Tk()
root.title("Label tuner")

frame = ttk.Frame(root, padding=10)
frame.grid(row=0, column=0)

contrast_slider = tk.Scale(frame, from_=0.5, to=10.0, resolution=0.1,
                           orient="horizontal", label="Contrast")
contrast_slider.set(2.0)
contrast_slider.grid(row=0, column=0, columnspan=4, sticky="ew")

brightness_slider = tk.Scale(frame, from_=0.5, to=10.0, resolution=0.1,
                             orient="horizontal", label="Brightness")
brightness_slider.set(1.5)
brightness_slider.grid(row=1, column=0, columnspan=4, sticky="ew")

threshold_slider = tk.Scale(frame, from_=0, to=255, resolution=1,
                            orient="horizontal", label="Threshold")
threshold_slider.set(128)
threshold_slider.grid(row=2, column=0, columnspan=4, sticky="ew")

# vier kolommen voor de previews
label1 = ttk.Label(frame); label1.grid(row=3, column=0, padx=5, pady=5)
label2 = ttk.Label(frame); label2.grid(row=3, column=1, padx=5, pady=5)
label3 = ttk.Label(frame); label3.grid(row=3, column=2, padx=5, pady=5)
label4 = ttk.Label(frame); label4.grid(row=3, column=3, padx=5, pady=5)

update_images()
contrast_slider.bind("<B1-Motion>", update_images)
brightness_slider.bind("<B1-Motion>", update_images)
threshold_slider.bind("<B1-Motion>", update_images)

root.mainloop()
