from django.conf import settings
from django import forms
from django.utils.translation import ugettext as _

import stripe

from .models import Customer
from .settings import PLAN_CHOICES, PASSWORD_INPUT_RENDER_VALUE, \
    PASSWORD_MIN_LENGTH

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = getattr(settings, "STRIPE_API_VERSION", "2012-11-07")


class PlanForm(forms.Form):

    plan = forms.ChoiceField(choices=PLAN_CHOICES)


class CancelSubscriptionForm(forms.Form):
    pass


########### Begin SignupForm code

class PasswordField(forms.CharField):
    def __init__(self, *args, **kwargs):
        render_value = kwargs.pop('render_value', PASSWORD_INPUT_RENDER_VALUE)
        kwargs['widget'] = forms.PasswordInput(
            render_value=render_value,
            attrs={'placeholder': _('Password')})
        super(PasswordField, self).__init__(*args, **kwargs)


class SetPasswordField(PasswordField):
    def clean(self, value):
        value = super(SetPasswordField, self).clean(value)
        min_length = PASSWORD_MIN_LENGTH
        if len(value) < min_length:
            raise forms.ValidationError(
                _("Password must be a minimum of {0} "
                  "characters.").format(min_length))
        return value


try:
    from .widgets import StripeWidget
except ImportError:
    StripeWidget = None

try:
    from allauth.account.utils import setup_user_email
except ImportError:
    setup_user_email = None


if StripeWidget and setup_user_email:

    class StripeSubscriptionSignupForm(forms.Form):
        """
            Requires the following packages:

                * django-crispy-forms
                * django-floppyforms
                * django-allauth

            Necessary settings::

                INSTALLED_APPS += (
                    "floppyforms",
                    "allauth",  # registration
                    "allauth.account",  # registration
                )
                ACCOUNT_SIGNUP_FORM_CLASS = "djstripe.StripeSubscriptionSignupForm"

            Necessary URLS::

                (r'^accounts/', include('allauth.urls')),

        """
        username = forms.CharField(max_length=30)
        email = forms.EmailField(max_length=30)
        password1 = SetPasswordField(label=_("Password"))
        password2 = PasswordField(label=_("Password (again)"))
        confirmation_key = forms.CharField(
            max_length=40,
            required=False,
            widget=forms.HiddenInput())
        stripe_token = forms.CharField(widget=forms.HiddenInput())
        plan = forms.ChoiceField(choices=PLAN_CHOICES)

        # Stripe nameless fields
        number = forms.CharField(max_length=20,
            required=False,
            widget=StripeWidget(attrs={"data-stripe": "number"})
        )
        cvc = forms.CharField(max_length=4, label=_("CVC"),
            required=False,
            widget=StripeWidget(attrs={"data-stripe": "cvc"}))
        exp_month = forms.CharField(max_length=2,
                required=False,
                widget=StripeWidget(attrs={"data-stripe": "exp-month"})
        )
        exp_year = forms.CharField(max_length=4,
                required=False,
                widget=StripeWidget(attrs={"data-stripe": "exp-year"})
        )

        def save(self, user):
            try:
                customer, created = Customer.get_or_create(user)
                customer.update_card(self.cleaned_data["stripe_token"])
                customer.subscribe(self.cleaned_data["plan"])
            except stripe.StripeError as e:
                # handle error here
                raise e

