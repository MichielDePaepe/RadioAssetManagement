from django.test import TestCase
from django.urls import reverse
from django.utils.translation import activate

from helpdesk.models import TicketStatus
from radio.models import ISSI, Radio, RadioModel, Subscription, TEIRange

from .models import Request


class VTEIRequestCreateViewTests(TestCase):
    def setUp(self):
        activate("en")
        TicketStatus.objects.get_or_create(
            code="NEW",
            defaults={"name": "New", "default": True},
        )
        self.model = RadioModel.objects.create(name="Test radio")
        TEIRange.objects.create(
            model=self.model,
            min_tei=750000000000000,
            max_tei=750000000000999,
        )
        self.old_radio = Radio.objects.create(TEI=750000000000001)
        self.new_radio = Radio.objects.create(TEI=750000000000002)
        self.old_issi = ISSI.objects.create(number=1000001)
        self.new_issi = ISSI.objects.create(number=1000002)
        Subscription.objects.create(radio=self.old_radio, issi=self.old_issi)

    def test_vtei_request_keeps_existing_issi(self):
        response = self.client.post(
            reverse("astrid:vtei_request"),
            {
                "old-radio": self.old_radio.pk,
                "new-radio": self.new_radio.pk,
                "request_description": "Swap device",
            },
        )

        request = Request.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(request.request_type, Request.RequestType.VTEI)
        self.assertEqual(request.old_issi, self.old_issi)
        self.assertEqual(request.new_issi, self.old_issi)

    def test_vissi_vtei_request_uses_new_issi(self):
        response = self.client.post(
            reverse("astrid:vissi_vtei_request"),
            {
                "request_type": Request.RequestType.VISSI_VTEI,
                "old-radio": self.old_radio.pk,
                "new-radio": self.new_radio.pk,
                "new-issi": self.new_issi.pk,
                "request_description": "Swap device and ISSI",
            },
        )

        request = Request.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(request.request_type, Request.RequestType.VISSI_VTEI)
        self.assertEqual(request.old_issi, self.old_issi)
        self.assertEqual(request.new_issi, self.new_issi)
