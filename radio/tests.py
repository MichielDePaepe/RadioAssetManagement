from unittest.mock import patch
import json

from django.test import TestCase
from django.contrib.auth.models import Permission, User
from django.urls import reverse
from django.utils.translation import override

from helpdesk.models import Ticket, TicketStatus, TicketType
from fireplan.models import Vehicle
from printer.models import Printer

from .services.image_service import ImageGenerator
from .models import ISSI, Radio, RadioDecommissioningTicket, RadioModel, Subscription, TEIRange


class RadioCreateViewTests(TestCase):
    def setUp(self):
        self.radio_model = RadioModel.objects.create(name="Portable")
        TEIRange.objects.create(
            model=self.radio_model,
            min_tei=75060200000,
            max_tei=75060300009,
        )

    @patch("radio.views.FireplanClient")
    def test_creates_missing_fireplan_radio_with_padded_tei(self, fireplan_client):
        fireplan_client.return_value.get_or_create_radio_fireplan_id.return_value = (
            1234,
            True,
        )

        with override("fr"):
            response = self.client.post(
                reverse("radio:create"),
                {
                    "TEI": "000075060235950",
                },
            )

        self.assertEqual(response.status_code, 302)
        fireplan_client.return_value.get_or_create_radio_fireplan_id.assert_called_once_with(
            "000075060235950"
        )

        radio = Radio.objects.get(TEI=75060235950)
        self.assertEqual(radio.fireplan_id, 1234)

    @patch("radio.views.FireplanClient")
    def test_uses_full_scanned_tei_for_fireplan_when_check_digit_is_not_zero(self, fireplan_client):
        TEIRange.objects.create(
            model=self.radio_model,
            min_tei=75190000000,
            max_tei=75199999999,
        )
        fireplan_client.return_value.get_or_create_radio_fireplan_id.return_value = (
            1287,
            False,
        )

        with override("fr"):
            response = self.client.post(
                reverse("radio:create"),
                {
                    "TEI": "000075190060667",
                },
            )

        self.assertEqual(response.status_code, 302)
        fireplan_client.return_value.get_or_create_radio_fireplan_id.assert_called_once_with(
            "000075190060667"
        )

        radio = Radio.objects.get(TEI=75190060667)
        self.assertEqual(radio.fireplan_id, 1287)


