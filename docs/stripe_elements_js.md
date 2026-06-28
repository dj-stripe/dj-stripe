# Integrating Stripe Elements (JS SDK)

To collect card and other payment details in the browser without sensitive data
touching your server, Stripe provides [Stripe.js](https://stripe.com/docs/js) and
[Stripe Elements](https://stripe.com/docs/payments/elements). Your frontend
tokenises the payment details with Stripe and sends only the resulting identifier
to your backend, where dj-stripe takes over.

There are several generations of Stripe's frontend APIs. dj-stripe works with all
of them, but new integrations should use **Payment Intents** with the **Payment
Element**.

## Recommended: Payment Intents + Payment Element

The [Payment Intents API](https://stripe.com/docs/payments/payment-intents) is the
current, recommended way to accept payments. It supports
[Strong Customer Authentication](https://stripe.com/docs/strong-customer-authentication)
(3D Secure) and a wide range of payment methods through a single integration.

Follow Stripe's [Accept a payment](https://stripe.com/docs/payments/accept-a-payment)
guide for the frontend. On the backend, your code creates a `PaymentIntent` (or a
`SetupIntent` / `Subscription`) via the Stripe API and syncs the result with
dj-stripe — see [Manually syncing data with Stripe](usage/manually_syncing_with_stripe.md)
and the [`PaymentIntent`][djstripe.models.core.PaymentIntent] and
[`PaymentMethod`][djstripe.models.payment_methods.PaymentMethod] models.

dj-stripe ships a runnable example of this flow: see
[`PurchaseSubscriptionView`](https://github.com/dj-stripe/dj-stripe/blob/main/tests/apps/example/views.py)
in the test app, which creates a `Customer`, attaches a payment method, and creates
a `Subscription`.

## Legacy token-based flows

Older integrations collect payment details with `stripe.createToken()`, producing a
single-use token (`tok_...`) that you pass to
[`Customer.add_payment_method`][djstripe.models.core.Customer.add_payment_method].
This still works, but it predates SCA and only supports cards.

_WARNING_: The Stripe **Sources** API (`stripe.createSource()`) is deprecated by
Stripe, and the corresponding `Source` model was **removed in dj-stripe 3.0**. If
your integration still relies on Sources, migrate to Payment Intents and
`PaymentMethod` objects. See the [3.0 release notes](changes/3_0_0.md).

If you are maintaining a legacy integration, prefer migrating to Payment Intents
over investing further in token- or source-based flows.
