# dj-stripe - Django + Stripe Made Easy

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
-   Tested with Stripe API `2020-08-27` (see [API versions](api_versions.md))

## Requirements

-   Django 2.2+
-   Python 3.6+
-   PostgreSQL engine (recommended) 9.5+
-   MySQL engine: MariaDB 10.2+ or MySQL 5.7+ (Django 3.2.5+ required for MySQL 8 support)
-   SQLite: Not recommended in production. Version 3.26+ required.


--8<-- "docs/installation.md"


## Changelog

[See release notes on Read the Docs](https://dj-stripe.readthedocs.io/en/latest/history/2_5_0/).

## Funding and Support

[![Stripe Logo](./logos/stripe_blurple.svg)](https://stripe.com)

You can now become a sponsor to dj-stripe with [GitHub Sponsors](https://github.com/sponsors/dj-stripe).

We've been bringing dj-stripe to the world for over 7 years and are excited to be able to start
dedicating some real resources to the project.

Your sponsorship helps us keep a team of maintainers actively working to improve dj-stripe and
ensure it stays up-to-date with the latest Stripe changes. If you use dj-stripe commercially, we would encourage you to invest in its continued
development by [signing up for a paid plan](https://github.com/sponsors/dj-stripe).
Corporate sponsors [receive priority support and development time](project/support.md).

All contributions through GitHub sponsors flow into our [Open Collective](https://opencollective.com/dj-stripe), which holds our funds and keeps
an open ledger on how donations are spent.

## Our Gold sponsors

<style>
img[alt="Stripe Logo"] {
    max-width: 250px;
}
</style>

[![Stripe Logo](./logos/stripe_blurple.svg)](https://stripe.com)


## Similar libraries

-   [dj-paypal](https://github.com/HearthSim/dj-paypal)
    ([PayPal](https://www.paypal.com/))
-   [dj-paddle](https://github.com/paddle-python/dj-paddle)
    ([Paddle](https://paddle.com/))
