# Using Stripe Webhooks

## Setting up a new webhook endpoint in dj-stripe

As of dj-stripe 2.7.0, dj-stripe can create its own webhook endpoints on Stripe from the
Django administration.

Create a new webhook endpoint from the Django administration by going to dj-stripe
-> Webhook endpoints -> Add webhook endpoint (or `/admin/djstripe/webhookendpoint/add/`).

From there, you can choose an account to create the endpoint for.
If no account is chosen, the default Stripe API key will be used to create the endpoint.
You can also choose to create the endpoint in test mode or live mode.

You may want to change the base URL of the endpoint. This field will be prefilled with
the current site. If you're running on the local development server, you may see
`http://localhost:8000` or similar in there. Stripe won't let you save webhook endpoints
with such a value, so you will want to change it to a real website URL.

When saved from the admin, the endpoint will be created in Stripe with a dj-stripe
specific UUID which will be part of the URL, making it impossible to guess externally
by brute-force.


## Extra configuration

dj-stripe provides the following settings to tune how your webhooks work:

-   [`DJSTRIPE_WEBHOOK_VALIDATION`][djstripe.settings.DjstripeSettings.WEBHOOK_VALIDATION]
-   [`DJSTRIPE_WEBHOOK_EVENT_CALLBACK`][djstripe.settings.DjstripeSettings.WEBHOOK_EVENT_CALLBACK]


## Official documentation

Stripe docs for types of Events:
<https://stripe.com/docs/api/events/types>

Stripe docs for Webhooks: <https://stripe.com/docs/webhooks>

Django docs for transactions:
<https://docs.djangoproject.com/en/dev/topics/db/transactions/#performing-actions-after-commit>
