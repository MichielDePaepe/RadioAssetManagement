from django.test import TestCase, override_settings
from django.urls import reverse

from fireplan.models import ResourceTypeCode, Service, StatusCode, Vector, Vehicle, VehicleStatus
from radio.models import ISSI, Radio, RadioModel, Subscription, TEIRange


@override_settings(ROIP_API_KEYS=["test-key"])
class IssiLookupApiTests(TestCase):
    def setUp(self):
        model = RadioModel.objects.create(name="MTP850", radio_type=RadioModel.RadioType.MOBILE)
        TEIRange.objects.create(model=model, min_tei=75000000000, max_tei=75999999999)

        self.issi = ISSI.objects.create(number=1234567, alias="P101")
        self.radio = Radio.objects.create(TEI=75000000001)
        Subscription.objects.create(
            issi=self.issi,
            radio=self.radio,
            active=True,
            DMO_only=False,
            astrid_alias="ASTRID P101",
        )

        vehicle = Vehicle.objects.create(
            id=42,
            number="P101 - Autopomp",
            num_letter="P",
            num_value=101,
            plate="1-ABC-123",
            utilisation="Intervention",
            chassis="CHASSIS",
            status=VehicleStatus.ACTIF,
            radio=self.radio,
        )
        service = Service.objects.create(code="H1", description="Hoofdkazerne")
        resource_type = ResourceTypeCode.objects.create(code="AP", description="Autopomp")
        status = StatusCode.objects.create(code="AVL", description="Available", color="#00AA00")
        Vector.objects.create(
            resourceCode="P101",
            vehicle=vehicle,
            name="Autopomp 101",
            abbreviation="AP101",
            service=service,
            resourceTypeCode=resource_type,
            statusCode=status,
        )

    def test_returns_issi_radio_vehicle_and_vector_details(self):
        response = self.client.get(
            reverse("roip_api:issi_lookup", kwargs={"issi": "1234567"}),
            HTTP_X_API_KEY="test-key",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["issi"]["alias"], "P101")
        self.assertEqual(data["radio"]["tei_15"], "000075000000001")
        self.assertEqual(data["vehicle"]["call_sign"], "P101")
        self.assertEqual(data["vector"]["resource_code"], "P101")
        self.assertEqual(data["vector"]["status"]["code"], "AVL")

    def test_accepts_bearer_token(self):
        response = self.client.get(
            reverse("roip_api:issi_lookup", kwargs={"issi": "1234567"}),
            HTTP_AUTHORIZATION="Bearer test-key",
        )

        self.assertEqual(response.status_code, 200)

    def test_rejects_missing_api_key(self):
        response = self.client.get(reverse("roip_api:issi_lookup", kwargs={"issi": "1234567"}))

        self.assertEqual(response.status_code, 401)

    def test_returns_404_for_unknown_issi(self):
        response = self.client.get(
            reverse("roip_api:issi_lookup", kwargs={"issi": "7654321"}),
            HTTP_X_API_KEY="test-key",
        )

        self.assertEqual(response.status_code, 404)
