# dj-stripe - Django + Stripe Made Easy

[![Stripe Verified Partner](https://img.shields.io/static/v1?label=Stripe&message=Verified%20Partner&color=red&style=for-the-badge)](https://stripe.com/docs/libraries#community-libraries)
<br>

[![CI tests](https://github.com/dj-stripe/dj-stripe/actions/workflows/ci.yml/badge.svg)](https://github.com/dj-stripe/dj-stripe/actions/workflows/ci.yml)
[![Package Downloads](https://img.shields.io/pypi/dm/dj-stripe)](https://pypi.org/project/dj-stripe/)
[![Documentation](https://img.shields.io/static/v1?label=Docs&message=READ&color=informational&style=plastic)](https://dj-stripe.github.io/dj-stripe/)
[![Sponsor dj-stripe](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=red&style=plastic)](https://github.com/sponsors/dj-stripe)
[![MIT License](https://img.shields.io/static/v1?label=License&message=MIT&color=informational&style=plastic)](https://github.com/sponsors/dj-stripe)

Stripe Models for Django.

## Introduction

dj-stripe implements all of the Stripe models, for Django. Set up your
webhook endpoint and start receiving model updates. You will then have
a copy of all the Stripe models available in Django models, as soon as
they are updated!

The full documentation is available [on Read the Docs](https://dj-stripe.github.io/dj-stripe/).

## Features

-   Stripe Core
-   Stripe Billing
-   Stripe Cards (JS v2) and Sources (JS v3)
-   Payment Methods and Payment Intents (SCA support)
-   Support for multiple accounts and API keys
-   Stripe Connect (partial support)
-   Tested with Stripe API `2020-08-27` (see [API versions](api_versions.md#dj-stripe_latest_tested_version))

## Requirements

-   Django >=3.2
-   Python >=3.7.12
-   PostgreSQL engine (recommended) >=9.6
-   MySQL engine: MariaDB >=10.2 or MySQL >=5.7
-   SQLite: Not recommended in production. Version >=3.26 required.

## Installation

See [installation](docs/installation.md) instructions.

## Changelog

[See release notes on Read the Docs](https://dj-stripe.github.io/dj-stripe/history/2_5_0/).

## Funding and Support

<a href="https://stripe.com">
  <img alt="Stripe Logo" src="./logos/stripe_blurple.svg" width="250px" />
</a>

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

<a href="https://stripe.com">
  <img alt="Stripe Logo" src="./logos/stripe_blurple.svg" width="250px" />
</a>

## Similar libraries

-   [dj-paypal](https://github.com/HearthSim/dj-paypal)
    ([PayPal](https://www.paypal.com/))
-   [dj-paddle](https://github.com/paddle-python/dj-paddle)
    ([Paddle](https://paddle.com/))
