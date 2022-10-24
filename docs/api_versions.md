# A note on Stripe API versions

A point that can cause confusion to new users of dj-stripe is that there
are several different Stripe API versions in play at once.

!!! attention
    Don't touch the [STRIPE_API_VERSION](reference/settings.md#stripe_api_version-2020-08-27) setting, but don't worry,
    it doesn't need to match your Stripe account api version.

See also [Stripe API Versioning](https://stripe.com/docs/api/versioning)

## Your Stripe account's API version

You can find this on [your Stripe dashboard](https://dashboard.stripe.com/developers) labelled "**default**"

For new accounts this will be the latest Stripe version. When upgrading
version Stripe only allows you to upgrade to the **latest** version.

!!! tip
    Checkout [Stripe Version Upgrade](https://stripe.com/docs/upgrades#how-can-i-upgrade-my-api) Documentation for Upgrading Stripe API version


!!! note
    This is the version used by Stripe when sending webhook data to you
    (though during webhook processing, dj-stripe re-fetches the data with
    its preferred version). It's also the default version used by the Stripe
    API, but dj-stripe overrides the API version when talking to stripe
    (this override is triggered on import of `djstripe.models`).

    As a result your Stripe account API version is mostly irrelevant, though
    from time to time we will increase the minimum supported API version,
    and it's good practise to regularly upgrade to the latest version with
    appropriate testing.

## Stripe's current latest API version

You can find this on your Stripe dashboard labelled "**latest**" or in
[Stripe's API documentation]
(https://stripe.com/docs/upgrades#api-changelog)

This is the version used by new accounts and it's also "**true**" internal
version of Stripe's API

!!! tip
    Checkout [Stripe API Versioning](https://stripe.com/blog/api-versioning)


## Dj-stripe API version

This is the Stripe API version used by dj-stripe in all communication
with Stripe, including when processing webhooks (though webhook data is
sent to you by Stripe with your API version, we re-fetch the data with
dj-stripe's API version), this is because the API schema needs to match
dj-stripe's Django model schema.

This is defined by [`djstripe.settings.djstripe_settings.DEFAULT_STRIPE_API_VERSION`][djstripe.settings.DjstripeSettings.DEFAULT_STRIPE_API_VERSION] and
can be overridden by the function, [`djstripe.settings.djstripe_settings.set_stripe_api_version`][djstripe.settings.DjstripeSettings.set_stripe_api_version], though see the warning
about doing this.


## Dj-stripe Latest Tested Version

This is the most recent Stripe account API version used by the
maintainers during testing, more recent versions account versions are
probably fine though.