class DecommissioningRequestTests(TestCase):
    def setUp(self):
        self.radio_model = RadioModel.objects.create(name="Portable")
        TEIRange.objects.create(
            model=self.radio_model,
            min_tei=75000000000,
            max_tei=75999999999,
        )
        self.radio = Radio.objects.create(TEI=75000000001)
        self.status = TicketStatus.objects.create(code="OPEN", name="Open", default=True)
        self.closed_status, _ = TicketStatus.objects.get_or_create(code="CLOSED", defaults={"name": "Closed"})
        self.user = User.objects.create_user(username="decommissioner", password="secret")
        permission = Permission.objects.get(codename="can_create_decommission_requests")
        self.user.user_permissions.add(permission)
        self.approver = User.objects.create_user(username="decommission-approver", password="secret")
        approve_permission = Permission.objects.get(codename="can_approve_decommission_requests")
        self.approver.user_permissions.add(approve_permission)

    def test_detail_shows_decommission_button_for_authorized_user(self):
        self.client.force_login(self.user)

        with override("nl"):
            detail_url = reverse("radio:detail", kwargs={"pk": self.radio.pk})
            decommission_url = reverse("radio:decommissioning_request_for_radio", kwargs={"pk": self.radio.pk})
            response = self.client.get(detail_url)

        self.assertContains(response, decommission_url)

    def test_detail_hides_decommission_button_without_permission(self):
        self.client.force_login(User.objects.create_user(username="viewer", password="secret"))

        with override("nl"):
            detail_url = reverse("radio:detail", kwargs={"pk": self.radio.pk})
            decommission_url = reverse("radio:decommissioning_request_for_radio", kwargs={"pk": self.radio.pk})
            response = self.client.get(detail_url)

        self.assertNotContains(response, decommission_url)
        self.assertNotContains(response, "Buiten dienst stellen")

    def test_request_creates_decommissioning_ticket_with_reason_and_user(self):
        self.client.force_login(self.user)

        with override("nl"):
            response = self.client.post(
                reverse("radio:decommissioning_request_for_radio", kwargs={"pk": self.radio.pk}),
                {"description": "Defect toestel, niet meer herstelbaar."},
            )

        ticket = RadioDecommissioningTicket.objects.get()
        with override("nl"):
            self.assertRedirects(response, reverse("helpdesk:ticket_detail", kwargs={"pk": ticket.pk}))
        self.assertEqual(ticket.radio, self.radio)
        self.assertEqual(ticket.created_by, self.user)
        self.assertEqual(ticket.ticket_type.code, "DECOMMISSIONING")
        self.assertEqual(ticket.description, "Defect toestel, niet meer herstelbaar.")
        self.assertIn(self.radio.tei_str, ticket.title)

    def test_request_blocks_second_open_decommissioning_ticket(self):
        self.client.force_login(self.user)
        RadioDecommissioningTicket.objects.create(
            radio=self.radio,
            description="Eerste aanvraag.",
            created_by=self.user,
        )

        with override("nl"):
            response = self.client.post(
                reverse("radio:decommissioning_request_for_radio", kwargs={"pk": self.radio.pk}),
                {"description": "Tweede aanvraag."},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(RadioDecommissioningTicket.objects.count(), 1)
        self.assertContains(response, "open decommissioning request")

    def test_approve_decommissioning_marks_radio_decommissioned_and_closes_ticket(self):
        ticket = RadioDecommissioningTicket.objects.create(
            radio=self.radio,
            description="Defect toestel.",
            created_by=self.user,
        )
        self.client.force_login(self.approver)

        with override("nl"):
            response = self.client.post(
                reverse("helpdesk:ticket_detail", kwargs={"pk": ticket.pk}),
                {"approve_decommissioning": "1"},
            )

        with override("nl"):
            self.assertRedirects(response, reverse("helpdesk:ticket_detail", kwargs={"pk": ticket.pk}))
        self.radio.refresh_from_db()
        ticket.refresh_from_db()
        self.assertTrue(self.radio.decommissioned)
        self.assertEqual(ticket.status.code, "CLOSED")
        self.assertEqual(ticket.logs.count(), 1)
        self.assertEqual(ticket.logs.first().user, self.approver)

    def test_approve_decommissioning_requires_permission(self):
        ticket = RadioDecommissioningTicket.objects.create(
            radio=self.radio,
            description="Defect toestel.",
            created_by=self.user,
        )
        self.client.force_login(self.user)

        with override("nl"):
            response = self.client.post(
                reverse("helpdesk:ticket_detail", kwargs={"pk": ticket.pk}),
                {"approve_decommissioning": "1"},
            )

        self.assertEqual(response.status_code, 403)
        self.radio.refresh_from_db()
        self.assertFalse(self.radio.decommissioned)


class DecommissionedLabelTests(TestCase):
    def setUp(self):
        self.radio_model = RadioModel.objects.create(name="Portable")
        TEIRange.objects.create(
            model=self.radio_model,
            min_tei=75000000000,
            max_tei=75999999999,
        )
        self.radio = Radio.objects.create(TEI=75000000001, decommissioned=True)
        self.user = User.objects.create_user(username="label-user", password="secret")

    def test_decommissioned_label_matches_tei_label_height_and_uses_warning_colors(self):
        generator = ImageGenerator(self.radio)

        tei_img = generator.portable_radio_tei_label(color_dark=(0, 0, 0), color_light=(255, 255, 0))
        label_img = generator.decommissioned_label(color_dark=(0, 0, 0), color_light=(255, 255, 0))
        label_colors = [color for count, color in label_img.getcolors(maxcolors=1000000)]

        self.assertEqual(label_img.height, tei_img.height)
        self.assertGreater(label_img.width, tei_img.width)
        self.assertIn((0, 0, 0), label_colors)
        self.assertIn((255, 255, 0), label_colors)

    def test_detail_shows_decommissioned_label_for_decommissioned_radio(self):
        self.client.force_login(self.user)

        with override("nl"):
            response = self.client.get(reverse("radio:detail", kwargs={"pk": self.radio.pk}))

        self.assertContains(response, "decommissioned_label")
        self.assertContains(response, "Decommissioned-label")

    def test_detail_links_vehicle_to_inventory_vehicle_page(self):
        vehicle = Vehicle.objects.create(number="A106 - Test", radio=self.radio)
        self.client.force_login(self.user)

        with override("nl"):
            response = self.client.get(reverse("radio:detail", kwargs={"pk": self.radio.pk}))
            vehicle_url = reverse("inventory:vehicle_radio_detail", args=[vehicle.pk])

        self.assertContains(response, vehicle_url)
        self.assertContains(response, "A106 - Test")

    @patch("radio.views.RadioPrintingService")
    def test_prints_decommissioned_label(self, print_service):
        printer = Printer.objects.create(
            name="Test printer",
            device="QL-800",
            ip="127.0.0.1",
        )
        print_service.return_value.print_decommissioned_label.return_value = "Printed"

        with override("nl"):
            detail_url = reverse("radio:detail", kwargs={"pk": self.radio.pk})
            response = self.client.post(
                detail_url,
                {
                    "printer_id": printer.pk,
                    "copies": "2",
                    "action": "decommissioned",
                },
            )

        self.assertRedirects(response, detail_url)
        print_service.return_value.print_decommissioned_label.assert_called_once_with("2")


class RadioListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="radio-list-user", password="secret")
        self.radio_model = RadioModel.objects.create(name="Portable")
        self.mobile_model = RadioModel.objects.create(name="Mobile", radio_type=RadioModel.RadioType.MOBILE)
        TEIRange.objects.create(
            model=self.radio_model,
            min_tei=75000000000,
            max_tei=75999999999,
        )
        TEIRange.objects.create(
            model=self.mobile_model,
            min_tei=76000000000,
            max_tei=76999999999,
        )
        self.open_status = TicketStatus.objects.create(code="OPEN", name="Open", default=True)
        self.ticket_type = TicketType.objects.create(code="INCIDENT", name="Incident")

        self.active_radio = Radio.objects.create(TEI=75000000001)
        active_issi = ISSI.objects.create(number=1234567, alias="A101")
        Subscription.objects.create(radio=self.active_radio, issi=active_issi)

        self.dmo_radio = Radio.objects.create(TEI=75000000002)
        dmo_issi = ISSI.objects.create(number=1234568, alias="D102")
        Subscription.objects.create(radio=self.dmo_radio, issi=dmo_issi, DMO_only=True)

        self.inactive_radio = Radio.objects.create(TEI=75000000003)
        self.decommissioned_radio = Radio.objects.create(TEI=75000000004, decommissioned=True)
        self.mobile_radio = Radio.objects.create(TEI=76000000001)

        Ticket.objects.create(
            radio=self.active_radio,
            ticket_type=self.ticket_type,
            status=self.open_status,
            title="Broken antenna",
            description="Needs repair",
            created_by=self.user,
        )

    def get_radio_list(self, query_string=""):
        self.client.force_login(self.user)
        with override("nl"):
            url = reverse("radio:list")
            if query_string:
                url = f"{url}?{query_string}"
            return self.client.get(url)

    def test_radio_list_shows_core_radio_information(self):
        response = self.get_radio_list()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.active_radio.tei_str)
        self.assertContains(response, "A101")
        with override("nl"):
            self.assertContains(response, reverse("radio:detail", kwargs={"pk": self.active_radio.pk}))
            self.assertContains(response, reverse("radio:issi_alias_edit", kwargs={"pk": 1234567}))
        listed_active_radio = next(radio for radio in response.context["radios"] if radio.pk == self.active_radio.pk)
        self.assertEqual(listed_active_radio.ticket_count, 1)

    def test_radio_list_filters_by_status(self):
        response = self.get_radio_list("status=dmo")

        listed_pks = {radio.pk for radio in response.context["radios"]}
        self.assertEqual(listed_pks, {self.dmo_radio.pk})

    def test_radio_list_searches_by_alias(self):
        response = self.get_radio_list("q=A101")

        listed_pks = {radio.pk for radio in response.context["radios"]}
        self.assertEqual(listed_pks, {self.active_radio.pk})

    def test_radio_list_filters_by_radio_type(self):
        response = self.get_radio_list(f"model={self.mobile_model.pk}")

        listed_pks = {radio.pk for radio in response.context["radios"]}
        self.assertEqual(listed_pks, {self.mobile_radio.pk})
        self.assertEqual(response.context["selected_model"], str(self.mobile_model.pk))

    def test_radio_list_combines_type_and_status_filters(self):
        response = self.get_radio_list(f"model={self.radio_model.pk}&status=dmo")

        listed_pks = {radio.pk for radio in response.context["radios"]}
        self.assertEqual(listed_pks, {self.dmo_radio.pk})


