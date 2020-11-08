# A note on Stripe API keys

Since 2.4.0 dj-stripe supports API keys in the database.

You can now add keys via the admin but dj-stripe will still use,
by default, the keys defined in `settings.py`.

The keys defined in `settings.py` will be synced to the database on the
next successful request.
