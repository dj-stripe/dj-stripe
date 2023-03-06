from django.urls import path

from . import views

app_name = "djstripe_example"

urlpatterns = [
    path(
        "checkout/",
        views.CreateCheckoutSessionView.as_view(),
        name="checkout",
    ),
    path(
        "checkout/server/",
        views.CreateCheckoutSessionServerView.as_view(),
        name="checkout",
    ),
    path("success/", views.CheckoutSessionSuccessView.as_view(), name="success"),
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
    path("payment-intent", views.create_payment_intent, name="payment_intent"),
]
