Subscription
------------
.. autoclass:: djstripe.models.Subscription

.. automethod:: djstripe.stripe_objects.StripeObject.api_list
.. automethod:: djstripe.models.Subscription.api_retrieve

.. autoattribute:: djstripe.models.Subscription.STATUS_ACTIVE
.. autoattribute:: djstripe.models.Subscription.STATUS_TRIALING
.. autoattribute:: djstripe.models.Subscription.STATUS_PAST_DUE
.. autoattribute:: djstripe.models.Subscription.STATUS_CANCELED
.. autoattribute:: djstripe.models.Subscription.STATUS_CANCELLED
.. autoattribute:: djstripe.models.Subscription.STATUS_UNPAID

.. automethod:: djstripe.models.Subscription.is_period_current
.. automethod:: djstripe.models.Subscription.is_status_current
.. automethod:: djstripe.models.Subscription.is_status_temporarily_current
.. automethod:: djstripe.models.Subscription.is_valid

.. automethod:: djstripe.models.Subscription.update
.. automethod:: djstripe.models.Subscription.extend
.. automethod:: djstripe.models.Subscription.cancel

.. automethod:: djstripe.models.Subscription.str_parts
.. automethod:: djstripe.stripe_objects.StripeObject.sync_from_stripe_data
