from django.test import TestCase
from django.urls import reverse
from django.utils.html import escape

from radio.templatetags.radio_selector_tags import render_radio_links
from radio.models import ISSI, Radio, RadioModel, Subscription, TEIRange


class RenderRadioLinksTests(TestCase):
    def setUp(self):
        model = RadioModel.objects.create(name="Test radio")
        TEIRange.objects.create(
            model=model,
            min_tei=750000000000000,
            max_tei=750000000000999,
        )
        self.radio = Radio.objects.create(TEI=750000000000001)
        issi = ISSI.objects.create(number=1234567, alias="TEST")
        Subscription.objects.create(radio=self.radio, issi=issi)

    def test_links_existing_tei_to_radio_detail_with_radio_label(self):
        rendered = render_radio_links("Controleer 750000000000001 aub")

        self.assertIn(reverse("radio:detail", kwargs={"pk": self.radio.pk}), rendered)
        self.assertIn(str(self.radio), rendered)

    def test_can_render_title_text_with_known_tei(self):
        rendered = render_radio_links("Probleem met 750000000000001")

        self.assertIn("<a ", rendered)
        self.assertIn(str(self.radio), rendered)

    def test_leaves_unknown_tei_as_plain_text(self):
        rendered = render_radio_links("Controleer 750000000000999 aub")

        self.assertNotIn("<a ", rendered)
        self.assertIn("750000000000999", rendered)

    def test_leaves_unknown_tei_with_leading_zeroes_as_plain_text(self):
        rendered = render_radio_links("Controleer 000098061050370 aub")

        self.assertNotIn("<a ", rendered)
        self.assertIn("000098061050370", rendered)

    def test_escapes_note_html(self):
        rendered = render_radio_links("<script>alert(1)</script> 750000000000001")

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", rendered)
        self.assertNotIn("<script>", rendered)

    def test_escapes_text_without_tei(self):
        rendered = render_radio_links("<strong>geen radio</strong>")

        self.assertEqual(rendered, escape("<strong>geen radio</strong>"))
