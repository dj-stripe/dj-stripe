from django import forms

from .settings import PLAN_CHOICES


class PlanForm(forms.Form):

    plan = forms.ChoiceField(choices=PLAN_CHOICES)
