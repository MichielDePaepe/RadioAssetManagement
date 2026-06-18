from uuid import uuid4
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from radio.models import ISSI, Radio, RadioModel, TEIRange

from .models import FireplanInventory, FireplanInventoryRadio, Vector, Vehicle, VehicleStatus
from .sync import _match_or_create_vehicle_from_vector_item, sync_fireplan_fleet
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

    def test_finds_radio_when_fireplan_legacy_tei_is_json_number(self):
        radio = Radio.objects.create(TEI=75060235950)

        found = find_radio_for_fireplan_tei(7506023595)

        self.assertEqual(found, radio)

    def test_exact_match_wins_when_fireplan_tei_is_15_digits(self):
        exact_radio = Radio.objects.create(TEI=75060235951)
        Radio.objects.create(TEI=75060235950)

        found = find_radio_for_fireplan_tei("000075060235951")

        self.assertEqual(found, exact_radio)


class VehicleSyncTests(TestCase):
    def test_vector_item_creates_missing_vehicle_without_fireplan_id(self):
        item = {
            "ResourceCode": "2-HBY-020",
            "Name": "A106",
            "IsActive": 1,
            "firstLetter": "A",
            "pName": "PIT ANDERLECHT 1 BRA",
            "pAbbreviation": "A-ANDPIT-BRA",
            "orderServiceAbbreviation": "AND Bracops PIT",
            "numericalAlphaCode": 106,
        }

        vehicle = _match_or_create_vehicle_from_vector_item(item)

        self.assertIsNotNone(vehicle)
        self.assertIsNone(vehicle.fireplan_id)
        self.assertEqual(vehicle.number, "A106")
        self.assertEqual(vehicle.call_sign, "A106")
        self.assertEqual(vehicle.num_letter, "A")
        self.assertEqual(vehicle.num_value, 106)
        self.assertEqual(vehicle.status, VehicleStatus.ACTIF)
        self.assertIn("PIT ANDERLECHT 1 BRA", vehicle.utilisation)

    @patch("fireplan.sync.FireplanClient")
    def test_fleet_sync_preserves_vehicle_without_fireplan_id(self, client_cls):
        manual_vehicle = Vehicle.objects.create(number="LOCAL01")
        response = Mock()
        response.json.return_value = {
            "records": [
                {
                    "id": 123,
                    "alphacode": "F123",
                    "numLettre": "F",
                    "num": 123,
                    "plate": "",
                    "utilisation": "Fireplan",
                    "chassis": "",
                    "statut": VehicleStatus.ACTIF,
                }
            ]
        }
        response.raise_for_status.return_value = None
        client_cls.return_value.post.return_value = response

        count = sync_fireplan_fleet()

        manual_vehicle.refresh_from_db()
        self.assertEqual(count, 1)
        self.assertIsNone(manual_vehicle.fireplan_id)
        self.assertTrue(Vehicle.objects.filter(fireplan_id=123, number="F123").exists())

    def test_vehicle_cannot_have_radio_and_direct_issi(self):
        radio_model = RadioModel.objects.create(name="Mobile")
        TEIRange.objects.create(model=radio_model, min_tei=75000000000, max_tei=75999999999)
        radio = Radio.objects.create(TEI=75000000001)
        issi = ISSI.objects.create(number=2345678, alias="A106")
        vehicle = Vehicle(number="A106", radio=radio, issi=issi)

        with self.assertRaises(ValidationError):
            vehicle.full_clean()


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

    def test_vector_inventory_history_uses_one_table_row_per_inventory(self):
        FireplanInventoryRadio.objects.create(
            inventory=self.inventory,
            container_uuid=uuid4(),
            item_uuid=uuid4(),
            tei="000075060235950",
        )
        FireplanInventoryRadio.objects.create(
            inventory=self.inventory,
            container_uuid=uuid4(),
            item_uuid=uuid4(),
            tei="000075190060667",
        )

        with override("nl"):
            response = self.client.get(
                reverse("fireplan:vector_inventory_history", args=[self.vector.pk])
            )

        self.assertEqual(response.content.decode().count("Scanner Test"), 1)
        self.assertContains(response, "000075060235950")
        self.assertContains(response, "000075190060667")
