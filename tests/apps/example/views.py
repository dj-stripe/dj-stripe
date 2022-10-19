import json
import logging

import stripe
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic import DetailView, FormView
from django.views.generic.base import TemplateView

from djstripe import models
from djstripe import settings as djstripe_settings

from . import forms

logger = logging.getLogger(__name__)


User = get_user_model()
stripe.api_key = djstripe_settings.djstripe_settings.STRIPE_SECRET_KEY


class CreateCheckoutSessionView(LoginRequiredMixin, TemplateView):
    """
    Example View to demonstrate how to use dj-stripe to:

     * Create a Stripe Checkout Session (for a new and a returning customer)
     * Add SUBSCRIBER_CUSTOMER_KEY to metadata to populate customer.subscriber model field
     * Fill out Payment Form and Complete Payment

    Redirects the User to Stripe Checkout Session.
    This does a logged in purchase for a new and a returning customer using Stripe Checkout
    """

    template_name = "checkout.html"

    def get_context_data(self, **kwargs):
        """
        Creates and returns a Stripe Checkout Session
        """
        # Get Parent Context
        context = super().get_context_data(**kwargs)

        # to initialise Stripe.js on the front end
        context[
            "STRIPE_PUBLIC_KEY"
        ] = djstripe_settings.djstripe_settings.STRIPE_PUBLIC_KEY

        success_url = self.request.build_absolute_uri(
            reverse("djstripe_example:success")
        )
        cancel_url = self.request.build_absolute_uri(reverse("home"))

        # get the id of the Model instance of djstripe_settings.djstripe_settings.get_subscriber_model()
        # here we have assumed it is the Django User model. It could be a Team, Company model too.
        # note that it needs to have an email field.
        id = self.request.user.id

        # example of how to insert the SUBSCRIBER_CUSTOMER_KEY: id in the metadata
        # to add customer.subscriber to the newly created/updated customer.
        metadata = {
            f"{djstripe_settings.djstripe_settings.SUBSCRIBER_CUSTOMER_KEY}": id
        }

        try:
            # retrieve the Stripe Customer.
            customer = models.Customer.objects.get(subscriber=self.request.user)

            print("Customer Object in DB.")

            # ! Note that Stripe will always create a new Customer Object if customer id not provided
            # ! even if customer_email is provided!
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                customer=customer.id,
                # payment_method_types=["bacs_debit"],  # for bacs_debit
                payment_intent_data={
                    "setup_future_usage": "off_session",
                    # so that the metadata gets copied to the associated Payment Intent and Charge Objects
                    "metadata": metadata,
                },
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            # "currency": "gbp",  # for bacs_debit
                            "unit_amount": 2000,
                            "product_data": {
                                "name": "Sample Product Name",
                                "images": ["https://i.imgur.com/EHyR2nP.png"],
                                "description": "Sample Description",
                            },
                        },
                        "quantity": 1,
                    },
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
            )

        except models.Customer.DoesNotExist:
            print("Customer Object not in DB.")

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                # payment_method_types=["bacs_debit"],  # for bacs_debit
                payment_intent_data={
                    "setup_future_usage": "off_session",
                    # so that the metadata gets copied to the associated Payment Intent and Charge Objects
                    "metadata": metadata,
                },
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            # "currency": "gbp",  # for bacs_debit
                            "unit_amount": 2000,
                            "product_data": {
                                "name": "Sample Product Name",
                                "images": ["https://i.imgur.com/EHyR2nP.png"],
                                "description": "Sample Description",
                            },
                        },
                        "quantity": 1,
                    },
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata,
            )

        context["CHECKOUT_SESSION_ID"] = session.id

        return context


class CheckoutSessionSuccessView(TemplateView):
    """
    Template View for showing Checkout Payment Success
    """

    template_name = "checkout_success.html"


