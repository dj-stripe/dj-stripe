import logging

import stripe
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.views.generic import DetailView, FormView

import djstripe.models
import djstripe.settings

from . import forms

logger = logging.getLogger(__name__)


User = get_user_model()


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
		ctx = super().get_context_data(**kwargs)

		if djstripe.models.Plan.objects.count() == 0:
			raise Exception(
				"No Product Plans in the dj-stripe database - create some in your stripe account and "
				"then run `./manage.py djstripe_sync_plans_from_stripe` (or use the dj-stripe webhooks)"
			)

		ctx["STRIPE_PUBLIC_KEY"] = djstripe.settings.STRIPE_PUBLIC_KEY

		return ctx

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
		# this can be overridden with settings.DJSTRIPE_SUBSCRIBER_MODEL
		customer, created = djstripe.models.Customer.get_or_create(subscriber=user)

		# Add the source as the customer's default card
		customer.add_card(stripe_source)

		# Using the Stripe API, create a subscription for this customer,
		# using the customer's default payment source
		stripe_subscription = stripe.Subscription.create(
			customer=customer.id,
			items=[{"plan": plan.id}],
			billing="charge_automatically",
			# tax_percent=15,
			api_key=djstripe.settings.STRIPE_SECRET_KEY,
		)

		# Sync the Stripe API return data to the database,
		# this way we don't need to wait for a webhook-triggered sync
		subscription = djstripe.models.Subscription.sync_from_stripe_data(stripe_subscription)

		self.request.subscription = subscription

		return super().form_valid(form)

	def get_success_url(self):
		return reverse(
			"djstripe_example:purchase_subscription_success",
			kwargs={"id": self.request.subscription.id},
		)


class PurchaseSubscriptionSuccessView(DetailView):
	template_name = "purchase_subscription_success.html"

	queryset = djstripe.models.Subscription.objects.all()
	slug_field = "id"
	slug_url_kwarg = "id"
	context_object_name = "subscription"


class PaymentIntentView(FormView):
	"""
	Example view to demonstrate how to use payment method

	* Create a customer
	"""

	template_name = "payment_intent.html"

	form_class = forms.PaymentIntentForm

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		ctx["STRIPE_PUBLIC_KEY"] = djstripe.settings.STRIPE_PUBLIC_KEY
		return ctx
