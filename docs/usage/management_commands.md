# Management commands

dj-stripe ships several Django management commands for syncing data and operating
your installation. Run any of them with `python manage.py <command>`.

## Syncing data

### `djstripe_sync_models`

Syncs Stripe API data into the local database — for example to populate an empty
database from an existing Stripe account. See
[Manually syncing data with Stripe](manually_syncing_with_stripe.md) for full usage,
including syncing specific models and per–API-key syncing.

### `djstripe_process_events`

Re-processes `Event` objects (for example, events whose webhook delivery failed).
See [Manually syncing data with Stripe](manually_syncing_with_stripe.md#command-line).

## Customers

### `djstripe_init_customers`

Creates `Customer` objects for existing subscribers that don't have one yet. Useful
after installing dj-stripe into a project that already has users.

### `djstripe_sync_customers`

Syncs each subscriber's customer data with Stripe.

## Maintenance

### `djstripe_clear_expired_idempotency_keys`

Deletes expired Stripe [idempotency keys](../settings.md#djstripe_idempotency_key_callback)
from the database. Safe to run periodically (e.g. as a scheduled task), since
expired keys are no longer useful.

## Local development

### `stripe_listen`

Runs the [Stripe CLI](https://stripe.com/docs/cli)'s `stripe listen` and forwards
webhook events to your local dj-stripe endpoint, wiring up the webhook signing
secret for you. See [Local webhook testing](local_webhook_testing.md) for the
underlying workflow.
