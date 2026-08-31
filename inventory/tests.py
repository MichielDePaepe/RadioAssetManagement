import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override

from fireplan.models import FireplanInventory, FireplanInventoryRadio, Vector, Vehicle
from radio.models import ISSI, Radio, RadioModel, Subscription, TEIRange
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

    def test_scanner_configuration_page_shows_switch_modes(self):
        with override("nl"):
            response = self.client.get(reverse("inventory:scanner_configuration"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A&K A2BDS-BL1")
        self.assertContains(response, "Scanner configureren")
        self.assertContains(response, "Draadloos via USB-stick")
        self.assertContains(response, "Bluetooth verbinden")
        self.assertContains(response, "Bluetooth ontkoppelen")

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


class UnassignedSubscriptionRadioListTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="inventory-control",
            password="secret",
        )
        self.client.force_login(self.user)
        self.radio_model = RadioModel.objects.create(name="Portable")
        TEIRange.objects.create(
            model=self.radio_model,
            min_tei=750000000001000,
            max_tei=750000000001999,
        )
        self.location = Location.objects.create(
            name="Post Centrum",
            location_type=Location.LocationType.POST,
        )
        self.position = RadioPosition.objects.create(
            location=self.location,
            name="Kast 01",
        )

    def create_subscribed_radio(self, tei, issi, alias="", active=True, dmo_only=False, decommissioned=False):
        radio = Radio.objects.create(TEI=tei, decommissioned=decommissioned)
        issi = ISSI.objects.create(number=issi, alias=alias)
        Subscription.objects.create(
            radio=radio,
            issi=issi,
            active=active,
            DMO_only=dmo_only,
        )
        return radio

    def test_lists_active_subscription_radios_without_position(self):
        unassigned = self.create_subscribed_radio(750000000001001, 123001, alias="A100")
        assigned = self.create_subscribed_radio(750000000001002, 123002, alias="A101")
        self.create_subscribed_radio(750000000001003, 123003, active=False)
        self.create_subscribed_radio(750000000001004, 123004, dmo_only=True)
        self.create_subscribed_radio(750000000001005, 123005, decommissioned=True)
        change_primary(self.position, assigned)

        with override("en"):
            response = self.client.get(reverse("inventory:unassigned_subscription_radios"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, unassigned.tei_str)
        self.assertNotContains(response, assigned.tei_str)
        self.assertNotContains(response, "750000000001003")
        self.assertNotContains(response, "750000000001004")
        self.assertNotContains(response, "750000000001005")
        self.assertContains(response, "1 of 2 active subscription radios have no active position.")

    def test_search_filters_unassigned_subscription_radios(self):
        matching = self.create_subscribed_radio(750000000001006, 123006, alias="ALPHA")
        other = self.create_subscribed_radio(750000000001007, 123007, alias="BRAVO")

        with override("en"):
            response = self.client.get(
                reverse("inventory:unassigned_subscription_radios"),
                {"q": "ALPHA"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, matching.tei_str)
        self.assertNotContains(response, other.tei_str)


class ParentPositionListTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="parent-position-admin",
            password="secret",
        )
        self.client.force_login(self.user)
        self.location = Location.objects.create(
            name="Post Centrum",
            location_type=Location.LocationType.POST,
        )
        self.vehicle = Vehicle.objects.create(number="AMB HELI 1")
        self.vector = Vector.objects.create(
            resourceCode="AMBHELI1",
            display_name="AMB HELI 1",
            vehicle=self.vehicle,
        )

    def test_location_parent_page_shows_positions_and_add_link(self):
        RadioPosition.objects.create(location=self.location, name="Kast 01", order=1)

        with override("en"):
            response = self.client.get(
                reverse("inventory:parent_positions", args=["location", self.location.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kast 01")
        self.assertContains(response, f"?location={self.location.pk}")
        self.assertNotContains(response, "Create positions from template")

    def test_vector_parent_page_offers_templates_when_empty(self):
        with override("en"):
            response = self.client.get(
                reverse("inventory:parent_positions", args=["vector", self.vector.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AMB HELI 1")
        self.assertContains(response, "Chauffeur en convoyeur")
        self.assertNotContains(response, "Chauffeur en chef")
        self.assertContains(response, "Genummerde ploeg en ATEX radio")
        self.assertContains(response, "Zelf 1 positie toevoegen")

    def test_template_creates_positions_for_vector(self):
        with override("en"):
            response = self.client.post(
                reverse("inventory:parent_positions", args=["vector", self.vector.pk]),
                {"template": "driver_convoyeur"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response["Location"].endswith(f"/inventory/parents/vector/{self.vector.pk}/positions/")
        )
        self.assertEqual(
            list(self.vector.radio_positions.order_by("order").values_list("name", flat=True)),
            ["Chauffeur", "Convoyeur"],
        )

    def test_template_is_not_applied_when_positions_already_exist(self):
        RadioPosition.objects.create(vector=self.vector, name="Existing", order=1)

        with override("en"):
            response = self.client.post(
                reverse("inventory:parent_positions", args=["vector", self.vector.pk]),
                {"template": "numbered_crew_atex"},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.vector.radio_positions.count(), 1)


class PublicLocationDashboardTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(
            name="Post Centrum",
            location_type=Location.LocationType.POST,
        )
        self.vehicle = Vehicle.objects.create(number="AMB HELI 1")
        self.vector = Vector.objects.create(
            resourceCode="AMBHELI1",
            display_name="AMB HELI 1",
            vehicle=self.vehicle,
        )
        self.location.dashboard_vectors.add(self.vector)
        self.position = RadioPosition.objects.create(
            vector=self.vector,
            name="Chauffeur",
            order=1,
        )

    def test_post_dashboard_is_public_but_not_clickable_or_editable(self):
        with override("en"):
            response = self.client.get(
                reverse("inventory:location_detail", args=[self.location.pk])
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Post Centrum")
        self.assertContains(response, "AMB HELI 1")
        self.assertContains(response, "Chauffeur")
        self.assertNotContains(response, reverse("inventory:location_edit", args=[self.location.pk]))
        self.assertNotContains(response, reverse("inventory:location_list"))
        self.assertNotContains(
            response,
            reverse("inventory:parent_positions", args=["vector", self.vector.pk]),
        )
        self.assertNotContains(response, reverse("inventory:position_detail", args=[self.position.pk]))

    def test_post_dashboard_menu_list_is_public_without_management_controls(self):
        Location.objects.create(
            name="Dispatch",
            location_type=Location.LocationType.DISPATCH,
        )

        with override("en"):
            response = self.client.get(reverse("inventory:location_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Post dashboards")
        self.assertContains(response, "Post Centrum")
        self.assertNotContains(response, "Dispatch")
        self.assertNotContains(response, reverse("inventory:location_create"))
        self.assertNotContains(response, "New location")
        self.assertNotContains(response, "All")
