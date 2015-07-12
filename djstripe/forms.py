# -*- coding: utf-8 -*-
"""
.. module:: djstripe.forms
   :synopsis: dj-stripe Forms.

.. moduleauthor:: Daniel Greenfeld (@pydanny)

"""

from django import forms

from . import settings as djstripe_settings


class PlanForm(forms.Form):
    plan = forms.ChoiceField(choices=djstripe_settings.get_plan_choices())


class CancelSubscriptionForm(forms.Form):
    pass
