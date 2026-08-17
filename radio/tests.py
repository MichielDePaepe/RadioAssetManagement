from unittest.mock import patch
import json

from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override

from .models import ISSI, Radio, RadioModel, Subscription, TEIRange


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
