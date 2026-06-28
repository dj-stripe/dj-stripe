# Settings

dj-stripe is configured through Django settings. All of its own settings are
prefixed with `DJSTRIPE_`; it also reads the standard `STRIPE_*` keys for API
credentials.

## API keys and mode

These configure how dj-stripe authenticates with Stripe. See
[Managing API keys](api_keys.md) for the full picture, including storing keys in
the database for multiple accounts.

| Setting | Default | Description |
| --- | --- | --- |
| `STRIPE_TEST_SECRET_KEY` | `""` | Secret key used when `STRIPE_LIVE_MODE` is `False`. |
| `STRIPE_LIVE_SECRET_KEY` | `""` | Secret key used when `STRIPE_LIVE_MODE` is `True`. |
| `STRIPE_SECRET_KEY` | — | If set, overrides both of the above regardless of mode. |
| `STRIPE_LIVE_MODE` | `False` | Selects between the test and live secret keys. Must be a real boolean. |
| `STRIPE_TEST_PUBLIC_KEY` / `STRIPE_LIVE_PUBLIC_KEY` / `STRIPE_PUBLIC_KEY` | `""` | Publishable keys. Only used by the deprecated dj-stripe mixins. |

## Stripe API

| Setting | Default | Description |
| --- | --- | --- |
| `STRIPE_API_VERSION` | [`DEFAULT_STRIPE_API_VERSION`][djstripe.settings.DjstripeSettings.DEFAULT_STRIPE_API_VERSION] | The Stripe API version dj-stripe uses. **Do not change this** — it must match dj-stripe's model schema. See [API versions](api_versions.md). |
| `STRIPE_API_HOST` | — | Alternate Stripe API base URL, e.g. for [stripe-mock](https://github.com/stripe/stripe-mock). Read once at startup. |

## Models

### `DJSTRIPE_FOREIGN_KEY_TO_FIELD`

**Required.** Determines which column dj-stripe's foreign keys point at:

-   `"id"` — the Stripe object id (e.g. `sub_...`). Use this for all **new**
    installations.
-   `"djstripe_id"` — dj-stripe's internal integer primary key. Use this only if
    you installed dj-stripe before this setting existed and have not migrated.

dj-stripe raises a [system check](https://docs.djangoproject.com/en/stable/topics/checks/)
error (`djstripe.E002` / `djstripe.E003`) if this is unset or invalid.

### `DJSTRIPE_SUBSCRIBER_MODEL`

By default, a `Customer` is linked to your `AUTH_USER_MODEL`. Set this to link
customers to a different model instead — for example an `Organization` or `Team`
for B2B billing:

```python
DJSTRIPE_SUBSCRIBER_MODEL = "myapp.Organization"
```

The model **must** have an `email` attribute. It is specified as an
`"app_label.ModelName"` string. If the model lives in a third-party app, you may
also need to set `DJSTRIPE_SUBSCRIBER_MODEL_MIGRATION_DEPENDENCY` to the migration
dj-stripe's initial migration should depend on (defaults to `"__first__"`).

### `DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK`

A callable taking the current `request` and returning the subscriber instance.
Defaults to `lambda request: request.user`. Override this when the subscriber is
not simply the logged-in user (e.g. the user's current organization):

```python
DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK = lambda request: request.user.organization
```

### `DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY`

Default: `"djstripe_subscriber"`. The Stripe metadata key dj-stripe writes on
`Customer` objects to record which subscriber they belong to. This is also the key
you set in [Stripe Checkout](usage/using_stripe_checkout.md) metadata to link a
session back to a subscriber.

## Webhooks

See [Using Stripe Webhooks](usage/webhooks.md) for the full webhook guide.

| Setting | Default | Description |
| --- | --- | --- |
| `DJSTRIPE_WEBHOOK_VALIDATION` | `"verify_signature"` | How incoming webhooks are validated. `"verify_signature"` (recommended) verifies Stripe's signature; `"retrieve_event"` re-fetches each event from the API to confirm it; `None` disables validation (**not recommended**). |
| `DJSTRIPE_WEBHOOK_SECRET` | — | The signing secret used with `"verify_signature"` when you are not using per-endpoint secrets stored by dj-stripe. |
| `DJSTRIPE_WEBHOOK_URL` | `r"^webhook/$"` | Regex for the legacy webhook URL. New installations use UUID endpoints created from the admin instead. |

## Advanced

### `DJSTRIPE_IDEMPOTENCY_KEY_CALLBACK`

A callable `(object_type, action, livemode) -> str` used to generate
[idempotency keys](https://stripe.com/docs/api/idempotent_requests) for Stripe
requests. By default dj-stripe stores and reuses keys via its `IdempotencyKey`
model.
