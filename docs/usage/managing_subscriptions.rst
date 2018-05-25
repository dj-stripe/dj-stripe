Managing subscriptions and payment sources
==========================================

Extending subscriptions
-----------------------

``Subscription.extend(*delta*)``

Subscriptions can be extended by using the ``Subscription.extend`` method, which takes a positive ``timedelta`` as its only property. This method is useful if you want to offer time-cards, gift-cards, or some other external way of subscribing users or extending subscriptions, while keeping the billing handling within Stripe.

.. warning::

    Subscription extensions are achieved by manipulating the ``trial_end`` of the subscription instance, which means that Stripe will change the status to ``trialing``.