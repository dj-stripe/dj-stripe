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

With no arguments this syncs all supported models for every secret key in the
database and in your settings. You can also name the models to sync.

```bash
    ./manage.py djstripe_sync_models Invoice Subscription
```

Note that this may be redundant since we recursively sync related
objects.

A list of models to sync can also be provided along with the API Keys.

```bash
    ./manage.py djstripe_sync_models Invoice Subscription --api-keys sk_test_XXX sk_test_YYY
```

Keys passed with `--api-keys` are used as given; they do not need to be in the
database.

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

For example, creating a product directly via the Stripe API and then syncing the
returned data into a dj-stripe `Product`:

```python
import stripe
from djstripe.models import Product

stripe_product = stripe.Product.create(
    name="Premium plan",
    api_key="sk_test_...",
)

# Returns the dj-stripe Product instance, created or updated from the data.
product = Product.sync_from_stripe_data(stripe_product)
```

Related objects referenced by the data are fetched and synced recursively. If you
don't pass `api_key`, dj-stripe falls back to the secret key from your settings.

### Syncing in bulk

Every object dj-stripe converts resolves the Stripe `Account` that owns the API
key it came from, which costs a couple of queries per object. That answer never
changes for a given key, so bulk syncs can hold on to it with
[`owner_account_cache`][djstripe.utils.owner_account_cache]:

```python
import stripe
from djstripe.models import Charge
from djstripe.utils import owner_account_cache

with owner_account_cache():
    for stripe_charge in stripe.Charge.list(api_key="sk_test_...").auto_paging_iter():
        Charge.sync_from_stripe_data(stripe_charge, api_key="sk_test_...")
```

The cache exists only for the duration of the block. dj-stripe applies it itself
around `djstripe_sync_models` runs and around webhook processing, so you only
need it for syncs you drive yourself.
