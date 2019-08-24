Manually syncing data with Stripe
=================================

If you're using dj-stripe's webhook handlers then data will be automatically synced from Stripe to the Django database,
but in some circumstances you may want to manually sync Stripe API data as well.

For example if you write to the Stripe API and want to work with the resulting dj-stripe object without having
to wait for the webhook trigger.

This can be done using the classmethod ``sync_from_stripe_data`` that exists on all dj-stripe model classes.

E.g. creating a product using the Stripe API, and then syncing the API return data to Django using dj-stripe:


.. literalinclude:: examples/manually_syncing_with_stripe.py
  :start-after: def
  :dedent: 1
