Webhooks
========

Using webhooks in dj-stripe
---------------------------

dj-stripe comes with native support for webhooks as event listeners.

Events allow you to do things like `sending an email to a customer when his payment has failed <https://stripe.com/docs/recipes/sending-emails-for-failed-payments>`_
or trial period is ending.

This is how you use them:

.. code-block:: python
    from djstripe import webhooks

    @webhooks.handler("customer.subscription.trial_will_end")
    def my_handler(event, **kwargs):
        print("We should probably notify the user at this point")


In order to get registrations picked up, you need to put them in a module is imported like models.py or make sure you import it manually.

Official documentation
----------------------

Stripe docs for types of Events: https://stripe.com/docs/api/events/types
Stripe docs for Webhooks: https://stripe.com/docs/webhooks
