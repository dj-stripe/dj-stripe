"""
Module for all dj-stripe Admin app forms
"""

from typing import Optional
from urllib.parse import urljoin

from django import forms
from django.contrib.admin import helpers
from django.urls import reverse
from stripe import AuthenticationError, InvalidRequestError, PermissionError

from djstripe import enums, models, utils
from djstripe.settings import djstripe_settings
from djstripe.signals import ENABLED_EVENTS


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
                self.instance.type
                in (
                    enums.APIKeyType.secret,
                    enums.APIKeyType.restricted,
                )
                and self.instance.djstripe_owner_account is None
            ):
                try:
                    self.instance.refresh_account()
                except AuthenticationError as e:
                    self.add_error("secret", str(e))
                # Abandon Key Creation if the given key doesn't allow Accounts to be retrieved from Stripe
                except PermissionError as e:
                    self.add_error("secret", str(e))


class WebhookEndpointAdminBaseForm(forms.ModelForm):
    def add_endpoint_tolerance(self):
        """Add djstripe_tolerance from submitted form"""
        self._stripe_data["djstripe_tolerance"] = self.cleaned_data.get(
            "djstripe_tolerance"
        )

    def add_endpoint_validation_method(self):
        """Add djstripe_validation_method from submitted form"""
        self._stripe_data["djstripe_validation_method"] = self.cleaned_data.get(
            "djstripe_validation_method"
        )

    def _get_field_name(self, stripe_field: Optional[str]) -> Optional[str]:
        if stripe_field is None:
            return None
        if stripe_field == "url":
            return "base_url"
        return stripe_field.partition("[")[0]

    def save(self, commit: bool = False):
        # If we do the following in _post_clean(), the data doesn't save properly.
        if not self._stripe_data:
            raise ValueError("_stripe_data is not present. ")

        # Update scenario
        # Add back secret if endpoint already exists
        if self.instance.pk and not self._stripe_data.get("secret"):
            self._stripe_data["secret"] = self.instance.secret

        # Add webhook tolerance and validation method from submitted form
        self.add_endpoint_tolerance()
        self.add_endpoint_validation_method()

        # Retrieve the api key that was used to create the endpoint
        api_key = getattr(self, "_stripe_api_key", None)
        if api_key:
            self.instance = models.WebhookEndpoint.sync_from_stripe_data(
                self._stripe_data, api_key=api_key
            )
        else:
            self.instance = models.WebhookEndpoint.sync_from_stripe_data(
                self._stripe_data
            )
        return super().save(commit=commit)


