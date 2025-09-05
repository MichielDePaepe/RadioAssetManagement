# python manage.py shell
# from load_em import do_import
# do_import("em.csv")


import csv
from radio.models import *
from django.db import transaction

filename = "em.csv"

def do_import(filename):

    em = Container.objects.get(name="Helihaven")

    with open(filename, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        data = list(reader)
        for row in data:
            container, _ = Container.objects.get_or_create(name=row["vehicle"], parent=em)
            print(row["name"] + " - " + str(container))
            rcl, _ = RadioContainerLink.objects.get_or_create(
                name = row["name"],
                container = container,
            )
            if row["ISSI"]:
                issi = ISSI.objects.get(number=row["ISSI"])
                if not issi.alias and getattr(issi, "subscription", None):
                    print(issi)
                    radio = issi.subscription.radio
                    rcl.radio = radio
                    rcl.save()
                    issi.alias = row["alias"]
                    issi.save()

