"""
Module for all dj-stripe app forms
"""
from django import forms
from django.contrib.admin import helpers
from stripe.error import AuthenticationError

from djstripe import utils

from . import enums, models


class CustomActionForm(forms.Form):
    """Form for Custom Django Admin Actions"""

    def __init__(self, *args, **kwargs):

        # remove model_name kwarg
        model_name = kwargs.pop("model_name")

        # remove action_name kwarg
        action_name = kwargs.pop("action_name")

        super().__init__(*args, **kwargs)

        model = utils.get_model(model_name)
        # set choices attribute
        # form field to keep track of all selected instances
        # for the Custom Django Admin Action

        if action_name == "_sync_all_instances":
            self.fields[helpers.ACTION_CHECKBOX_NAME] = forms.MultipleChoiceField(
                widget=forms.MultipleHiddenInput,
                choices=[(action_name, action_name)],
            )
        else:
            self.fields[helpers.ACTION_CHECKBOX_NAME] = forms.MultipleChoiceField(
                widget=forms.MultipleHiddenInput,
                choices=zip(
                    model.objects.values_list("pk", flat=True),
                    model.objects.values_list("pk", flat=True),
                ),
            )


class APIKeyAdminCreateForm(forms.ModelForm):
    class Meta:
        model = models.APIKey
        fields = ["name", "secret"]

    def _post_clean(self):
        super()._post_clean()

        if not self.errors:
            if (
                self.instance.type == enums.APIKeyType.secret
                and self.instance.djstripe_owner_account is None
            ):
                try:
                    self.instance.refresh_account()
                except AuthenticationError as e:
                    self.add_error("secret", str(e))
