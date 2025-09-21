from django import forms
from django.utils.translation import gettext as _

from .models import Radio, TEIRange


class RadioForm(forms.ModelForm):
    class Meta:
        model = Radio
        fields = ['TEI', 'fireplan_id']

    def clean_TEI(self):
	    raw_input = self.data.get('TEI')  # get raw string input from the form

	    if not raw_input.isdigit():
	        raise forms.ValidationError(_("TEI must contain only digits."))

	    if len(raw_input) not in (14, 15):
	        raise forms.ValidationError(_("TEI must be 14 or 15 digits long."))

	    if len(raw_input) == 15:
	        # if length is 15, last digit must be zero and removed
	        if not raw_input.endswith('0'):
	            raise forms.ValidationError(_("If 15 digits, last digit must be zero."))
	        raw_input = raw_input[:-1]

	    tei_int = int(raw_input)

	    # check if TEI integer falls in any known range
	    if not TEIRange.objects.filter(min_tei__lte=tei_int, max_tei__gte=tei_int).exists():
	        raise forms.ValidationError(_("TEI is not within known TEI ranges."))

	    # keep original raw TEI value for further use if needed
	    self.cleaned_data['TEI_raw'] = self.data.get('TEI')

	    return tei_int

