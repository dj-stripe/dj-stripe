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
------
.. autoclass:: djstripe.models.Customer
    
    .. autoattribute:: djstripe.models.Charge.STATUS_SUCCEEDED
    .. autoattribute:: djstripe.models.Charge.STATUS_FAILED
    .. autoattribute:: djstripe.models.Charge.CARD_ERROR_CODES
    
    .. automethod:: djstripe.stripe_objects.StripeObject.api_list
    .. automethod:: djstripe.models.Charge.api_retrieve
    
    .. automethod:: djstripe.models.Customer.purge
    .. automethod:: djstripe.models.Charge.refund
    
    .. automethod:: djstripe.models.Customer.str_parts
    .. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data

