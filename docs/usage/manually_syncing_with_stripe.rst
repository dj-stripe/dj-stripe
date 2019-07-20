Manually syncing data with Stripe
=================================

If you're using dj-stripe's webhook handlers then data will be automatically synced from Stripe to the Django database,
but in some circumstances you may want to manually sync Stripe API data as well.

Command line
------------

You can sync your database with stripe using the manage command ``djstripe_sync_models``,
e.g. to populate an empty database from an existing Stripe account.

.. code-block::

	./manage.py djstripe_sync_models


With no arguments this will sync all supported models, or a list of models to sync can be provided.

.. code-block::

	./manage.py djstripe_sync_models Invoice Subscription


Note that this may be redundant since we recursively sync related objects.


In Code
-------

To sync in code, for example if you write to the Stripe API and want to work with the resulting
dj-stripe object without having to wait for the webhook trigger.

This can be done using the classmethod ``sync_from_stripe_data`` that exists on all dj-stripe model classes.

E.g. creating a product using the Stripe API, and then syncing the API return data to Django using dj-stripe:


.. literalinclude:: examples/manually_syncing_with_stripe.py
  :start-after: def
  :dedent: 1
