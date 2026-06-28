# Create a Stripe Checkout Session

Stripe Checkout is a prebuilt, hosted payment page optimized for conversion. It creates a secure, Stripe-hosted payment page that lets you collect payments quickly.

## Basic Implementation

For your convenience, dj-stripe provides an example implementation,
[`CreateCheckoutSessionView`](https://github.com/dj-stripe/dj-stripe/blob/main/tests/apps/example/views.py).

## Key Points

### Customer-Subscriber Linking

Please note that in order for dj-stripe to create a link between your `customers` and your `subscribers`, you need to add the `DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY` key to the `metadata` parameter of `Checkout`. This is also demonstrated in the example view linked above.

### Example Code Structure

The example implementation shows:

-   How to create a checkout session
-   How to handle success and cancel URLs
-   How to properly set metadata for customer linking
-   How to handle the redirect flow

### Integration Steps

1. Create a view that initializes the Checkout Session
2. Set up success and cancel URLs
3. Add the required metadata for customer linking
4. Handle the webhook events for successful payments
5. Redirect users to the Stripe-hosted checkout page
