# Integrating Stripe Elements (JS SDK)

!!! tip

    TLDR: If you haven't yet migrated to PaymentIntents, prefer
    `stripe.createSource()` over `stripe.createToken()` for better
    compatibility with PaymentMethods.


!!! attention
    A point that can cause confusion when integrating Stripe on the web is
    that there are multiple generations of frontend JS APIs that use Stripe
    Elements with stripe js v3.

## In descending order of preference these are:

### [Payment Intents](https://stripe.com/docs/payments/payment-intents) (SCA compliant)

The newest and preferred way of handling payments, which supports SCA
compliance (3D secure etc).


### [Charges using stripe.createSource()](https://stripe.com/docs/js/tokens_sources/create_source)

This creates Source objects within Stripe, and can be used for various different methods of payment (including, but not limited to cards), but isn't SCA compliant.

The [Card Elements Quickstart JS](https://stripe.com/docs/payments/accept-a-payment-charges?platform=web) example can be used, except use `stripe.createSource` instead of `stripe.createToken` and the `result.source` instead of `result.token`. [`Checkout a working example of this`][tests.apps.example.views.PurchaseSubscriptionView]



### Charges using stripe.createToken()

This predates `stripe.createSource`, and creates legacy Card objects within Stripe, which have some compatibility issues with Payment Methods.

If you're using `stripe.createToken`, see if you can upgrade to
`stripe.createSource` or ideally to Payment Intents .

!!! tip
    Checkout [Card Elements Quickstart JS](https://stripe.com/docs/payments/accept-a-payment-charges?platform=web)
