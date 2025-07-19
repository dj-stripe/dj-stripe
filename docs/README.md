# dj-stripe - Django + Stripe Made Easy

[![Stripe Verified Partner](https://img.shields.io/static/v1?label=Stripe&message=Verified%20Partner&color=red&style=for-the-badge)](https://stripe.com/docs/libraries#community-libraries)

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
-   Tested with latest Stripe API (see [API versions](api_versions.md#dj-stripe_latest_tested_version))

## Requirements

-   Django >=5.0
-   Python >=3.11
-   PostgreSQL engine (recommended) >=12
-   MySQL engine: MariaDB >=10.5 or MySQL >=8.0
-   SQLite: Not recommended in production. Version >=3.26 required.

## Installation

See [installation](https://dj-stripe.dev/docs/latest/installation/) instructions.

## Changelog

[See release notes](https://dj-stripe.dev/changes).

## Funding and Support

[![Funded by Stripe](./logos/stripe_blurple.svg)](https://stripe.com)

You can now become a sponsor to dj-stripe with [GitHub Sponsors](https://github.com/sponsors/dj-stripe).

We've been bringing dj-stripe to the world for over 10 years and are excited to be able to start
dedicating some real resources to the project.

Your sponsorship helps us keep a team of maintainers actively working to improve dj-stripe and
ensure it stays up-to-date with the latest Stripe changes. If you use dj-stripe commercially, we would encourage you to invest in its continued
development by [signing up for a paid plan](https://github.com/sponsors/dj-stripe).
Corporate sponsors [receive priority support and development time](project/support.md).

## Similar libraries

-   [dj-paypal](https://github.com/HearthSim/dj-paypal)
    ([PayPal](https://www.paypal.com/))
-   [dj-paddle](https://github.com/paddle-python/dj-paddle)
    ([Paddle](https://paddle.com/))
