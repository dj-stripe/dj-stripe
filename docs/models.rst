Models
======

Models hold the bulk of the functionality included in the dj-stripe package.
Each model is tied closely to its corresponding object in the stripe dashboard.
Fields that are not implemented for each model have a short reason behind the decision
in the docstring for each model.

.. note::

    Some model methods documented as classmethods show the base "StripeObject"
    instead of the model. When using these methods, be sure to replace "StripeObject"
    with the actual class name.


Charge
------
.. autoclass:: djstripe.models.Charge
    
    .. autoattribute:: djstripe.models.Charge.STATUS_SUCCEEDED
    .. autoattribute:: djstripe.models.Charge.STATUS_FAILED
    .. autoattribute:: djstripe.models.Charge.CARD_ERROR_CODES
    
    .. automethod:: djstripe.stripe_objects.StripeObject.api_list
    .. automethod:: djstripe.models.Charge.api_retrieve
    
    .. automethod:: djstripe.models.Charge.capture
    .. automethod:: djstripe.models.Charge.refund
    
    .. automethod:: djstripe.models.Charge.str_parts
    .. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data


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
    
    .. automethod:: djstripe.models.Customer.str_parts
    .. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data

