# What is dj-stripe?

dj-stripe implements Stripe models, for Django. It continuously syncs your Stripe
data to your local database via webhooks, exposing it as native Django models. You
work with subscriptions, invoices, charges and the rest of the Stripe object graph
through the Django ORM — querying your own database instead of making repeated,
slower calls to the Stripe API.

Set up your webhook endpoint, point Stripe at it, and your database stays in sync
with Stripe automatically.

## Why use it?

-   **Query Stripe data with the ORM.** A customer's subscriptions, invoices and
    payment methods are Django models with real foreign keys. Fetch a customer and
    their related objects in a single query instead of several network round-trips.
-   **Stay in sync automatically.** dj-stripe's webhook handlers keep your local
    models up to date as things change in Stripe. You can also
    [sync on demand](usage/manually_syncing_with_stripe.md).
-   **Built-in webhook handling.** Signature verification, event storage and
    [Django signals](usage/webhooks.md) for every event type, out of the box.
-   **Multiple accounts and API keys.** Operate on behalf of several Stripe
    accounts from a single instance — see [Managing API keys](api_keys.md).
-   **Tested against the latest Stripe API.** dj-stripe pins a known-good Stripe
    API version (see [API versions](api_versions.md)).

## Getting started

1.  [Install dj-stripe](installation.md) and run its migrations.
2.  [Add your Stripe API keys](api_keys.md).
3.  [Set up a webhook endpoint](usage/webhooks.md) so Stripe can notify your app.
4.  [Sync your existing Stripe data](usage/manually_syncing_with_stripe.md).

From there, the [usage guides](usage/subscribing_customers.md) cover the common
flows: subscribing customers, creating charges, using Stripe Checkout, and
reacting to webhook events.

## Tutorials

Community-written tutorials and blog posts. These are maintained externally and
may target older versions of dj-stripe, Django or the Stripe API — treat them as
supplementary to this documentation.

-   [How to Create a Subscription SaaS Application with Django and Stripe](https://www.saaspegasus.com/guides/django-stripe-integrate/)

Written something about dj-stripe? Open a pull request to add it here.
