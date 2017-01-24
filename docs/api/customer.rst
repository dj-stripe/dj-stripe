Customer
--------
.. autoclass:: djstripe.models.Customer

.. automethod:: djstripe.stripe_objects.StripeObject.api_list
.. automethod:: djstripe.models.Customer.api_retrieve

.. automethod:: djstripe.models.Customer.get_or_create
.. automethod:: djstripe.models.Customer.purge
.. automethod:: djstripe.models.Customer.has_active_subscription
.. automethod:: djstripe.models.Customer.has_any_active_subscription
.. autoattribute:: djstripe.models.Customer.subscription
.. automethod:: djstripe.models.Customer.subscribe
.. automethod:: djstripe.models.Customer.can_charge
.. automethod:: djstripe.models.Customer.charge
.. automethod:: djstripe.models.Customer.add_invoice_item
.. automethod:: djstripe.models.Customer.send_invoice
.. automethod:: djstripe.models.Customer.retry_unpaid_invoices
.. automethod:: djstripe.models.Customer.has_valid_source
.. automethod:: djstripe.models.Customer.add_card
.. automethod:: djstripe.models.Customer.upcoming_invoice

.. automethod:: djstripe.models.Customer.str_parts
.. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data
