# dj-stripe

[![Build Status](https://travis-ci.org/dj-stripe/dj-stripe.svg?branch=master)](https://travis-ci.org/dj-stripe/dj-stripe)
[![Documentation Status](https://readthedocs.org/projects/dj-stripe/badge/)](https://dj-stripe.readthedocs.io/)
[![Sponsor dj-stripe](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub)](https://github.com/sponsors/dj-stripe)

Stripe Models for Django.

## Introduction

dj-stripe implements all of the Stripe models, for Django. Set up your
webhook and start receiving model updates. You will then have a copy of
all the Stripe models available in Django models, no API traffic
required!

The full documentation is available here:
<https://dj-stripe.readthedocs.io/>

## Features

-   Subscriptions
-   Individual charges
-   Stripe Sources
-   Stripe v2 and v3 support
-   Supports SCA regulations, Checkout Sessions, and Payment Intents
-   Tested with Stripe API <span class="title-ref">2020-03-02</span>
    (see <https://dj-stripe.readthedocs.io/en/latest/api_versions.html>
    )

## Requirements

-   Django &gt;= 2.2
-   Python &gt;= 3.6
-   Supports Stripe exclusively. See "Similar Libraries" below for other
    solutions.
-   PostgreSQL engine (recommended): &gt;= 9.4
-   MySQL engine: MariaDB &gt;= 10.2 or MySQL &gt;= 5.7

## Similar libraries

-   [dj-paypal](https://github.com/HearthSim/dj-paypal)
    ([PayPal](https://www.paypal.com/))
-   [dj-paddle](https://github.com/dj-paddle/dj-paddle)
    ([Paddle](https://paddle.com/))

## Quickstart

Install dj-stripe:

    pip install dj-stripe

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

    STRIPE_LIVE_PUBLIC_KEY = os.environ.get("STRIPE_LIVE_PUBLIC_KEY", "<your publishable key>")
    STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "<your secret key>")
    STRIPE_TEST_PUBLIC_KEY = os.environ.get("STRIPE_TEST_PUBLIC_KEY", "<your publishable key>")
    STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "<your secret key>")
    STRIPE_LIVE_MODE = False  # Change to True in production
    DJSTRIPE_WEBHOOK_SECRET = "whsec_xxx"  # Get it from the section in the Stripe dashboard where you added the webhook endpoint

Add some payment plans via the Stripe.com dashboard.

Run the commands:

    python manage.py migrate

    python manage.py djstripe_init_customers

    python manage.py djstripe_sync_plans_from_stripe

See <https://dj-stripe.readthedocs.io/en/latest/stripe_elements_js.html>
for notes about usage of the Stripe Elements frontend JS library.

## Running the Tests

Assuming the tests are run against PostgreSQL:

    createdb djstripe
    pip install tox
    tox

# Funding this project

You can now become a sponsor to dj-stripe with [GitHub Sponsors](https://github.com/sponsors/dj-stripe).

We've been bringing dj-stripe to the world for over 7 years and are excited to be able to start
dedicating some real resources to the project.

Your sponsorship helps us keep a team of maintainers actively working to improve dj-stripe and
ensure it stays up-to-date with the latest Stripe changes. If you're using dj-stripe in a commercial
capacity and have the ability to start a sponsorship, we'd greatly appreciate the contribution.

All contributions through GitHub sponsors flow into our [Open Collective](https://opencollective.com/dj-stripe),
which holds our funds and keeps an open ledger on how donations are spent.
