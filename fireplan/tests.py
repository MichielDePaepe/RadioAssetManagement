from django.test import TestCase

from radio.models import Radio, RadioModel, TEIRange

from .sync_inventory import find_radio_for_fireplan_tei


class FireplanInventoryTEIMatchingTests(TestCase):
    def setUp(self):
        radio_model = RadioModel.objects.create(name="Portable")
        TEIRange.objects.create(
            model=radio_model,
            min_tei=75060200000,
            max_tei=75060300009,
        )
        TEIRange.objects.create(
            model=radio_model,
            min_tei=75190000000,
            max_tei=75199999999,
        )

    def test_finds_radio_for_current_15_digit_fireplan_tei(self):
        radio = Radio.objects.create(TEI=75190060667)

        found = find_radio_for_fireplan_tei("000075190060667")

        self.assertEqual(found, radio)

    def test_finds_radio_for_legacy_14_digit_fireplan_tei_missing_trailing_zero(self):
        radio = Radio.objects.create(TEI=75060235950)

        found = find_radio_for_fireplan_tei("00007506023595")

        self.assertEqual(found, radio)

    def test_exact_match_wins_when_fireplan_tei_is_15_digits(self):
        exact_radio = Radio.objects.create(TEI=75060235951)
        Radio.objects.create(TEI=75060235950)

        found = find_radio_for_fireplan_tei("000075060235951")

        self.assertEqual(found, exact_radio)
