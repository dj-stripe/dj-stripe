Invoice
-------
.. autoclass:: djstripe.models.Invoice

.. automethod:: djstripe.stripe_objects.StripeObject.api_list
.. automethod:: djstripe.models.Invoice.api_retrieve

.. autoattribute:: djstripe.models.Invoice.STATUS_PAID
.. autoattribute:: djstripe.models.Invoice.STATUS_FORGIVEN
.. autoattribute:: djstripe.models.Invoice.STATUS_CLOSED
.. autoattribute:: djstripe.models.Invoice.STATUS_OPEN
.. autoattribute:: djstripe.models.Invoice.status
.. autoattribute:: djstripe.models.Invoice.plan

.. automethod:: djstripe.models.Invoice.retry
.. automethod:: djstripe.models.Invoice.upcoming

.. automethod:: djstripe.models.Invoice.str_parts
.. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data
