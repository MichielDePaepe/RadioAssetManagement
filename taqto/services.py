from django.db.models import Q
from django.urls import reverse

from radio.models import Discipline, ISSI, Radio


DISCIPLINE_TYPES = {
    "fire": Discipline.DisciplineType.FIRE,
    "medical": Discipline.DisciplineType.MEDICAL,
}


def get_phonebook_issi_queryset(discipline_filter=""):
    discipline_filter = (discipline_filter or "").lower()
    issi_qs = ISSI.objects.exclude(alias__isnull=True).exclude(alias__exact="")

    if discipline_filter in DISCIPLINE_TYPES:
        selected_type = DISCIPLINE_TYPES[discipline_filter]
        issi_qs = issi_qs.filter(
            Q(discipline__discipline_type=selected_type)
            | Q(discipline__discipline_type=Discipline.DisciplineType.OTHER)
        )

    return issi_qs.order_by("alias", "number")


def get_phonebook_contacts(discipline_filter=""):
    return [
        {
            "index": index,
            "name": issi.alias[:16],
            "number": str(issi.number),
            "type": 0,
            "type_label": "TETRA / SSI",
        }
        for index, issi in enumerate(
            get_phonebook_issi_queryset(discipline_filter).select_related("discipline"),
            start=1,
        )
    ]


def get_issi_radio_lookup():
    rows = (
        ISSI.objects.exclude(alias__isnull=True)
        .exclude(alias__exact="")
        .select_related("discipline")
        .values_list("number", "alias", "discipline__discipline_type")
    )
    return {
        str(number)[-7:]: {
            "alias": alias,
            "discipline": discipline_type,
        }
        for number, alias, discipline_type in rows
    }


def get_radio_detail_lookup():
    lookup = {}
    for tei in Radio.objects.values_list("TEI", flat=True):
        tei_str = str(tei)
        url = reverse("radio:detail", kwargs={"pk": tei})
        lookup[tei_str] = url
        lookup[tei_str.zfill(14)] = url
        lookup[f"{tei_str.zfill(14)}0"] = url
    return lookup
