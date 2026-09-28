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


class DeactivationWorkflowTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Permission
        activate("nl")
        TicketStatus.objects.get_or_create(code="NEW", defaults={"name": "New", "default": True})
        model = RadioModel.objects.create(name="Test radio")
        TEIRange.objects.create(model=model, min_tei=750000000000000, max_tei=750000000000999)
        self.radio = Radio.objects.create(TEI=750000000000001)
        self.issi = ISSI.objects.create(number=1000001)
        Subscription.objects.create(radio=self.radio, issi=self.issi)
        self.requester = User.objects.create_user(username="requester")
        self.operator = User.objects.create_user(username="operator")
        self.verifier = User.objects.create_user(username="verifier")
        self.operator.user_permissions.add(Permission.objects.get(content_type__app_label="astrid", codename="has_access_to_myastrid"))
        self.verifier.user_permissions.add(Permission.objects.get(content_type__app_label="astrid", codename="can_verify_requests"))
        self.client.force_login(self.requester)
        self.create_url = reverse("astrid:deactivation_request")

    def create_request(self):
        self.client.post(self.create_url, {"radio": self.radio.pk, "request_description": "Stop abonnement"})
        obj = Request.objects.get()
        self.url = reverse("astrid:request_detail", kwargs={"pk": obj.pk})
        return obj

    def submit(self):
        self.client.force_login(self.operator)
        return self.client.post(self.url, {"type": "astrid_request_submitted", "action": "request_submitted", "astrid_ticket": "AST-123"})

    def process(self):
        return self.client.post(self.url, {"type": "feedback_from_astrid", "action": "processed"})

    def verify(self, action="radio_inactive", note="Getest op netwerk"):
        return self.client.post(self.url, {"type": "validate_deactivation", "action": action, "note": note})

    def test_full_flow_deletes_subscription_only_after_successful_validation(self):
        obj = self.create_request()
        self.assertEqual(obj.created_by, self.requester)
        self.assertEqual(obj.old_issi, self.issi)
        self.submit()
        obj.refresh_from_db()
        self.assertEqual(obj.status.code, "IN_PROGRESS")
        self.assertEqual(obj.external_reference, "AST-123")
        self.process()
        obj.refresh_from_db()
        self.assertEqual(obj.status.code, "WAITING_VERIFICATION")
        self.assertTrue(Subscription.objects.filter(radio=self.radio).exists())
        self.client.force_login(self.verifier)
        response = self.client.get(self.url)
        self.assertContains(response, 'value="radio_inactive"')
        self.assertContains(response, "Radio niet meer actief")
        self.assertContains(response, "Radio nog steeds actief")
        self.verify("radio_active")
        obj.refresh_from_db()
        self.assertEqual(obj.status.code, "WAITING_VERIFICATION")
        self.assertTrue(Subscription.objects.filter(radio=self.radio).exists())
        self.verify()
        obj.refresh_from_db()
        self.assertEqual(obj.status.code, "CLOSED")
        self.assertFalse(Subscription.objects.filter(radio=self.radio).exists())
        self.assertTrue(Radio.objects.filter(pk=self.radio.pk).exists())
        self.assertTrue(ISSI.objects.filter(pk=self.issi.pk).exists())
        count = obj.logs.count()
        self.verify()
        self.assertEqual(obj.logs.count(), count)

    def test_permissions_and_out_of_order_actions(self):
        obj = self.create_request()
        self.assertEqual(self.client.post(self.url, {"type": "feedback_from_astrid", "action": "processed"}).status_code, 403)
        self.client.force_login(self.verifier)
        self.verify()
        obj.refresh_from_db()
        self.assertEqual(obj.status.code, "NEW")
        self.submit()
        self.process()
        self.assertEqual(self.verify().status_code, 403)
        self.assertTrue(Subscription.objects.filter(radio=self.radio).exists())

    def test_refusal_preserves_subscription(self):
        obj = self.create_request()
        self.submit()
        self.client.post(self.url, {"type": "feedback_from_astrid", "action": "refused", "note": "Geweigerd door ASTRID"})
        obj.refresh_from_db()
        self.assertEqual(obj.status.code, "CLOSED")
        self.assertTrue(Subscription.objects.filter(radio=self.radio).exists())
        self.assertIn("geweigerd", obj.logs.last().note)

    def test_changed_subscription_is_not_deleted(self):
        obj = self.create_request()
        self.submit()
        self.process()
        replacement = ISSI.objects.create(number=1000002)
        Subscription.objects.filter(radio=self.radio).update(issi=replacement)
        self.client.force_login(self.verifier)
        self.verify()
        obj.refresh_from_db()
        self.assertEqual(obj.status.code, "WAITING_VERIFICATION")
        self.assertEqual(Subscription.objects.get(radio=self.radio).issi, replacement)

    def test_duplicate_inactive_and_anonymous_requests_are_rejected(self):
        self.assertContains(self.client.get(self.create_url), "Desactivatie aanvragen")
        self.create_request()
        self.client.post(self.create_url, {"radio": self.radio.pk})
        self.assertEqual(Request.objects.count(), 1)
        Request.objects.all().delete()
        Subscription.objects.all().delete()
        self.client.post(self.create_url, {"radio": self.radio.pk})
        self.assertFalse(Request.objects.exists())
        self.client.logout()
        self.assertEqual(self.client.post(self.create_url, {"radio": self.radio.pk}).status_code, 302)
        self.assertFalse(Request.objects.exists())

    def test_required_reference_note_and_invalid_action(self):
        obj = self.create_request()
        self.client.force_login(self.operator)
        self.client.post(self.url, {"type": "astrid_request_submitted", "action": "request_submitted"})
        obj.refresh_from_db()
        self.assertEqual(obj.status.code, "NEW")
        self.assertEqual(self.client.post(self.url, {"type": "astrid_request_submitted", "action": "unknown"}).status_code, 400)
        self.submit()
        self.process()
        self.client.force_login(self.verifier)
        self.verify(note="   ")
        obj.refresh_from_db()
        self.assertEqual(obj.status.code, "WAITING_VERIFICATION")
        self.assertTrue(Subscription.objects.filter(radio=self.radio).exists())

    def test_validation_after_import_already_removed_subscription(self):
        obj = self.create_request()
        self.submit()
        self.process()
        Subscription.objects.all().delete()
        self.client.force_login(self.verifier)
        self.verify()
        obj.refresh_from_db()
        self.assertEqual(obj.status.code, "CLOSED")
