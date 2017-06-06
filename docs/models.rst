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
    .. automethod:: djstripe.models.Customer.upcoming_invoice

    .. automethod:: djstripe.models.Customer.str_parts
    .. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data


Event
-----
.. autoclass:: djstripe.models.Event

    .. automethod:: djstripe.stripe_objects.StripeObject.api_list
    .. automethod:: djstripe.models.Event.api_retrieve

    .. autoattribute:: djstripe.models.Event.message
    .. automethod:: djstripe.models.Event.validate
    .. automethod:: djstripe.models.Event.process

    .. automethod:: djstripe.models.Event.str_parts
    .. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data


Transfer
--------
.. autoclass:: djstripe.models.Transfer

    .. automethod:: djstripe.stripe_objects.StripeObject.api_list
    .. automethod:: djstripe.models.Transfer.api_retrieve

    .. autoattribute:: djstripe.models.Transfer.DESTINATION_TYPES
    .. autoattribute:: djstripe.models.Transfer.SOURCE_TYPES
    .. autoattribute:: djstripe.models.Transfer.FAILURE_CODES

    .. automethod:: djstripe.models.Transfer.str_parts
    .. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data


Card
----
.. autoclass:: djstripe.models.Card

    .. automethod:: djstripe.stripe_objects.StripeObject.api_list
    .. automethod:: djstripe.models.Card.api_retrieve

    .. autoattribute:: djstripe.models.Card.BRANDS
    .. autoattribute:: djstripe.models.Card.FUNDING_TYPES
    .. autoattribute:: djstripe.models.Card.CARD_CHECK_RESULTS
    .. autoattribute:: djstripe.models.Card.TOKENIZATION_METHODS

    .. automethod:: djstripe.models.Card.remove
    .. automethod:: djstripe.stripe_objects.StripeCard.create_token

    .. automethod:: djstripe.models.Card.str_parts
    .. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data


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


InvoiceItem
-----------
.. autoclass:: djstripe.models.InvoiceItem

    .. automethod:: djstripe.stripe_objects.StripeObject.api_list
    .. automethod:: djstripe.models.InvoiceItem.api_retrieve

    .. automethod:: djstripe.models.InvoiceItem.str_parts
    .. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data


Plan
----
.. autoclass:: djstripe.models.Plan

    .. automethod:: djstripe.stripe_objects.StripeObject.api_list
    .. automethod:: djstripe.models.Plan.api_retrieve

    .. automethod:: djstripe.models.Plan.get_or_create

    .. automethod:: djstripe.models.Plan.str_parts
    .. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data


Subscription
------------
.. autoclass:: djstripe.models.Subscription

    .. automethod:: djstripe.stripe_objects.StripeObject.api_list
    .. automethod:: djstripe.models.Subscription.api_retrieve

    .. automethod:: djstripe.models.Subscription.is_period_current
    .. automethod:: djstripe.models.Subscription.is_status_current
    .. automethod:: djstripe.models.Subscription.is_status_temporarily_current
    .. automethod:: djstripe.models.Subscription.is_valid

    .. automethod:: djstripe.models.Subscription.update
    .. automethod:: djstripe.models.Subscription.extend
    .. automethod:: djstripe.models.Subscription.cancel

    .. automethod:: djstripe.models.Subscription.str_parts
    .. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data
