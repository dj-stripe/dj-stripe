Subscribing a customer to a plan
================================

See this example from ``tests.apps.example.views.PurchaseSubscriptionView.form_valid``

.. literalinclude:: ../../tests/apps/example/views.py
   :pyobject: PurchaseSubscriptionView.form_valid
   :start-after: User.objects.create
   :end-before: self.request.subscription
   :dedent: 2
