# dj-stripe

[![Documentation](https://readthedocs.org/projects/dj-stripe/badge/)](https://dj-stripe.readthedocs.io/)
[![Sponsor dj-stripe](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub)](https://github.com/sponsors/dj-stripe)

Stripe Models for Django.

## Introduction

dj-stripe implements all of the Stripe models, for Django. Set up your
webhook endpoint and start receiving model updates. You will then have
a copy of all the Stripe models available in Django models, as soon as
they are updated!

The full documentation is available [on Read the Docs](https://dj-stripe.readthedocs.io/).

## Features

-   Stripe Core
-   Stripe Billing
-   Stripe Cards (JS v2) and Sources (JS v3)
-   Payment Methods and Payment Intents (SCA support)
-   Support for multiple accounts and API keys
-   Stripe Connect (partial support)
-   Tested with Stripe API `2020-08-27` (see [API versions](https://dj-stripe.readthedocs.io/en/latest/api_versions.html))

## Requirements

-   Django 2.2+
-   Python 3.6+
-   PostgreSQL engine (recommended) 9.5+
-   MySQL engine: MariaDB 10.2+ or MySQL 5.7+
-   SQLite: Not recommended in production. Version 3.26+ required.

## Quickstart

Install dj-stripe with pip:

    pip install dj-stripe

Or with [Poetry](https://python-poetry.org/) (recommended):

    poetry add dj-stripe

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

Add your Stripe keys and other settings:

```py
STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "<live secret key>")
STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "<test secret key>")
STRIPE_LIVE_MODE = False  # Change to True in production
DJSTRIPE_WEBHOOK_SECRET = "whsec_xxx"  # Get it from the section in the Stripe dashboard where you added the webhook endpoint
DJSTRIPE_USE_NATIVE_JSONFIELD = True  # We recommend setting to True for new installations
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"  # Set to `"id"` for all new 2.4+ installations
```

Add some payment plans via the Stripe.com dashboard.

Run the commands:

    python manage.py migrate

    python manage.py djstripe_sync_models

See <https://dj-stripe.readthedocs.io/en/latest/stripe_elements_js.html>
for notes about usage of the Stripe Elements frontend JS library.

## Running the Tests

Assuming the tests are run against PostgreSQL:

    createdb djstripe
    pytest

# Changelog

[See release notes on Read the Docs](https://dj-stripe.readthedocs.io/en/latest/history/2_4_0/).

# Funding this project

[![Stripe Logo](./docs/logos/stripe_blurple.svg)](https://stripe.com)

You can now become a sponsor to dj-stripe with [GitHub Sponsors](https://github.com/sponsors/dj-stripe).

We've been bringing dj-stripe to the world for over 7 years and are excited to be able to start
dedicating some real resources to the project.

Your sponsorship helps us keep a team of maintainers actively working to improve dj-stripe and
ensure it stays up-to-date with the latest Stripe changes. If you're using dj-stripe in a commercial
capacity and have the ability to start a sponsorship, we'd greatly appreciate the contribution.

All contributions through GitHub sponsors flow into our [Open Collective](https://opencollective.com/dj-stripe),
which holds our funds and keeps an open ledger on how donations are spent.

## Similar libraries

-   [dj-paypal](https://github.com/HearthSim/dj-paypal)
    ([PayPal](https://www.paypal.com/))
-   [dj-paddle](https://github.com/paddle-python/dj-paddle)
    ([Paddle](https://paddle.com/))
