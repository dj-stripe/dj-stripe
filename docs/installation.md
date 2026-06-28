# Installation

## Install the package

Install dj-stripe with [uv](https://docs.astral.sh/uv/) (recommended):

```bash
uv add dj-stripe
```

Or with pip:

```bash
pip install dj-stripe
```

## Configuration

Add `djstripe` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = (
    ...
    "djstripe",
    ...
)
```

Include the dj-stripe URLs in your `urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    ...
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
]
```

Add your Stripe keys and set the operating mode:

```python
import os

STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "")
STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "")
STRIPE_LIVE_MODE = False  # Change to True in production

# Use the Stripe object id (e.g. "sub_...") as the foreign-key target.
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"
```

See [Managing API keys](api_keys.md) for the full set of options, including storing
keys in the database to support multiple Stripe accounts.

**Note:** `STRIPE_LIVE_MODE` must be a real boolean. If you populate it from an
environment variable (which is always a string), convert it explicitly. The
[django-environ](https://django-environ.readthedocs.io/en/latest/) library handles
this for you.

## Run migrations and sync

Create the dj-stripe tables and pull down your existing Stripe data:

```bash
python manage.py migrate
python manage.py djstripe_sync_models
```

`djstripe_sync_models` syncs data for every API key it can find (from your settings
or the database). See [Manually syncing data with Stripe](usage/manually_syncing_with_stripe.md)
for details.

## Next steps

-   [Set up a webhook endpoint](usage/webhooks.md) so Stripe keeps your database in
    sync automatically.
-   If you collect card details in the browser, read
    [Integrating Stripe Elements](stripe_elements_js.md#integrating-stripe-elements-js-sdk).
