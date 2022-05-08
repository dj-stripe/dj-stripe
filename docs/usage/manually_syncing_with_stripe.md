# Manually syncing data with Stripe

If you're using dj-stripe's webhook handlers then data will be
automatically synced from Stripe to the Django database, but in some
circumstances you may want to manually sync Stripe API data as well.

## Command line

You can sync your database with stripe using the management command
[`djstripe_sync_models`][djstripe.management.commands.djstripe_sync_models], e.g. to populate an empty database from an
existing Stripe account.
```bash

    ./manage.py djstripe_sync_models
```
With no arguments this will sync all supported models for all in database API Keys , or a list of
models to sync can also be provided.
```bash
    ./manage.py djstripe_sync_models Invoice Subscription
```
Note that this may be redundant since we recursively sync related
objects.

A list of models to sync can also be provided along with the API Keys.
```bash
    ./manage.py djstripe_sync_models Invoice Subscription --api-keys sk_test_XXX sk_test_YYY
```
This will sync all the Invoice and Subscription data for the given API Keys. Please note that the API Keys sk_test_YYY and sk_test_XXX need to be in the database.

You can manually reprocess events using the management commands
[`djstripe_process_events`][djstripe.management.commands.djstripe_process_events]. By default this processes all events, but
options can be passed to limit the events processed. Note the Stripe API
documents a limitation where events are only guaranteed to be available
for 30 days.

```bash
    # all events
    ./manage.py djstripe_process_events
    # failed events (events with pending webhooks or where all webhook delivery attempts failed)
    ./manage.py djstripe_process_events --failed
    # filter by event type (all payment_intent events in this example)
    ./manage.py djstripe_process_events --type payment_intent.*
    # specific events by ID
    ./manage.py djstripe_process_events --ids evt_foo evt_bar
    # more output for debugging processing failures
    ./manage.py djstripe_process_events -v 2
```

## In Code

To sync in code, for example if you write to the Stripe API and want to
work with the resulting dj-stripe object without having to wait for the
webhook trigger.

This can be done using the classmethod [`sync_from_stripe_data`][djstripe.models.base.StripeModel.sync_from_stripe_data] that
exists on all dj-stripe model classes.

E.g. creating a product using the Stripe API, and then syncing the API
return data to Django using dj-stripe:
