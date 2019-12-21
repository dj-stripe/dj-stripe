Subscribing a customer to a plan
================================

For your convenience, dj-stripe provides a :meth:`djstripe.models.Customer.subscribe`
method that will try to charge the customer immediately unless you specify
``charge_immediately=False``

.. code-block:: python

    plan = Plan.objects.get(nickname="one_plan")
    customer = Customer.objects.first()
    customer.subscribe(plan)

However in some cases :meth:`djstripe.models.Customer.subscribe` might not support all
the arguments you need for your implementation. When this happens you can just call the
official ``stripe.Customer.subscribe()``.

See this example from ``tests.apps.example.views.PurchaseSubscriptionView.form_valid``

.. literalinclude:: ../../tests/apps/example/views.py
   :pyobject: PurchaseSubscriptionView.form_valid
   :start-after: User.objects.create
   :end-before: self.request.subscription
   :dedent: 2


Note that PaymentMethods can be used instead of Cards/Source by substituting

.. code-block:: python

    # Add the payment method customer's default
    customer.add_payment_method(payment_method)

instead of

.. code-block:: python

    # Add the source as the customer's default card
    customer.add_card(stripe_source)


in the above example.  See :meth:`djstripe.models.Customer.add_payment_method`.
