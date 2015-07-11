.. :changelog:

History
=======

0.6.0 (2015-07-??)
---------------------

* Support for Django 1.6 and lower is now deprecated.
* Improved test harness now tests coverage and pep8
* SubscribeFormView and ChangePlanView no longer populate self.error with form errors
* InvoiceItems.plan can now be null (as it is with individual charges), resolving #140 (Thanks @awechsler and @MichelleGlauser for help troubleshooting)
* Email templates are now packaged during distribution.
* sync_plans now takes an optional api_key
* 100% test coverage
* Stripe ID is now returned as part of each model's str method
* Customer model now stores card expiration month and year (Thanks @jpadilla)
* Ability to extend subscriptions (Thanks @TigerDX)
* Rest API endpoints for Subscriptions [contrib] (Thanks @philippeluickx)
* Admin interface search by email funtionality is removed (#221) (Thanks @jpadilla)

0.5.0 (2015-05-25)
---------------------

* Began deprecation of support for Django 1.6 and lower.
* Added formal support for Django 1.8.
* Removed the StripeSubscriptionSignupForm
* Removed ``djstripe.safe_settings``. Settings are now all located in ``djstripe.settings``
* ``DJSTRIPE_TRIAL_PERIOD_FOR_SUBSCRIBER_CALLBACK`` can no longer be a module string
* The sync_subscriber argument has been renamed from subscriber_model to subscriber
* Moved available currencies to the DJSTRIPE_CURRENCIES setting (Thanks @martinhill)
* Allow passing of extra parameters to stripe Charge API (Thanks @mthornhill)
* Support for all available arguments when syncing plans (Thanks @jamesbrobb)
* charge.refund() now returns the refunded charge object (Thanks @mthornhill)
* Charge model now has captured field and a capture method (Thanks @mthornhill)
* Subscription deleted webhook bugfix
* South migrations are now up to date (Thanks @Tyrdall)

0.4.0 (2015-04-05)
----------------------

* Formal Python 3.3+/Django 1.7 Support (including migrations)
* Removed Python 2.6 from Travis CI build. (Thanks @audreyr)
* Dropped Django 1.4 support. (Thanks @audreyr)
* Deprecated the ``djstripe.forms.StripeSubscriptionSignupForm``. Making this form work easily with both `dj-stripe` and `django-allauth` required too much abstraction. It will be removed in the 0.5.0 release.
* Add the ability to add invoice items for a customer (Thanks @kavdev)
* Add the ability to use a custom customer model (Thanks @kavdev)
* Added setting to disable Invoice receipt emails (Thanks Chris Halpert)
* Enable proration when customer upgrades plan, and pass proration policy and cancellation at period end for upgrades in settings. (Thanks Yasmine Charif)
* Removed the redundant context processor. (Thanks @kavdev)
* Fixed create a token call in change_card.html (Thanks @dollydagr)
* Fix ``charge.dispute.closed`` typo. (Thanks @ipmb)
* Fix contributing docs formatting. (Thanks @audreyr)
* Fix subscription cancelled_at_period_end field sync on plan upgrade (Thanks @nigma)
* Remove "account" bug in Middleware (Thanks @sromero84)
* Fix correct plan selection on subscription in subscribe_form template. (Thanks Yasmine Charif)
* Fix subscription status in account, _subscription_status, and cancel_subscription templates. (Thanks Yasmine Charif)
* Now using ``user.get_username()`` instead of ``user.username``, to support custom User models. (Thanks @shvechikov)
* Update remaining DOM Ids for Bootstrap 3. (Thanks Yasmine Charif)
* Update publish command in setup.py. (Thanks @pydanny)
* Explicitly specify tox's virtual environment names. (Thanks @audreyr)
* Manually call django.setup() to populate apps registry. (Thanks @audreyr)

0.3.5 (2014-05-01)
----------------------

* Fixed ``djstripe_init_customers`` management command so it works with custom user models.

0.3.4 (2014-05-01)
----------------------

* Clarify documentation for redirects on app_name.
* If settings.DEBUG is True, then django-debug-toolbar is exempt from redirect to subscription form.
* Use collections.OrderedDict to ensure that plans are listed in order of price.
* Add ``ordereddict`` library to support Python 2.6 users. 
* Switch from ``__unicode__`` to ``__str__`` methods on models to better support Python 3.
* Add ``python_2_unicode_compatible`` decorator to Models.
* Check for PY3 so the ``unicode(self.user)`` in models.Customer doesn't blow up in Python 3.

0.3.3 (2014-04-24)
----------------------

* Increased the extendability of the views by removing as many hard-coded URLs as possible and replacing them with ``success_url`` and other attributes/methods.
* Added single unit purchasing to the cookbook

0.3.2 (2014-01-16)
----------------------

* Made Yasmine Charif a core committer
* Take into account trial days in a subscription plan (Thanks Yasmine Charif)
* Correct invoice period end value (Thanks Yasmine Charif)
* Make plan cancellation and plan change consistently not prorating (Thanks Yasmine Charif)
* Fix circular import when ACCOUNT_SIGNUP_FORM_CLASS is defined (Thanks Dustin Farris)
* Add send e-mail receipt action in charges admin panel (Thanks Buddy Lindsay)
* Add `created` field to all ModelAdmins to help with internal auditing (Thanks Kulbir Singh)

0.3.1 (2013-11-14)
----------------------

* Cancellation fix (Thanks Yasmine Charif)
* Add setup.cfg for wheel generation (Thanks Charlie Denton)

0.3.0 (2013-11-12)
----------------------

* Fully tested against Django 1.6, 1.5, and 1.4
* Fix boolean default issue in models (from now on they are all default to `False`).
* Replace duplicated code with `djstripe.utils.user_has_active_subscription`.

0.2.9 (2013-09-06)
----------------------

* Cancellation added to views.
* Support for kwargs on charge and invoice fetching.
* def charge() now supports send_receipt flag, default to True.
* Fixed templates to work with Bootstrap 3.0.0 column design.

0.2.8 (2013-09-02)
----------------------

* Improved usage documentation.
* Corrected order of fields in StripeSubscriptionSignupForm.
* Corrected transaction history template layout.
* Updated models to take into account when settings.USE_TZ is disabled.

0.2.7 (2013-08-24)
----------------------

* Add handy rest_framework permission class.
* Fixing attribution for django-stripe-payments.
* Add new status to Invoice model.

0.2.6 (2013-08-20)
----------------------

* Changed name of division tag to djdiv. 
* Added ``safe_setting.py`` module to handle edge cases when working with custom user models.
* Added cookbook page in the documentation.

0.2.5 (2013-08-18)
----------------------

* Fixed bug in initial checkout
* You can't purchase the same plan that you currently have.

0.2.4 (2013-08-18)
----------------------

* Recursive package finding.

0.2.3 (2013-08-16)
----------------------

* Fix packaging so all submodules are loaded

0.2.2 (2013-08-15)
----------------------

* Added Registration + Subscription form

0.2.1 (2013-08-12)
----------------------

* Fixed a bug on CurrentSubscription tests
* Improved usage documentation
* Added to migration from other tools documentation

0.2.0 (2013-08-12)
----------------------

* Cancellation of plans now works.
* Upgrades and downgrades of plans now work.
* Changing of cards now works.
* Added breadcrumbs to improve navigation.
* Improved installation instructions.
* Consolidation of test instructions.
* Minor improvement to django-stripe-payments documentation
* Added coverage.py to test process.
* Added south migrations.
* Fixed the subscription_payment_required function-based view decorator.
* Removed unnecessary django-crispy-forms

0.1.7 (2013-08-08)
----------------------

* Middleware excepts all of the djstripe namespaced URLs. This way people can pay.

0.1.6 (2013-08-08)
----------------------

* Fixed a couple template paths
* Fixed the manifest so we include html, images.

0.1.5 (2013-08-08)
----------------------

* Fixed the manifest so we include html, css, js, images.

0.1.4 (2013-08-08)
----------------------

* Change PaymentRequiredMixin to SubscriptionPaymentRequiredMixin
* Add subscription_payment_required function-based view decorator
* Added SubscriptionPaymentRedirectMiddleware
* Much nicer accounts view display
* Much improved subscription form display
* Payment plans can have decimals
* Payment plans can have custom images

0.1.3 (2013-08-7)
----------------------

* Added account view
* Added Customer.get_or_create method
* Added djstripe_sync_customers management command
* sync file for all code that keeps things in sync with stripe
* Use client-side JavaScript to get history data asynchronously
* More user friendly action views

0.1.2 (2013-08-6)
----------------------

* Admin working
* Better publish statement
* Fix dependencies

0.1.1 (2013-08-6)
----------------------

* Ported internals from django-stripe-payments
* Began writing the views
* Travis-CI
* All tests passing on Python 2.7 and 3.3
* All tests passing on Django 1.4 and 1.5
* Began model cleanup
* Better form
* Provide better response from management commands

0.1.0 (2013-08-5)
----------------------

* First release on PyPI.
