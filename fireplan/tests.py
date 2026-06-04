from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from radio.models import Radio, RadioModel, TEIRange

from .models import FireplanInventory, Vector, Vehicle
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


class FireplanInventoryHistoryViewTests(TestCase):
    def setUp(self):
        self.vehicle = Vehicle.objects.create(
            id=1,
            number="CIT 01 - Test",
            num_letter="CIT",
            num_value=1,
            plate="TEST-1",
            utilisation="Test",
            chassis="CHASSIS",
            status=1,
        )
        self.vector = Vector.objects.create(
            resourceCode="CIT01",
            vehicle=self.vehicle,
            name="Citerne 01",
        )
        self.inventory = FireplanInventory.objects.create(
            uuid=uuid4(),
            vehicle_alpha_code=self.vehicle.number,
            vehicle=self.vehicle,
            vector=self.vector,
            closed_at=timezone.now(),
            done_by_full_name="Scanner Test",
        )

    def test_overview_links_vector_to_inventory_history(self):
        with override("nl"):
            response = self.client.get(reverse("fireplan:latest_inventory_per_vector"))
            history_url = reverse("fireplan:vector_inventory_history", args=[self.vector.pk])

        self.assertContains(response, history_url)

    def test_vector_inventory_history_shows_vehicle_and_scanner(self):
        with override("nl"):
            response = self.client.get(
                reverse("fireplan:vector_inventory_history", args=[self.vector.pk])
            )

        self.assertContains(response, "Citerne 01")
        self.assertContains(response, "CIT 01")
        self.assertContains(response, "Scanner Test")
