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
        self.new_issi = ISSI.objects.create(number=1000002, alias="NEW")
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

    def test_vissi_request_keeps_same_radio_and_uses_new_issi(self):
        new_issi_number = 1000003

        response = self.client.post(
            reverse("astrid:vissi_request"),
            {
                "request_type": Request.RequestType.VISSI,
                "old-radio": self.old_radio.pk,
                "new-issi": new_issi_number,
                "request_description": "Change ISSI",
            },
        )

        request = Request.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("astrid:request_detail", kwargs={"pk": request.pk}))
        self.assertEqual(request.request_type, Request.RequestType.VISSI)
        self.assertEqual(request.old_radio, self.old_radio)
        self.assertEqual(request.new_radio, self.old_radio)
        self.assertEqual(request.old_issi, self.old_issi)
        self.assertEqual(request.new_issi.number, new_issi_number)

    def test_vissi_request_page_renders_single_radio_selector(self):
        response = self.client.get(reverse("astrid:vissi_request"))

        self.assertContains(response, "VISSI")
        self.assertContains(response, "Radio")
        self.assertContains(response, "Nieuwe ISSI")
        self.assertContains(response, "data-issi-typeahead")
        self.assertNotContains(response, "Nieuwe radio")

    def test_vissi_vtei_request_page_uses_issi_typeahead(self):
        response = self.client.get(reverse("astrid:vissi_vtei_request"))

        self.assertContains(response, "Nieuwe ISSI")
        self.assertContains(response, "data-issi-typeahead")
        self.assertContains(response, reverse("astrid:issi_suggestions"))

    def test_activation_request_page_uses_issi_typeahead(self):
        response = self.client.get(reverse("astrid:activation_request"))

        self.assertContains(response, "ISSI")
        self.assertContains(response, "data-issi-typeahead")
        self.assertContains(response, reverse("astrid:issi_suggestions"))

    def test_vissi_request_rejects_active_new_issi(self):
        active_radio = Radio.objects.create(TEI=750000000000003)
        active_issi = ISSI.objects.create(number=1000004, alias="ACTIVE")
        Subscription.objects.create(radio=active_radio, issi=active_issi)

        response = self.client.post(
            reverse("astrid:vissi_request"),
            {
                "request_type": Request.RequestType.VISSI,
                "old-radio": self.old_radio.pk,
                "new-issi": active_issi.number,
                "request_description": "Change ISSI",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Request.objects.exists())

    def test_issi_suggestions_search_by_number_and_alias(self):
        response = self.client.get(reverse("astrid:issi_suggestions"), {"q": "NEW"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"][0],
            {
                "number": "1000002",
                "alias": "NEW",
                "label": "1000002 (NEW)",
                "is_active": False,
            },
        )

    def test_issi_suggestions_mark_active_issi(self):
        response = self.client.get(reverse("astrid:issi_suggestions"), {"q": "1000001"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["results"][0]["is_active"])

    def test_request_detail_shows_new_issi_alias_as_copy_field(self):
        request = Request.objects.create(
            request_type=Request.RequestType.VISSI,
            old_radio=self.old_radio,
            old_issi=self.old_issi,
            new_issi=self.new_issi,
            radio=self.old_radio,
            description="Swap ISSI",
        )

        response = self.client.get(reverse("astrid:request_detail", kwargs={"pk": request.pk}))

        self.assertContains(response, 'value="NEW"')
        self.assertContains(response, 'data-copy-value="NEW"')

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
