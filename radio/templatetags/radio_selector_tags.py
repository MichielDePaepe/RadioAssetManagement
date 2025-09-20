from django import template

register = template.Library()


@register.inclusion_tag('radio/selector/modal.html')
def radio_selector_modal(title="Radio zoeken"):
    return {
        'title': title,
    }


@register.inclusion_tag('radio/selector/button.html')
def radio_selector_button(callback=None, btn_type="btn-primary", extra_class='', **extra_data):

    return {
        'btn_type': btn_type,
        'callback': callback,
        'extra_class': extra_class,
        'extra_data': extra_data,
    }