class RadioSelectorLookupTests(TestCase):
    def setUp(self):
        self.radio_model = RadioModel.objects.create(name="Portable")
        TEIRange.objects.create(
            model=self.radio_model,
            min_tei=75000000000,
            max_tei=75999999999,
        )
        TEIRange.objects.create(
            model=self.radio_model,
            min_tei=88000000000,
            max_tei=88999999999,
        )
        self.radio = Radio.objects.create(TEI=75000000001, fireplan_id=4321)
        self.issi = ISSI.objects.create(number=1234567, alias="P101")
        Subscription.objects.create(radio=self.radio, issi=self.issi)
        self.reported_radio = Radio.objects.create(TEI=88060594070, fireplan_id=821)

    def lookup_url(self, name):
        with override("en"):
            return reverse(name)

    def test_lookup_auto_finds_radio_by_tei(self):
        response = self.client.post(
            self.lookup_url("radio:lookup"),
            {"type": "auto", "value": "000075000000001"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["TEI"], self.radio.TEI)

    def test_lookup_auto_finds_radio_by_issi(self):
        response = self.client.post(
            self.lookup_url("radio:lookup"),
            {"type": "auto", "value": "1234567"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["TEI"], self.radio.TEI)

    def test_lookup_auto_finds_radio_by_alias(self):
        response = self.client.post(
            self.lookup_url("radio:lookup"),
            {"type": "auto", "value": "p101"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["TEI"], self.radio.TEI)

    def test_scan_finds_radio_by_qr_url(self):
        response = self.client.post(
            self.lookup_url("radio:scan"),
            data=json.dumps({
                "scanned_line": "https://infoscan.firebru.brussels?data=1,1,4321,1010",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["TEI"], self.radio.TEI)

    def test_scan_finds_radio_by_qr_url_with_keyboard_mismatch(self):
        response = self.client.post(
            self.lookup_url("radio:scan"),
            data=json.dumps({
                "scanned_line": "httpsM==infoscqn:firebru:brussels+dqtq-&;&;’\"é&;&à&à",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["TEI"], self.radio.TEI)

    def test_scan_finds_reported_radio_with_qwerty_scanner_output(self):
        response = self.client.post(
            self.lookup_url("radio:scan"),
            data=json.dumps({
                "scanned_line": "https.>>infoscqn<firebru<brusselsMdqtq/!m!m*@!m!)!)",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["TEI"], self.reported_radio.TEI)

    def test_scan_finds_reported_radio_with_shifted_digit_variant(self):
        response = self.client.post(
            self.lookup_url("radio:scan"),
            data=json.dumps({
                "scanned_line": "https.>>infoscqn<firebru<brusselsMdqtq/!m!m$&*m!)!)",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["TEI"], self.reported_radio.TEI)

    def test_scan_finds_radio_by_tei_barcode(self):
        response = self.client.post(
            self.lookup_url("radio:scan"),
            data=json.dumps({"scanned_line": "000075000000001"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["TEI"], self.radio.TEI)

    def test_scan_finds_radio_by_shifted_qwerty_tei_barcode(self):
        response = self.client.post(
            self.lookup_url("radio:scan"),
            data=json.dumps({"scanned_line": "))))**)^)%($)&)"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["TEI"], self.reported_radio.TEI)

    def test_scan_finds_radio_when_shifted_qwerty_tei_barcode_is_duplicated(self):
        response = self.client.post(
            self.lookup_url("radio:scan"),
            data=json.dumps({"scanned_line": "))))**)^)%($)&)))))**)^)%($)&)"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["TEI"], self.reported_radio.TEI)
