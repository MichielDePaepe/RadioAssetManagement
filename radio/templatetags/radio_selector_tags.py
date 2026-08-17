import re

from django import template
from django.urls import reverse
from django.utils.html import conditional_escape, escape, format_html
from django.utils.safestring import mark_safe

from radio.models import Radio

register = template.Library()

TEI_RE = re.compile(r"(?<!\d)\d{14,15}(?!\d)")


@register.filter(needs_autoescape=True)
def render_radio_links(value, autoescape=True):
    if not value:
        return ""

    text = str(value)
    matches = list(TEI_RE.finditer(text))
    if not matches:
        return mark_safe(escape(text))

    tei_values = {int(match.group(0)) for match in matches}
    radios_by_tei = {
        radio.TEI: radio
        for radio in Radio.objects.filter(TEI__in=tei_values).select_related("subscription__issi")
    }

    output = []
    last_end = 0
    escape_value = conditional_escape if autoescape else lambda x: x

    for match in matches:
        output.append(escape_value(text[last_end:match.start()]))
        tei_text = match.group(0)
        tei = int(tei_text)

        radio = radios_by_tei.get(tei)
        if radio:
            output.append(
                format_html(
                    '<a href="{}" class="font-monospace">{}</a>',
                    reverse("radio:detail", kwargs={"pk": tei}),
                    str(radio),
                )
            )
        else:
            output.append(escape_value(tei_text))

        last_end = match.end()

    output.append(escape_value(text[last_end:]))
    return mark_safe("".join(str(part) for part in output))


@register.inclusion_tag('radio/selector/modal.html')
def radio_selector_modal(
    title="Radio zoeken",
    static=False,
    auto_confirm=False,
    callback="radio_selector_callback",
):
    return {
        'title': title,
        'static': static,
        'auto_confirm': auto_confirm,
        'callback': callback,
    }


@register.inclusion_tag('radio/selector/button.html')
def radio_selector_button(
    callback=None, 
    btn_type="btn-primary", 
    extra_class='', 
    **extra_data
):
    return {
        'btn_type': btn_type,
        'callback': callback,
        'extra_class': extra_class,
        'extra_data': extra_data,
    }
