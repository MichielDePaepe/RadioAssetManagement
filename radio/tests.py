from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override

from .models import Radio, RadioModel, TEIRange


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
