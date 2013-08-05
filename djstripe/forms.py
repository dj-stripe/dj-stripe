from django import forms

from .settings import PLAN_CHOICES


class PlanForm(forms.Form):

    if len(PLAN_CHOICES) == 1:
        plan = forms.CharField(initial=PLAN_CHOICES[0][0])
    else:
        plan = forms.ChoiceField(choices=PLAN_CHOICES + [("", "-------")])

    def __init__(self, *args, **kwargs):
        super(PlanForm, self).__init__(*args, **kwargs)
        self.fields['plan'].widget.attrs['readonly'] = True

