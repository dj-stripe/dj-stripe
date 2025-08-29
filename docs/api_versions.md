# A note on Stripe API versions

A point that can cause confusion to new users of dj-stripe is that there
are several different Stripe API versions in play at once.

## Your Stripe account's API version

This is the version used by Stripe when sending webhook data to you and the default version used by the Stripe API.
You can find this on [your Stripe dashboard](https://dashboard.stripe.com/developers) labelled "**default**".
New Stripe accounts are always on the latest version.

Read more about it on [stripe.com/docs/api/versioning](https://stripe.com/docs/api/versioning).


## Stripe's current latest API version

You can find this on your Stripe dashboard labelled "**latest**" or in
[Stripe's API documentation](https://stripe.com/docs/upgrades#api-changelog)

See [stripe.com/docs/upgrades](https://stripe.com/docs/upgrades#how-can-i-upgrade-my-api) on how to upgrade your Stripe API version.
Stripe will only allow upgrades to the **latest** version.

## Dj-stripe API version

This is the Stripe API version used by dj-stripe in all communication
with Stripe, including when processing webhooks (though webhook data is
sent to you by Stripe with your API version, we re-fetch the data with
dj-stripe's API version), this is because the API schema needs to match
dj-stripe's Django model schema.

It is defined by [`STRIPE_API_VERSION`](reference/settings.md#stripe_api_version-2020-08-27) with a default of
[`DEFAULT_STRIPE_API_VERSION`][djstripe.settings.DjstripeSettings.DEFAULT_STRIPE_API_VERSION].
You mustn't change this as it ensures that
dj-stripe receives data in the format it expects.

**Note:**
dj-stripe will always use `STRIPE_API_VERSION` in its requests
    regardless of what `stripe.api_version` is set to.

## Dj-stripe Latest Tested Version

This is the most recent Stripe account API version used by the
maintainers during testing, more recent versions account versions are
probably fine though.