class PurchaseSubscriptionView(FormView):
    """
    Example view to demonstrate how to use dj-stripe to:

    * create a Customer
    * add a card to the Customer
    * create a Subscription using that card

    This does a non-logged in purchase for the user of the provided email
    """

    template_name = "purchase_subscription.html"

    form_class = forms.PurchaseSubscriptionForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if models.Plan.objects.count() == 0:
            raise Exception(
                "No Product Plans in the dj-stripe database - create some in your "
                "stripe account and then "
                "run `./manage.py djstripe_sync_models Plan` "
                "(or use the dj-stripe webhooks)"
            )

        context[
            "STRIPE_PUBLIC_KEY"
        ] = djstripe_settings.djstripe_settings.STRIPE_PUBLIC_KEY

        return context

    def form_valid(self, form):
        stripe_source = form.cleaned_data["stripe_source"]
        email = form.cleaned_data["email"]
        plan = form.cleaned_data["plan"]

        # Guest checkout with the provided email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create(username=email, email=email)

        # Create the stripe Customer, by default subscriber Model is User,
        # this can be overridden with djstripe_settings.djstripe_settings.DJSTRIPE_SUBSCRIBER_MODEL
        customer, created = models.Customer.get_or_create(subscriber=user)

        # Add the source as the customer's default card
        customer.add_card(stripe_source)

        # Using the Stripe API, create a subscription for this customer,
        # using the customer's default payment source
        stripe_subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"plan": plan.id}],
            collection_method="charge_automatically",
            # tax_percent=15,
            api_key=djstripe_settings.djstripe_settings.STRIPE_SECRET_KEY,
        )

        # Sync the Stripe API return data to the database,
        # this way we don't need to wait for a webhook-triggered sync
        subscription = models.Subscription.sync_from_stripe_data(stripe_subscription)

        self.request.subscription = subscription

        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "djstripe_example:purchase_subscription_success",
            kwargs={"id": self.request.subscription.id},
        )


class PurchaseSubscriptionSuccessView(DetailView):
    template_name = "purchase_subscription_success.html"

    queryset = models.Subscription.objects.all()
    slug_field = "id"
    slug_url_kwarg = "id"
    context_object_name = "subscription"


def create_payment_intent(request):
    if request.method == "POST":
        intent = None
        data = json.loads(request.body)
        try:
            if "payment_method_id" in data:
                # Create the PaymentIntent
                intent = stripe.PaymentIntent.create(
                    payment_method=data["payment_method_id"],
                    amount=1099,
                    currency="usd",
                    confirmation_method="manual",
                    confirm=True,
                    api_key=djstripe_settings.djstripe_settings.STRIPE_SECRET_KEY,
                )
            elif "payment_intent_id" in data:
                intent = stripe.PaymentIntent.confirm(
                    data["payment_intent_id"],
                    api_key=djstripe_settings.djstripe_settings.STRIPE_SECRET_KEY,
                )
        except stripe.error.CardError as e:
            # Display error on client
            return_data = json.dumps({"error": e.user_message}), 200
            return HttpResponse(
                return_data[0], content_type="application/json", status=return_data[1]
            )

        if (
            intent.status == "requires_action"
            and intent.next_action.type == "use_stripe_sdk"
        ):
            # Tell the client to handle the action
            return_data = (
                json.dumps(
                    {
                        "requires_action": True,
                        "payment_intent_client_secret": intent.client_secret,
                    }
                ),
                200,
            )
        elif intent.status == "succeeded":
            # The payment did not need any additional actions and completed!
            # Handle post-payment fulfillment
            return_data = json.dumps({"success": True}), 200
        else:
            # Invalid status
            return_data = json.dumps({"error": "Invalid PaymentIntent status"}), 500
        return HttpResponse(
            return_data[0], content_type="application/json", status=return_data[1]
        )

    else:
        context = {
            "STRIPE_PUBLIC_KEY": djstripe_settings.djstripe_settings.STRIPE_PUBLIC_KEY
        }
        return TemplateResponse(request, "payment_intent.html", context)
