# Managing Stripe API keys

Dj-Stripe can read your Stripe API keys from **either** your Django settings
(typically populated from environment variables) **or** the database. Both are
fully supported, and you can mix them.

- **Settings** are the simplest option and the right choice for most projects,
  especially if you deploy from environment variables, run in containers, or
  don't use the Django admin. A single Stripe account is supported this way.
- **The database** lets you store more than one key, which is required to operate
  on behalf of multiple Stripe accounts from a single instance. Keys added to the
  database are editable from the Django admin.

When dj-stripe needs a key, it first looks for one stored in the database for the
relevant account; if none is found, it falls back to the keys defined in your
settings.

## Using settings (environment variables)

Define the following in your Django settings:

```python
STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "")
STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "")

# Switches between the test and live secret keys above.
STRIPE_LIVE_MODE = False
```

You may instead set a single `STRIPE_SECRET_KEY`, which takes precedence over the
test/live keys regardless of `STRIPE_LIVE_MODE`.

These keys are picked up automatically by API calls, webhook processing and the
`djstripe_sync_models` management command — you do not need to add them to the
database first.

## Using the database

You may add new API keys via the Dj-Stripe "API key" administration. The only
required value is the key's "secret" value itself. Example:

![Adding an API key from the Django administration](https://user-images.githubusercontent.com/235410/99198962-2a1f2e00-279c-11eb-96cc-96dee0ba03ac.png)

Once saved, Dj-Stripe will automatically detect whether the key is a public,
restricted or secret key, and whether it's for live or test mode. If it's a
secret key, the matching Account object will automatically be fetched as well and
the key will be associated with it, so that it can be used to communicate with the
Stripe API when dealing with objects belonging to that Account.

_NOTE_: By default, keys in the database are visible to anyone who has access to
the dj-stripe administration.

### Updating database keys

When expiring or rolling new secret keys, you should create the new API key in
Stripe, then add it from the Django administration. Whenever you are ready, you
may delete the old key. (It is safe to keep it around, as long as it hasn't
expired. Keeping expired keys in the database may result in errors during usage).

## FAQ

### Which should I use?

If you only deal with a single Stripe account, settings (environment variables)
are the simplest and most common choice. Use the database when you need to store
multiple keys to act on behalf of multiple Stripe accounts.

### Why support storing them in the database?

Supporting multiple Stripe accounts per instance requires a mechanism to store
more than one Stripe API key. The database also allows proper programmatic access
to create and delete keys, and API keys are a legitimate upstream Stripe object.

### Isn't storing them in the database insecure?

Please do keep your billing database encrypted regardless: it holds a copy of all
your customers' billing data. If you'd rather not store full-access secret keys in
the database, you may create a read-only restricted key with all-read permissions
for dj-stripe, or simply keep your keys in settings.

### What about public keys?

The `STRIPE_LIVE_PUBLIC_KEY` and `STRIPE_TEST_PUBLIC_KEY` settings are only used by
the (deprecated) Dj-Stripe mixins. You can safely leave them in your settings or
move them to the database as well (keys beginning in `pk_test_` and `pk_live_`
are detected as publishable keys).
