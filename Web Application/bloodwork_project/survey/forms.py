"""
Dynamic form construction.

Rather than a fixed ModelForm, the survey form is built at request time
based on which features the selected tests require. This keeps the form
lean and avoids asking questions that are not needed.
"""

from django import forms
from .tests_config import QUESTIONS, TESTS


TEST_CHOICES = [(t['key'], t['label']) for t in TESTS]


class TestSelectionForm(forms.Form):
    selected_tests = forms.MultipleChoiceField(
        choices=TEST_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        error_messages={'required': 'Please select at least one test.'},
    )


def build_survey_form(feature_keys, data=None):
    """
    Dynamically constructs a Django Form class containing only the fields
    needed for the given list of feature keys.

    Special handling:
      - 'bmi' generates height_ft, height_in, weight_lb fields
      - 'map' generates bp_systolic, bp_diastolic fields
      - All other features generate a single field matching their type
    """
    fields = {}

    for key in feature_keys:
        q = QUESTIONS[key]
        qtype = q['type']

        if qtype == 'bmi_inputs':
            fields['height_ft'] = forms.IntegerField(
                label='Height (feet)',
                min_value=3, max_value=8,
                widget=forms.NumberInput(attrs={
                    'class': 'number-input', 'placeholder': 'ft',
                    'min': 3, 'max': 8,
                }),
            )
            fields['height_in'] = forms.IntegerField(
                label='Height (inches)',
                min_value=0, max_value=11,
                widget=forms.NumberInput(attrs={
                    'class': 'number-input', 'placeholder': 'in',
                    'min': 0, 'max': 11,
                }),
            )
            fields['weight_lb'] = forms.FloatField(
                label='Weight (pounds)',
                min_value=50, max_value=600,
                widget=forms.NumberInput(attrs={
                    'class': 'number-input', 'placeholder': 'lbs',
                    'min': 50, 'max': 600,
                }),
            )

        elif qtype in ('radio', 'binary_radio', 'season'):
            choices = [(str(v), label) for v, label in q['choices']]
            fields[key] = forms.ChoiceField(
                label=q['question'],
                choices=choices,
                widget=forms.RadioSelect(attrs={'class': 'radio-input'}),
            )

        elif qtype == 'number':
            attrs = {'class': 'number-input'}
            attrs.update({k: str(v) for k, v in q.get('attrs', {}).items()})
            fields[key] = forms.FloatField(
                label=q['question'],
                widget=forms.NumberInput(attrs=attrs),
                min_value=q.get('attrs', {}).get('min', None),
                max_value=q.get('attrs', {}).get('max', None),
            )

    # Dynamically create the form class
    SurveyForm = type('SurveyForm', (forms.BaseForm,), {'base_fields': fields})
    return SurveyForm(data=data) if data is not None else SurveyForm()
