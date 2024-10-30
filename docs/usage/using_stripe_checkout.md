# Create a Stripe Checkout Session


For your convenience, dj-stripe has provided an example implementation on how to use [`Checkouts`][tests.apps.example.views.CreateCheckoutSessionView]



Please note that in order for dj-stripe to create a link between your `customers` and your `subscribers`, you need to add the `DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY` key to the `metadata` parameter of `Checkout`. This has also been demonstrated in the aforementioned [example][tests.apps.example.views.CreateCheckoutSessionView]
