from django.urls import path, re_path

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
	re_path(r'payment-intent', views.create_payment_intent),
]
