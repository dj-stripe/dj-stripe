## Installation

### Get the distribution

Install dj-stripe with pip:
```bash

    pip install dj-stripe
```

Or with [Poetry](https://python-poetry.org/) (recommended):
```bash
    poetry add dj-stripe
```

### Configuration

Add `djstripe` to your `INSTALLED_APPS`:
```bash
    INSTALLED_APPS =(
        ...
        "djstripe",
        ...
    )
```

Add to urls.py:

```bash

    path("stripe/", include("djstripe.urls", namespace="djstripe")),
```

Tell Stripe about the webhook (Stripe webhook docs can be found
[here](https://stripe.com/docs/webhooks)) using the full URL of your
endpoint from the urls.py step above (e.g.
`https://example.com/stripe/webhook`).

Add your Stripe keys and set the operating mode:
```bash

    STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "<your secret key>")
    STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "<your secret key>")
    STRIPE_LIVE_MODE = False  # Change to True in production
    DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"
```

**Note:**

    djstripe expects `STRIPE_LIVE_MODE` to be a Boolean Type. In case you use `Bash env vars or equivalent` to inject its value, make sure to convert it to a Boolean type. We highly recommended the library [django-environ](https://django-environ.readthedocs.io/en/latest/)


Sync data from Stripe:

**Note:**

    djstripe expects `APIKeys` of all Stripe Accounts you'd like to sync data for to already be in the DB. They can be Added from Django Admin.


Run the commands:

```bash
    python manage.py migrate

    python manage.py djstripe_sync_models
```

See [here](stripe_elements_js.md#integrating_stripe_elements-js_sdk) for notes about usage of the Stripe Elements
frontend JS library.

### Running Tests

Assuming the tests are run against PostgreSQL:

```bash
    createdb djstripe
    pip install tox
    tox
```
