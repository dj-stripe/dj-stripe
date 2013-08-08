.. :changelog:

History
-------

0.1.5 (2013-08-08)
+++++++++++++++++++

* Fixed the manifest so we include html, css, js, images.

0.1.4 (2013-08-08)
+++++++++++++++++++

* Change PaymentRequiredMixin to SubscriptionPaymentRequiredMixin
* Add subscription_payment_required function-based view decorator
* Added SubscriptionPaymentRedirectMiddleware
* Much nicer accounts view display
* Much improved subscription form display
* Payment plans can have decimals
* Payment plans can have custom images

0.1.3 (2013-08-7)
++++++++++++++++++

* Added account view
* Added Customer.get_or_create method
* Added djstripe_sync_customers management command
* sync file for all code that keeps things in sync with stripe
* Use client-side JavaScript to get history data asynchronously
* More user friendly action views

0.1.2 (2013-08-6)
++++++++++++++++++

* Admin working
* Better publish statement
* Fix dependencies

0.1.1 (2013-08-6)
++++++++++++++++++

* Ported internals from django-stripe-payments
* Began writing the views
* Travis-CI
* All tests passing on Python 2.7 and 3.3
* All tests passing on Django 1.4 and 1.5
* Began model cleanup
* Better form
* Provide better response from management commands

0.1.0 (2013-08-5)
++++++++++++++++++

* First release on PyPI.