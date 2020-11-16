# Integrating Stripe Elements (JS SDK)

!!! note

    TLDR: If you haven't yet migrated to PaymentIntents, prefer
    `stripe.createSource()` over `stripe.createToken()` for better
    compatibility with PaymentMethods.

A point that can cause confusion when integrating Stripe on the web is
that there are multiple generations of frontend JS APIs that use Stripe
Elements with stripe js v3.

In descending order of preference these are:

## Payment Intents (SCA compliant)

The newest and preferred way of handling payments, which supports SCA
compliance (3D secure etc).

See <https://stripe.com/docs/payments/payment-intents/web>

## Charges using stripe.createSource()

This creates Source objects within Stripe, and can be used for various
different methods of payment (including, but not limited to cards), but
isn't SCA compliant.

See <https://stripe.com/docs/stripe-js/reference#stripe-create-source>

The [Card Elements Quickstart
JS](https://stripe.com/docs/payments/cards/collecting/web) example can
be used, except use `stripe.createSource` instead of
`stripe.createToken` and the `result.source` instead of `result.token`.

See
<https://github.com/dj-stripe/dj-stripe/blob/master/tests/apps/example/templates/purchase_subscription.html>
in for a working example of this.

## Charges using stripe.createToken()

This predates `stripe.createSource`, and creates legacy Card objects
within Stripe, which have some compatibility issues with Payment
Methods.

If you're using `stripe.createToken`, see if you can upgrade to
`stripe.createSource` or ideally to Payment Intents .

See [Card Elements Quickstart
JS](https://stripe.com/docs/payments/cards/collecting/web)
