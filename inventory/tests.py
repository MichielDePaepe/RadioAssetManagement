import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override

from fireplan.models import FireplanInventory, FireplanInventoryRadio, Vector, Vehicle
from radio.models import Radio, RadioModel, TEIRange


class FireplanInventoryFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="scanner",
            password="secret",
            first_name="Scan",
            last_name="Operator",
        )
        self.client.force_login(self.user)

        radio_model = RadioModel.objects.create(name="Portable")
        TEIRange.objects.create(
            model=radio_model,
            min_tei=750000000000000,
            max_tei=750000000000999,
        )
        self.radio = Radio.objects.create(TEI=750000000000001, fireplan_id=12345)
        self.vehicle = Vehicle.objects.create(number="A106 - Test", plate="TEST-1")
        self.vector = Vector.objects.create(
            resourceCode="A106",
            vehicle=self.vehicle,
            name="Ambulance 106",
        )

    def test_vehicle_search_returns_vector_context(self):
        with override("en"):
            response = self.client.get(reverse("inventory:vehicle_search"), {"q": "A106"})

        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["id"], self.vehicle.id)
        self.assertEqual(result["indicatif"], "A106")
        self.assertEqual(result["vector"], "Ambulance 106")

    def test_scan_page_shows_vehicle_status_without_alpha_code_block(self):
        self.vehicle.status = 1
        self.vehicle.save(update_fields=["status"])

        with override("nl"):
            response = self.client.get(
                reverse("inventory:fireplan_inventory_scan", args=[self.vehicle.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Voertuigstatus")
        self.assertContains(response, "Actif")
        self.assertNotContains(response, "Vehicle alpha code")

    def test_closing_inventory_writes_fireplan_inventory_and_radios(self):
        with override("en"):
            response = self.client.post(
                reverse("inventory:fireplan_inventory_scan", args=[self.vehicle.pk]),
                {
                    "radios": json.dumps([
                        {"tei": self.radio.tei_str, "alias": "ignored client value"},
                    ])
                },
            )

        self.assertEqual(response.status_code, 302)
        inventory = FireplanInventory.objects.get()
        self.assertEqual(inventory.vehicle, self.vehicle)
        self.assertEqual(inventory.vehicle_alpha_code, self.vehicle.number)
        self.assertEqual(inventory.vector, self.vector)
        self.assertEqual(inventory.done_by_full_name, "Scan Operator")
        self.assertIsNotNone(inventory.closed_at)
        self.assertIsNone(inventory.uuid)
        self.assertIsNone(inventory.root_inventoried_container_uuid)

        inventory_radio = FireplanInventoryRadio.objects.get(inventory=inventory)
        self.assertEqual(inventory_radio.radio, self.radio)
        self.assertEqual(inventory_radio.tracked_item_id, self.radio.fireplan_id)
        self.assertEqual(inventory_radio.tei, self.radio.tei_str)
        self.assertIsNone(inventory_radio.container_uuid)
        self.assertIsNone(inventory_radio.item_uuid)
