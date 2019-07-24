from django.urls import path

from . import views

app_name = "djstripe_example"

urlpatterns = [
	path(
		"purchase-subscription",
		views.PurchaseSubscriptionView.as_view(),
		name="purchase_subscription",
	),
	path(
		"purchase-subscription-success/<id>",
		views.PurchaseSubscriptionSuccessView.as_view(),
		name="purchase_subscription_success",
	),
	path(
		"payment-intent",
		views.PaymentIntentView.as_view(),
		name="payment_intent",
	),
]
