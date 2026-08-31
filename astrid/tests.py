from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import activate

from helpdesk.models import TicketStatus
from helpdesk.services.printing import TicketPrintingService
from printer.models import Printer
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

    def test_ticket_label_text_includes_astrid_request_type(self):
        request = Request.objects.create(
            request_type=Request.RequestType.VTEI,
            old_radio=self.old_radio,
            old_issi=self.old_issi,
            new_issi=self.old_issi,
            radio=self.new_radio,
            description="Swap device",
        )
        printer = Printer(name="Test printer", device="QL-800", ip="127.0.0.1")

        self.assertEqual(TicketPrintingService(request, printer).label_text(), f"VTEI #{request.pk}")

    def test_request_detail_shows_printer_modal_when_multiple_printers_exist(self):
        user = User.objects.create_user(username="astrid-label-user", password="secret")
        self.client.force_login(user)
        Printer.objects.create(name="Printer 1", device="QL-800", ip="127.0.0.1")
        Printer.objects.create(name="Printer 2", device="QL-800", ip="127.0.0.2")
        request = Request.objects.create(
            request_type=Request.RequestType.VISSI,
            old_radio=self.old_radio,
            old_issi=self.old_issi,
            new_issi=self.new_issi,
            radio=self.old_radio,
            description="Swap ISSI",
        )

        response = self.client.get(reverse("astrid:request_detail", kwargs={"pk": request.pk}))

        self.assertContains(response, "Print ticket label")
        self.assertContains(response, "ticketLabelPrinterModal")
        self.assertContains(response, "Printer 1")
        self.assertContains(response, "Printer 2")

    @patch("astrid.views.TicketPrintingService")
    def test_request_detail_prints_label_without_real_printing(self, printing_service):
        user = User.objects.create_user(username="astrid-print-user", password="secret")
        self.client.force_login(user)
        printer = Printer.objects.create(name="Test printer", device="QL-800", ip="127.0.0.1")
        request = Request.objects.create(
            request_type=Request.RequestType.VISSI_VTEI,
            old_radio=self.old_radio,
            old_issi=self.old_issi,
            new_issi=self.new_issi,
            radio=self.new_radio,
            description="Swap radio and ISSI",
        )
        printing_service.return_value.print_ticket_number_label.return_value = "Printed"

        detail_url = reverse("astrid:request_detail", kwargs={"pk": request.pk})
        response = self.client.post(
            detail_url,
            {
                "print_ticket_label": "1",
                "printer_id": printer.pk,
            },
        )

        self.assertRedirects(response, detail_url)
        printing_service.assert_called_once_with(request, printer)
        printing_service.return_value.print_ticket_number_label.assert_called_once_with()
