Subscribing a customer to a plan
================================

For your convenience, dj-stripe provides a ``Customer.subscribe()`` method that
will try to charge the customer immediately unless you specify ``charge_immediately=False``

.. code-block:: python

    plan = Plan.objects.get(nickname="one_plan")
    customer = Customer.objects.first()
    customer.subscribe(plan)

However in some cases ``Customer.subscribe()`` might not support all the arguments
you need for your implementation. When this happens you can just call the
official ``stripe.Customer.subscribe()``.

See this example from ``tests.apps.example.views.PurchaseSubscriptionView.form_valid``

.. literalinclude:: ../../tests/apps/example/views.py
   :pyobject: PurchaseSubscriptionView.form_valid
   :start-after: User.objects.create
   :end-before: self.request.subscription
   :dedent: 2
