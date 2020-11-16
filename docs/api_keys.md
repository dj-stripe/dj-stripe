# Managing Stripe API keys

Stripe API keys are stored in the database, and editable from the Django admin.

**Important note**: By default, keys are visible by anyone who has access to the
dj-stripe administration.

### Adding new API keys

You may add new API keys via the Dj-Stripe "API key" administration. The only required
value is the key's "secret" value itself. Example:

![Adding an API key from the Django administration](https://user-images.githubusercontent.com/235410/99198962-2a1f2e00-279c-11eb-96cc-96dee0ba03ac.png)

Once saved, Dj-Stripe will automatically detect whether the key is a public, restricted
or secret key, and whether it's for live or test mode. If it's a secret key, the
matching Account object will automatically be fetched as well and the key will be
associated with it, so that it can be used to communicate with the Stripe API when
dealing with objects belonging to that Account.

### Updating the API keys

When expiring or rolling new secret keys, you should create the new API key in Stripe,
then add it from the Django administration. Whenever you are ready, you may delete the
old key. (It is safe to keep it around, as long as it hasn't expired. Keeping expired
keys in the database may result in errors during usage).

### FAQ

#### Why store them in the database?

As we work on supporting multiple Stripe accounts per instance, it is vital for
dj-stripe to have a mechanism to store more than one Stripe API key. It also became
obvious that we may want proper programmatic access to create and delete keys.
Furthermore, API keys are a legitimate upstream Stripe object, and it is not unlikely
the API may allow access to listing other API keys in the future, in which case we will
want to move them to the database anyway.

#### Isn't that insecure?

Please do keep your billing database encrypted. There's a copy of all your customers'
billing data on it!

You may also instead create a read-only restricted key with all-read permissions for
dj-stripe. There is no added risk there, given that dj-stripe holds a copy of all your
data regardless.

### I'm using environment variables. Do I need to change anything?

Not at this time. The settings `STRIPE_LIVE_SECRET_KEY` and `STRIPE_TEST_SECRET_KEY` can
still be used. Their values will however be automatically saved to the database at the
earliest opportunity.

### What about public keys?

Setting `STRIPE_LIVE_PUBLIC_KEY` and `STRIPE_TEST_PUBLIC_KEY` will be deprecated in
2.5.0. You do not risk anything by leaving them in your settings: They are not used by
Dj-Stripe outside of the Dj-Stripe mixins, which are now themselves deprecated. So you
can safely leave them in your settings, or you can move them to the database as well
(Keys beginning in `pk_test_` and `pk_live_` will be detected as publishable keys).
