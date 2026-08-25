import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override

from fireplan.models import FireplanInventory, FireplanInventoryRadio, Vector, Vehicle
from radio.models import Radio, RadioModel, TEIRange
from .models import Location, RadioPosition, RadioPositionAssignment
from .services import assign_substitute, change_primary, release_primary, release_substitute


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


class RadioPositionAssignmentTests(TestCase):
    def setUp(self):
        radio_model = RadioModel.objects.create(name="Portable")
        TEIRange.objects.create(
            model=radio_model,
            min_tei=750000000000000,
            max_tei=750000000000999,
        )
        self.primary_radio = Radio.objects.create(TEI=750000000000101)
        self.substitute_radio = Radio.objects.create(TEI=750000000000102)
        self.other_radio = Radio.objects.create(TEI=750000000000103)
        self.location = Location.objects.create(
            name="Intelligente kast",
            location_type=Location.LocationType.SMART_CABINET,
        )
        self.position = RadioPosition.objects.create(
            location=self.location,
            name="Slot 01",
        )

    def test_position_requires_exactly_one_parent(self):
        vehicle = Vehicle.objects.create(number="A106")
        invalid_position = RadioPosition(
            location=self.location,
            vehicle=vehicle,
            name="Chauffeur",
        )

        with self.assertRaises(ValidationError):
            invalid_position.full_clean()

    def test_primary_and_substitute_can_be_active_together(self):
        primary = change_primary(self.position, self.primary_radio)
        substitute = assign_substitute(self.position, self.substitute_radio)

        self.assertIsNone(primary.ended_at)
        self.assertIsNone(substitute.ended_at)
        self.assertEqual(substitute.replaces, primary)
        self.assertEqual(self.position.operational_radio, self.substitute_radio)

    def test_radio_cannot_have_two_active_assignments(self):
        change_primary(self.position, self.primary_radio)
        other_position = RadioPosition.objects.create(
            location=self.location,
            name="Slot 02",
        )

        with self.assertRaises(ValidationError):
            change_primary(other_position, self.primary_radio)

    def test_only_one_active_primary_per_position(self):
        change_primary(self.position, self.primary_radio)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RadioPositionAssignment.objects.create(
                    position=self.position,
                    radio=self.other_radio,
                    role=RadioPositionAssignment.Role.PRIMARY,
                )

    def test_release_substitute_keeps_primary_active(self):
        primary = change_primary(self.position, self.primary_radio)
        substitute = assign_substitute(self.position, self.substitute_radio)

        release_substitute(self.position)
        primary.refresh_from_db()
        substitute.refresh_from_db()

        self.assertIsNone(primary.ended_at)
        self.assertIsNotNone(substitute.ended_at)
        self.assertEqual(self.position.operational_radio, self.primary_radio)

    def test_release_primary_closes_primary_assignment(self):
        primary = change_primary(self.position, self.primary_radio)

        release_primary(self.position)
        primary.refresh_from_db()

        self.assertIsNotNone(primary.ended_at)
        self.assertIsNone(self.position.operational_radio)

    def test_release_primary_keeps_substitute_active(self):
        primary = change_primary(self.position, self.primary_radio)
        substitute = assign_substitute(self.position, self.substitute_radio)

        release_primary(self.position)
        primary.refresh_from_db()
        substitute.refresh_from_db()

        self.assertIsNotNone(primary.ended_at)
        self.assertIsNone(substitute.ended_at)
        self.assertEqual(self.position.operational_radio, self.substitute_radio)


class RadioPositionViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="position-admin",
            password="secret",
        )
        self.client.force_login(self.user)
        self.location = Location.objects.create(
            name="Post Centrum",
            location_type=Location.LocationType.POST,
        )
        self.position = RadioPosition.objects.create(
            location=self.location,
            name="Kast 01",
        )

    def test_position_can_be_deleted_from_confirm_view(self):
        with override("en"):
            response = self.client.post(
                reverse("inventory:position_delete", args=[self.position.pk])
            )

        with override("en"):
            self.assertRedirects(response, reverse("inventory:location_detail", args=[self.location.pk]))
        self.assertFalse(RadioPosition.objects.filter(pk=self.position.pk).exists())
