from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import override

from printer.models import Printer
from radio.templatetags.radio_selector_tags import render_radio_links
from radio.models import ISSI, Radio, RadioModel, Subscription, TEIRange

from .models import Ticket, TicketStatus, TicketType
from .services.printing import TicketPrintingService


class RenderRadioLinksTests(TestCase):
    def setUp(self):
        model = RadioModel.objects.create(name="Test radio")
        TEIRange.objects.create(
            model=model,
            min_tei=750000000000000,
            max_tei=750000000000999,
        )
        self.radio = Radio.objects.create(TEI=750000000000001)
        issi = ISSI.objects.create(number=1234567, alias="TEST")
        Subscription.objects.create(radio=self.radio, issi=issi)

    def test_links_existing_tei_to_radio_detail_with_radio_label(self):
        rendered = render_radio_links("Controleer 750000000000001 aub")

        self.assertIn(reverse("radio:detail", kwargs={"pk": self.radio.pk}), rendered)
        self.assertIn(str(self.radio), rendered)

    def test_can_render_title_text_with_known_tei(self):
        rendered = render_radio_links("Probleem met 750000000000001")

        self.assertIn("<a ", rendered)
        self.assertIn(str(self.radio), rendered)

    def test_leaves_unknown_tei_as_plain_text(self):
        rendered = render_radio_links("Controleer 750000000000999 aub")

        self.assertNotIn("<a ", rendered)
        self.assertIn("750000000000999", rendered)

    def test_leaves_unknown_tei_with_leading_zeroes_as_plain_text(self):
        rendered = render_radio_links("Controleer 000098061050370 aub")

        self.assertNotIn("<a ", rendered)
        self.assertIn("000098061050370", rendered)

    def test_escapes_note_html(self):
        rendered = render_radio_links("<script>alert(1)</script> 750000000000001")

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertNotIn("<script>", rendered)

    def test_escapes_text_without_tei(self):
        rendered = render_radio_links("<strong>geen radio</strong>")

        self.assertEqual(rendered, escape("<strong>geen radio</strong>"))


class TicketLabelPrintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ticket-label-user", password="secret")
        model = RadioModel.objects.create(name="Test radio")
        TEIRange.objects.create(
            model=model,
            min_tei=750000000000000,
            max_tei=750000000000999,
        )
        self.radio = Radio.objects.create(TEI=750000000000001)
        self.status = TicketStatus.objects.create(code="OPEN", name="Open", default=True)
        self.ticket_type = TicketType.objects.create(code="INCIDENT", name="Incident")
        self.ticket = Ticket.objects.create(
            radio=self.radio,
            ticket_type=self.ticket_type,
            status=self.status,
            title="Defect",
            description="Test",
            created_by=self.user,
        )

    def test_ticket_number_label_is_12mm_high_with_black_text_on_white(self):
        printer = Printer(name="Test printer", device="QL-800", ip="127.0.0.1")
        label = TicketPrintingService(self.ticket, printer).ticket_number_label()
        colors = [color for count, color in label.getcolors(maxcolors=1000000)]

        self.assertEqual(label.height, int(12 * 360 / 25.4))
        self.assertIn((255, 255, 255), colors)
        self.assertIn((0, 0, 0), colors)

    def test_ticket_detail_shows_printer_modal_when_multiple_printers_exist(self):
        self.client.force_login(self.user)
        Printer.objects.create(name="Printer 1", device="QL-800", ip="127.0.0.1")
        Printer.objects.create(name="Printer 2", device="QL-800", ip="127.0.0.2")

        with override("nl"):
            response = self.client.get(reverse("helpdesk:ticket_detail", kwargs={"pk": self.ticket.pk}))

        self.assertContains(response, "Print ticketlabel")
        self.assertContains(response, "ticketLabelPrinterModal")
        self.assertContains(response, "Printer 1")
        self.assertContains(response, "Printer 2")

    @patch("helpdesk.views.TicketPrintingService")
    def test_print_ticket_label_posts_to_selected_printer_without_real_printing(self, printing_service):
        self.client.force_login(self.user)
        printer = Printer.objects.create(name="Test printer", device="QL-800", ip="127.0.0.1")
        printing_service.return_value.print_ticket_number_label.return_value = "Printed"

        with override("nl"):
            detail_url = reverse("helpdesk:ticket_detail", kwargs={"pk": self.ticket.pk})
            response = self.client.post(
                detail_url,
                {
                    "print_ticket_label": "1",
                    "printer_id": printer.pk,
                },
            )

        self.assertRedirects(response, detail_url)
        printing_service.assert_called_once_with(self.ticket, printer)
        printing_service.return_value.print_ticket_number_label.assert_called_once_with()
