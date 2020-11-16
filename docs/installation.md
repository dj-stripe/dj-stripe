# Installation

## Get the distribution

Install dj-stripe:

    pip install dj-stripe

## Configuration

Add `djstripe` to your `INSTALLED_APPS`:

    INSTALLED_APPS =(
        ...
        "djstripe",
        ...
    )

Add to urls.py:

    path("stripe/", include("djstripe.urls", namespace="djstripe")),

Tell Stripe about the webhook (Stripe webhook docs can be found
[here](https://stripe.com/docs/webhooks)) using the full URL of your
endpoint from the urls.py step above (e.g.
`https://example.com/stripe/webhook`).

Add your Stripe keys and set the operating mode:

    STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "<your secret key>")
    STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "<your secret key>")
    STRIPE_LIVE_MODE = False  # Change to True in production
    DJSTRIPE_WEBHOOK_SECRET = "whsec_xxx"  # Get it from the section in the Stripe dashboard where you added the webhook endpoint

Add some payment plans via the Stripe.com dashboard.

Run the commands:

    python manage.py migrate

    python manage.py djstripe_sync_models

See [here](stripe_elements_js.md) for notes about usage of the Stripe Elements
frontend JS library.

## Running Tests

Assuming the tests are run against PostgreSQL:

    createdb djstripe
    pip install tox
    tox