class WebhookEndpointAdminCreateForm(WebhookEndpointAdminBaseForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["djstripe_owner_account"].label = "Stripe account"
        self.fields["djstripe_owner_account"].help_text = ""

    enabled_events = forms.MultipleChoiceField(
        label="Enabled Events",
        required=True,
        help_text=(
            "The list of events to enable for this endpoint. ['*'] indicates that all"
            " events are enabled, except those that require explicit selection."
        ),
        choices=zip(ENABLED_EVENTS, ENABLED_EVENTS),
        initial=["*"],
    )
    livemode = forms.BooleanField(
        label="Live mode",
        required=False,
        help_text="Whether to create this endpoint in live mode or test mode",
    )
    base_url = forms.URLField(
        required=True,
        help_text=(
            "Sets the base URL (scheme and host) for the endpoint. "
            "The final full URL will be auto-generated by dj-stripe."
        ),
    )
    connect = forms.BooleanField(
        label="Listen to events on Connected accounts",
        initial=False,
        required=False,
        help_text=(
            "Clients can make requests as connected accounts using the special "
            "header `Stripe-Account` which should contain a Stripe account ID "
            "(usually starting with the prefix `acct_`)."
        ),
    )

    class Meta:
        model = models.WebhookEndpoint
        fields = (
            "enabled_events",
            "livemode",
            "djstripe_owner_account",
            "base_url",
            "connect",
            "api_version",
            "metadata",
            "djstripe_tolerance",
            "djstripe_validation_method",
        )

    # Hook into _post_clean() instead of save().
    # This is used by Django for ModelForm logic. It's internal, but exactly
    # what we need to add errors after the data has been validated locally.
    def _post_clean(self):
        base_url = self.cleaned_data.get("base_url")
        url_path = reverse(
            "djstripe:djstripe_webhook_by_uuid",
            kwargs={"uuid": self.instance.djstripe_uuid},
        )
        url = urljoin(base_url, url_path, allow_fragments=False)

        metadata = self.instance.metadata or {}
        metadata["djstripe_uuid"] = str(self.instance.djstripe_uuid)

        _api_key = {}
        account = self.cleaned_data.get("djstripe_owner_account")
        livemode = self.cleaned_data.get("livemode", None)
        if account:
            self._stripe_api_key = _api_key["api_key"] = account.get_default_api_key(
                livemode=livemode
            )

        try:
            self._stripe_data = models.WebhookEndpoint._api_create(
                url=url,
                api_version=self.cleaned_data.get("api_version", ""),
                enabled_events=self.cleaned_data.get("enabled_events"),
                metadata=metadata,
                connect=self.cleaned_data.get("connect", False),
                **_api_key,
            )
        except InvalidRequestError as e:
            field_name = self._get_field_name(e.param)
            self.add_error(field_name, e.user_message)

        except AuthenticationError as e:
            self.add_error("__all__", e.user_message)

        return super()._post_clean()

    def get_initial_for_field(self, field, field_name):
        if field_name == "api_version":
            return djstripe_settings.STRIPE_API_VERSION
        return super().get_initial_for_field(field, field_name)


class WebhookEndpointAdminEditForm(WebhookEndpointAdminBaseForm):
    enabled_events = forms.MultipleChoiceField(
        label="Enabled Events",
        required=True,
        help_text=(
            "The list of events to enable for this endpoint. ['*'] indicates that all"
            " events are enabled, except those that require explicit selection."
        ),
        choices=zip(ENABLED_EVENTS, ENABLED_EVENTS),
    )
    base_url = forms.URLField(
        required=False,
        help_text=(
            "Updating this changes the base URL of the endpoint. "
            "MUST be publicly-accessible."
        ),
    )
    enabled = forms.BooleanField(
        initial=True,
        required=False,
        help_text="When disabled, the endpoint will not receive events.",
    )

    class Meta:
        model = models.WebhookEndpoint
        fields = (
            "base_url",
            "enabled_events",
            "metadata",
            "djstripe_tolerance",
            "djstripe_validation_method",
        )

    def get_initial_for_field(self, field, field_name):
        if field_name == "base_url":
            metadata = self.instance.metadata or {}
            djstripe_uuid = metadata.get("djstripe_uuid")
            if djstripe_uuid:
                # if a djstripe_uuid is set (for dj-stripe endpoints), set the base_url
                endpoint_path = reverse(
                    "djstripe:djstripe_webhook_by_uuid", kwargs={"uuid": djstripe_uuid}
                )
                return self.instance.url.replace(endpoint_path, "")
        return super().get_initial_for_field(field, field_name)

    def _post_clean(self):
        base_url = self.cleaned_data.get("base_url", "")
        if base_url and self.instance.djstripe_uuid:
            url_path = reverse(
                "djstripe:djstripe_webhook_by_uuid",
                kwargs={"uuid": self.instance.djstripe_uuid},
            )
            url = urljoin(base_url, url_path, allow_fragments=False)
        else:
            url = self.instance.url

        try:
            self._stripe_data = self.instance._api_update(
                url=url,
                enabled_events=self.cleaned_data.get("enabled_events"),
                metadata=self.cleaned_data.get("metadata"),
                disabled=(not self.cleaned_data.get("enabled")),
            )
        except InvalidRequestError as e:
            field_name = self._get_field_name(e.param)
            self.add_error(field_name, e.user_message)

        except AuthenticationError as e:
            self.add_error("__all__", e.user_message)

        return super()._post_clean()
