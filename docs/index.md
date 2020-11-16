# dj-stripe - Django + Stripe Made Easy

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

## Funding and Support

You can now become a sponsor to dj-stripe with [GitHub Sponsors](https://github.com/sponsors/dj-stripe).

If you use dj-stripe commercially, we would encourage you to invest in its continued
development by [signing up for a paid plan](https://github.com/sponsors/dj-stripe).
Corporate sponsors [receive priority support and development time](project/support.md).

All contributions through GitHub sponsors flow into our
[Open Collective](https://opencollective.com/dj-stripe), which holds our funds and keeps
an open ledger on how donations are spent.

### Our Gold sponsors

<style>
img[alt="Stripe Logo"] {
    max-width: 250px;
}
</style>

[![Stripe Logo](./logos/stripe_blurple.svg)](https://stripe.com)

<!--
AUTODOC SETUP: Do not remove the piece of code below.

We use mkautodoc (https://github.com/tomchristie/mkautodoc) throughout the documentation.
It works by importing, at docs build time, various attributes from our codebase and
inspecting its docstrings, members etc.
However, throughout our codebase, we call various pieces of Django's machinery. As you
might know, this requires calling django.setup() beforehand…

Autodoc has no way to run code at initialization time. So, as one of the ugliest
workarounds ever written, we force import a member of docs.django_settings initializer,
which runs django.setup() when imported.

We do this in the index.md so that it's done as the very first processed document.

Also see: https://github.com/tomchristie/mkautodoc/issues/16
-->

<style type="text/css">
/* Hide the hack signature from the index. */
.autodoc { display: none; }
</style>

::: docs.django_settings.setup
