.. :changelog:

History
=======

2.1.0 (unreleased)
------------------

- Dropped previously-deprecated ``Charge.fee_details`` property.
- Dropped previously-deprecated ``Transfer.fee_details`` property.
- Dropped previously-deprecated ``field_name`` parameter to ``sync_from_stripe_data``
- Dropped previously-deprecated alias ``StripeObject`` of ``StripeModel``
- Dropped previously-deprecated alias ``PaymentMethod`` of ``DjstripePaymentMethod``
- ``enums.PaymentMethodType`` has been deprecated, use ``enums.DjstripePaymentMethodType``

2.0.3 (2019-06-11)
------------------

This is a bugfix-only version:

- In ``_get_or_create_from_stripe_object``, wrap create ``_create_from_stripe_object`` in transaction,
  fixes ``TransactionManagementError`` on race condition in webhook processing (#877/#903).

2.0.2 (2019-06-09)
------------------

This is a bugfix-only version:

- Don't save event objects if the webhook processing fails (#832).
- Fixed IntegrityError when ``REMOTE_ADDR`` is an empty string.
- Deprecated ``field_name`` parameter to ``sync_from_stripe_data``

2.0.1 (2019-04-29)
------------------

This is a bugfix-only version:

- Fixed an error on ``invoiceitem.updated`` (#848).
- Handle test webhook properly in recent versions of Stripe API (#779).
  At some point 2018 Stripe silently changed the ID used for test events and
  ``evt_00000000000000`` is not used anymore.
- Fixed OperationalError seen in migration 0003 on postgres (#850).
- Fixed issue with migration 0003 not being unapplied correctly (#882).
- Fixup missing ``SubscriptionItem.quantity`` on Plans with ``usage_type="metered"`` (#865).
- Fixed ``Plan.create()`` (#870).

2.0.0 (2019-03-01)
------------------

- The Python stripe library minimum version is now ``2.3.0``.
- ``PaymentMethod`` has been renamed to ``DjstripePaymentMethod`` (#841).
  An alias remains but will be removed in the next version.
- Dropped support for Django < 2.0, Python < 3.4.
- Dropped previously-deprecated ``stripe_objects`` module.
- Dropped previously-deprecated ``stripe_timestamp`` field.
- Dropped previously-deprecated ``Charge.receipt_number`` field.
- Dropped previously-deprecated ``StripeSource`` alias for ``Card``
- Dropped previously-deprecated ``SubscriptionView``,
  ``CancelSubscriptionView`` and ``CancelSubscriptionForm``.
- Removed the default value from ``DJSTRIPE_SUBSCRIPTION_REDIRECT``.
- All ``stripe_id`` fields have been renamed ``id``.
- ``Charge.source_type`` has been deprecated. Use ``Charge.source.type``.
- ``Charge.source_stripe_id`` has been deprecated. Use ``Charge.source.id``.
- All deprecated Transfer fields (Stripe API < 2017-04-06), have been dropped.
  This includes ``date``, ``destination_type`` (``type``), ``failure_code``,
  ``failure_message``, ``statement_descriptor`` and ``status``.
- Fixed IntegrityError when ``REMOTE_ADDR`` is missing (#640).
- New models:
  - ``ApplicationFee``
  - ``ApplicationFeeRefund``
  - ``BalanceTransaction``
  - ``CountrySpec``
  - ``ScheduledQuery``
  - ``SubscriptionItem``
  - ``TransferReversal``
  - ``UsageRecord``
- The ``fee`` and ``fee_details`` attributes of both the ``Charge`` and
  ``Transfer`` objects are no longer stored in the database. Instead, they
  access their respective new ``balance_transaction`` foreign key.
  Note that ``fee_details`` has been deprecated on both models.
- The ``fraudulent`` attribute on ``Charge`` is now a property that checks
  the ``fraud_details`` field.
- Object key validity is now always enforced (#503).
- ``Customer.sources`` no longer refers to a Card queryset, but to a Source
  queryset. In order to correctly transition, you should change all your
  references to ``customer.sources`` to ``customer.legacy_cards`` instead.
  The ``legacy_cards`` attribute already exists in 1.2.0.
- ``Customer.sources_v3`` is now named ``Customer.sources``.
- A new property ``Customer.payment_methods`` is now available, which allows
  you to iterate over all of a customer's payment methods (sources then cards).
- ``Card.customer`` is now nullable and cards are no longer deleted when their
  corresponding customer is deleted (#654).
- Webhook signature verification is now available and is preferred. Set the
  ``DJSTRIPE_WEBHOOK_SECRET`` setting to your secret to start using it.
- ``StripeObject`` has been renamed ``StripeModel``. An alias remains but will
  be removed in the next version.
- The metadata key used in the ``Customer`` object can now be configured by
  changing the ``DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY`` setting. Setting this to
  None or an empty string now also disables the behaviour altogether.
- Text-type fields in dj-stripe will no longer ever be None. Instead, any falsy
  text field will return an empty string.
- Switched test runner to pytest-django
- ``StripeModel.sync_from_stripe_data()`` will now automatically retrieve related objects
  and populate foreign keys (#681)
- Added ``Coupon.name``
- Added ``Transfer.balance_transaction``
- Exceptions in webhooks are now re-raised as well as saved in the database (#833)


1.2.4 (2019-02-27)
------------------

This is a bugfix-only version:

- Allow billing_cycle_anchor argument when creating a subscription (#814)
- Fixup plan amount null with tier plans (#781)
- Update Cancel subscription view tests to match backport in f64af57
- Implement Invoice._manipulate_stripe_object_hook for compatability with API 2018-11-08 (#771)
- Fix product webhook for type="good" (#724)
- Add trial_from_plan, trial_period_days args to Customer.subscribe() (#709)


1.2.3 (2018-10-13)
------------------

This is a bugfix-only version:

- Updated Subscription.cancel() for compatibility with Stripe 2018-08-23 (#723)


1.2.2 (2018-08-11)
------------------

This is a bugfix-only version:

- Fixed an error with request.urlconf in some setups (#562)
- Always save text-type fields as empty strings in db instead of null (#713)
- Fix support for DJSTRIPE_SUBSCRIBER_MODEL_MIGRATION_DEPENDENCY (#707)
- Fix reactivate() with Stripe API 2018-02-28 and above


1.2.1 (2018-07-18)
------------------

This is a bugfix-only version:

- Fixed various Python 2.7 compatibility issues
- Fixed issues with max_length of receipt_number
- Fixed various fields incorrectly marked as required
- Handle product webhook calls
- Fix compatibility with stripe-python 2.0.0


1.2.0 (2018-06-11)
------------------

The dj-stripe 1.2.0 release resets all migrations.

**Do not upgrade to 1.2.0 directly from 1.0.1 or below.
You must upgrade to 1.1.0 first.**

Please read the 1.1.0 release notes below for more information.

1.1.0 (2018-06-11)
------------------

In dj-stripe 1.1.0, we made a *lot* of changes to models in order to
bring the dj-stripe model state much closer to the upstream API objects.
If you are a current user of dj-stripe, you will most likely have to
make changes in order to upgrade. Please read the full changelog below.
If you are having trouble upgrading, you may ask for help `by filing an
issue on GitHub`_.

Migration reset
^^^^^^^^^^^^^^^

The next version of dj-stripe, **1.2.0**, will reset all the migrations
to ``0001_initial``. Migrations are currently in an unmaintainable
state.

**What this means is you will not be able to upgrade directly to
dj-stripe 1.2.0. You must go through 1.1.0 first, run
``manage.py migrate djstripe``, then upgrade to 1.2.0.**

Python 2.7 end-of-life
^^^^^^^^^^^^^^^^^^^^^^

dj-stripe 1.1.0 drops support for Django 1.10 and adds support for
Django 2.0. Django 1.11+ and Python 2.7+ or 3.4+ are required.

Support for Python versions older than 3.5, and Django versions older
than 2.0, will be dropped in dj-stripe 2.0.0.

Backwards-incompatible changes and deprecations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Removal of polymorphic models
"""""""""""""""""""""""""""""

The model architecture of dj-stripe has been simplified. Polymorphic
models have been dropped and the old base StripeCustomer, StripeCharge,
StripeInvoice, etc models have all been merged into the top-level
Customer, Charge, Invoice, etc models.

Importing those legacy models from ``djstripe.stripe_objects`` will
yield the new ones. This is deprecated and support for this will be
dropped in dj-stripe 2.0.0.

Full support for Stripe Sources (Support for v3 stripe.js)
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Stripe sources (``src_XXXX``) are objects that can arbitrarily reference
any of the payment method types that Stripe supports. However, the
legacy ``Card`` object (with object IDs like ``card_XXXX`` or
``cc_XXXX``) is not a Source object, and cannot be turned into a Source
object at this time.

In order to support both Card and Source objects in ForeignKeys,
a new model ``PaymentMethod`` has been devised (renamed to ``DjstripePaymentMethod``
in 2.0). That model can resolve into a Card, a Source, or a BankAccount object.

-  **The ``default_source`` attribute on ``Customer`` now refers to a
   ``PaymentMethod`` object**. You will need to call ``.resolve()`` on
   it to get the Card or Source in question.
-  References to ``Customer.sources`` expecting a queryset of Card
   objects should be updated to ``Customer.legacy_cards``.
-  The legacy ``StripeSource`` name refers to the ``Card`` model. This
   will be removed in dj-stripe 2.0.0. Update your references to either
   ``Card`` or ``Source``.
-  ``enums.SourceType`` has been renamed to ``enums.LegacySourceType``.
   ``enums.SourceType`` now refers to the actual Stripe Source types
   enum.

Core fields renamed
"""""""""""""""""""

-  The numeric ``id`` field has been renamed to ``djstripe_id``. This
   avoids a clash with the upstream stripe id. Accessing ``.id`` is
   deprecated and \**will reference the upstream ``stripe_id`` in
   dj-stripe 2.0.0

.. _by filing an issue on GitHub: https://github.com/dj-stripe/dj-stripe/issues


1.0.0 (2017-08-12)
------------------

It's finally here! We've made significant changes to the codebase and are
now compliant with stripe API version **2017-06-05**.

I want to give a huge thanks to all of our contributors for their help
in making this happen, especially Bill Huneke (@wahuneke) for his
impressive design work and @jleclanche for really pushing this release along.

I also want to welcome onboard two more maintainers, @jleclanche and @lskillen.
They've stepped up and have graciously dedicated their resources to making dj-stripe
such an amazing package.

Almost all methods now mimic the parameters of those same methods in the
stripe API. Note that some methods do not have some parameters
implemented. This is intentional. That being said, expect all method
signatures to be different than those in previous versions of dj-stripe.

Finally, please note that there is still a bit of work ahead of us. Not everything
in the Stripe API is currently supported by dj-stripe -- we're working on it.
That said, v1.0.0 has been thoroughly tested and is verified stable in
production applications.

A few things to get excited for
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

-  Multiple subscription support (finally)
-  Multiple sources support (currently limited to Cards)
-  Idempotency support (See #455, #460 for discussion -- big thanks to
   @jleclanche)
-  Full model documentation
-  Objects that come through webhooks are now tied to the API version
   set in dj-stripe. No more errors if dj-stripe falls behind the newest
   stripe API version.
-  Any create/update action on an object automatically syncs the object.
-  Concurrent LIVE and TEST mode support (Thanks to @jleclanche). Note
   that you'll run into issues if ``livemode`` isn't set on your
   existing customer objects.
-  All choices are now enum-based (Thanks @jleclanche, See #520). Access
   them from the new ``djstripe.enums`` module. The ability to check
   against model property based choices will be deprecated in 1.1
-  Support for the Coupon model, and coupons on Customer objects.
-  Support for the `Payout/Transfer
   split <https://stripe.com/docs/transfer-payout-split>`__ from api
   version ``2017-04-06``.

What still needs to be done (in v1.1.0)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

-  **Documentation**. Our original documentation was not very helpful,
   but it covered the important bits. It will be very out of date after
   this update and will need to be rewritten. If you feel like helping,
   we could use all the help we can get to get this pushed out asap.
-  **Master sync re-write**. This sounds scary, but really isn't. The
   current management methods run sync methods on Customer that aren't
   very helpful and are due for removal. My plan is to write something
   that first updates local data (via ``api_retrieve`` and
   ``sync_from_stripe_data``) and then pulls all objects from Stripe and
   populates the local database with any records that don't already
   exist there.

   You might be wondering, "Why are they releasing this if there are only
   a few things left?" Well, that thinking turned this into a two year
   release... Trust me, this is a good thing.

Significant changes (mostly backwards-incompatible)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

-  **Idempotency**. #460 introduces idempotency keys and implements
   idempotency for ``Customer.get_or_create()``. Idempotency will be
   enabled for all calls that need it.
-  **Improved Admin Interface**. This is almost complete. See #451 and
   #452.
-  **Drop non-trivial endpoint views**. We're dropping everything except
   the webhook endpoint and the subscription cancel endpoint. See #428.
-  **Drop support for sending receipts**. Stripe now handles this for
   you. See #478.
-  **Drop support for plans as settings**, including custom plan
   hierarchy (if you want this, write something custom) and the dynamic
   trial callback. We've decided to gut having plans as settings.
   Stripe should be your source of truth; create your plans
   there and sync them down manually. If you need to create plans
   locally for testing, etc., simply use the ORM to create Plan models.
   The sync rewrite will make this drop less annoying.
-  **Orphan Customer Sync**. We will now sync Customer objects from
   Stripe even if they aren't linked to local subscriber objects. You
   can link up subscribers to those Customers manually.
-  **Concurrent Live and Test Mode**. dj-stripe now supports test-mode
   and live-mode Customer objects concurrently. As a result, the
   User.customer One-to-One reverse-relationship is now the
   User.djstripe_customers RelatedManager. (Thanks @jleclanche) #440. You'll
   run into some dj-stripe check issues if you don't update your KEY settings
   accordingly. Check our GitHub issue tracker for help on this.

SETTINGS
^^^^^^^^

-  The ``PLAN_CHOICES``, ``PLAN_LIST``, and ``PAYMENT_PLANS`` objects
   are removed. Use Plan.objects.all() instead.
-  The ``plan_from_stripe_id`` function is removed. Use
   Plan.objects.get(stripe\_id=)

SYNCING
^^^^^^^

-  sync\_plans no longer takes an api\_key
-  sync methods no longer take a ``cu`` parameter
-  All sync methods are now private. We're in the process of building a
   better syncing mechanism.

UTILITIES
^^^^^^^^^

-  dj-stripe decorators now take a plan argument. If you're passing in a
   custom test function to ``subscriber_passes_pay_test``, be sure to
   account for this new argument.

MIXINS
^^^^^^

-  The context provided by dj-stripe's mixins has changed.
   ``PaymentsContextMixin`` now provides ``STRIPE_PUBLIC_KEY`` and
   ``plans`` (changed to ``Plan.objects.all()``). ``SubscriptionMixin``
   now provides ``customer`` and ``is_plans_plural``.
-  We've removed the SubscriptionPaymentRequiredMixin. Use
   ``@method_decorator("dispatch",``\ `subscription\_payment\_required <https://github.com/kavdev/dj-stripe/blob/1.0.0/djstripe/decorators.py#L39>`__\ ``)``
   instead.

MIDDLEWARE
^^^^^^^^^^

-  dj-stripe middleware doesn't support multiple subscriptions.

SIGNALS
^^^^^^^

-  Local custom signals are deprecated in favor of Stripe webhooks:
-  ``cancelled`` -> WEBHOOK\_SIGNALS["customer.subscription.deleted"]
-  ``card_changed`` -> WEBHOOK\_SIGNALS["customer.source.updated"]
-  ``subscription_made`` ->
   WEBHOOK\_SIGNALS["customer.subscription.created"]

WEBHOOK EVENTS
^^^^^^^^^^^^^^

-  The Event Handlers designed by @wahuneke are the new way to handle
   events that come through webhooks. Definitely take a look at
   ``event_handlers.py`` and ``webhooks.py``.

EXCEPTIONS
^^^^^^^^^^

-  ``SubscriptionUpdateFailure`` and ``SubscriptionCancellationFailure``
   exceptions are removed. There should no longer be a case where they
   would have been useful. Catch native stripe errors in their place
   instead.

MODELS
^^^^^^

   .. rubric:: CHARGE
      :name: charge

-  ``Charge.charge_created`` -> ``Charge.stripe_timestamp``
-  ``Charge.card_last_4`` and ``Charge.card_kind`` are removed. Use
   ``Charge.source.last4`` and ``Charge.source.brand`` (if the source is
   a Card)
-  ``Charge.invoice`` is no longer a foreign key to the Invoice model.
   ``Invoice`` now has a OneToOne relationship with ``Charge``.
   (``Charge.invoice`` will still work, but will no longer be
   represented in the database).

   .. rubric:: CUSTOMER
      :name: customer

-  dj-stripe now supports test mode and live mode Customer objects
   concurrently (See #440). As a result, the
   ``<subscriber_model>.customer`` OneToOne reverse relationship is no
   longer a thing. You should now instead add a ``customer`` property to
   your subscriber model that checks whether you're in live or test mode
   (see djstripe.settings.STRIPE\_LIVE\_MODE as an example) and grabs
   the customer from ``<subscriber_model>.djstripe_customers`` with a
   simple ``livemode=`` filter.
-  Customer no longer has a ``current_subscription`` property. We've
   added a ``subscription`` property that should suit your needs.
-  With the advent of multiple subscriptions, the behavior of
   ``Customer.subscribe()`` has changed. Before, ``calling subscribe()``
   when a customer was already subscribed to a plan would switch the
   customer to the new plan with an option to prorate. Now calling
   ``subscribe()`` simply subscribes that customer to a new plan in
   addition to it's current subsription. Use ``Subscription.update()``
   to change a subscription's plan instead.
-  ``Customer.cancel_subscription()`` is removed. Use
   ``Subscription.cancel()`` instead.
-  The ``Customer.update_plan_quantity()`` method is removed. Use
   ``Subscription.update()`` instead.
-  ``CustomerManager`` is now ``SubscriptionManager`` and works on the
   ``Subscription`` model instead of the ``Customer`` model.
-  ``Customer.has_valid_card()`` is now ``Customer.has_valid_source()``.
-  ``Customer.update_card()`` now takes an id. If the id is not
   supplied, the default source is updated.
-  ``Customer.stripe_customer`` property is removed. Use
   ``Customer.api_retrieve()`` instead.
-  The ``at_period_end`` parameter of ``Customer.cancel_subscription()``
   now actually follows the
   `DJSTRIPE\_PRORATION\_POLICY <http://dj-stripe.readthedocs.org/en/latest/settings.html#djstripe-proration-policy-false>`__
   setting.
-  ``Customer.card_fingerprint``, ``Customer.card_last_4``,
   ``Customer.card_kind``, ``Customer.card_exp_month``,
   ``Customer.card_exp_year`` are all removed. Check
   ``Customer.default_source`` (if it's a Card) or one of the sources in
   ``Customer.sources`` (again, if it's a Card) instead.
-  The ``invoice_id`` parameter of ``Customer.add_invoice_item`` is now
   named ``invoice`` and can be either an Invoice object or the
   stripe\_id of an Invoice.

   .. rubric:: EVENT
      :name: event

-  ``Event.kind`` -> ``Event.type``
-  Removed ``Event.validated_message``. Just check if the event is valid
   - no need to double check (we do that for you)

   .. rubric:: TRANSFER
      :name: transfer

-  Removed ``Transfer.update_status()``
-  Removed ``Transfer.event``
-  ``TransferChargeFee`` is removed. It hasn't been used in a while due
   to a broken API version. Use ``Transfer.fee_details`` instead.
-  Any fields that were in ``Transfer.summary`` no longer exist and are
   therefore deprecated (unused but not removed from the database).
   Because of this, ``TransferManager`` now only aggregates
   ``total_sum``

   .. rubric:: INVOICE
      :name: invoice

-  ``Invoice.attempts`` -> ``Invoice.attempt_count``
-  InvoiceItems are no longer created when Invoices are synced. You must
   now sync InvoiceItems directly.

   .. rubric:: INVOICEITEM
      :name: invoiceitem

-  Removed ``InvoiceItem.line_type``

   .. rubric:: PLAN
      :name: plan

-  Plan no longer has a ``stripe_plan`` property.
   Use ``api_retrieve()`` instead.
-  ``Plan.currency`` no longer uses choices. Use the
   ``get_supported_currency_choices()`` utility and create your own
   custom choices list instead.
-  Plan interval choices are now in ``Plan.INTERVAL_TYPE_CHOICES``

   .. rubric:: SUBSCRIPTION
      :name: subscription

-  ``Subscription.is_period_current()`` now checks for a current trial
   end if the current period has ended. This change means subscriptions
   extended with ``Subscription.extend()`` will now be seen as valid.

MIGRATIONS
^^^^^^^^^^

We'll sync your current records with Stripe in a migration. It will take
a while, but it's the only way we can ensure data integrity. There were
some fields for which we needed to temporarily add placeholder defaults,
so just make sure you have a customer with ID 1 and a plan with ID 1 and
you shouldn't run into any issues (create dummy values for these if need
be and delete them after the migration).

BIG HUGE NOTE - DON'T OVERLOOK THIS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. warning::
	Subscription and InvoiceItem migration is not possible because old records don't have Stripe IDs (so we can't sync them). Our approach is to delete all local subscription and invoiceitem objects and re-sync them from Stripe.

	We 100% recommend you create a backup of your database before performing this upgrade.


Other changes
^^^^^^^^^^^^^

* Postgres users now have access to the ``DJSTRIPE_USE_NATIVE_JSONFIELD`` setting. (Thanks @jleclanche) #517, #523
* Charge receipts now take ``DJSTRIPE_SEND_INVOICE_RECEIPT_EMAILS`` into account (Thanks @r0fls)
* Clarified/modified installation documentation (Thanks @pydanny)
* Corrected and revised ANONYMOUS_USER_ERROR_MSG (Thanks @pydanny)
* Added fnmatching to ``SubscriptionPaymentMiddleware`` (Thanks @pydanny)
* ``SubscriptionPaymentMiddleware.process_request()`` functionality broken up into multiple methods, making local customizations easier (Thanks @pydanny)
* Fully qualified events are now supported by event handlers as strings e.g. 'customer.subscription.deleted' (Thanks @lskillen) #316
* runtests now accepts positional arguments for declaring which tests to run (Thanks @lskillen) #317
* It is now possible to reprocess events in both code and the admin interface (Thanks @lskillen) #318
* The confirm page now checks that a valid card exists. (Thanks @scream4ik) #325
* Added support for viewing upcoming invoices (Thanks @lskillen) #320
* Event handler improvements and bugfixes (Thanks @lskillen) #321
* API list() method bugfixes (Thanks @lskillen) #322
* Added support for a custom webhook event handler (Thanks @lskillen) #323
* Django REST Framework contrib package improvements (Thanks @aleccool213) #334
* Added ``tax_percent`` to CreateSubscriptionSerializer (Thanks @aleccool213) #349
* Fixed incorrectly assigned ``application_fee`` in Charge calls (Thanks @kronok) #382
* Fixed bug caused by API change (Thanks @jessamynsmith) #353
* Added inline documentation to pretty much everything and enforced docsytle via flake8 (Thanks @aleccool213)
* Fixed outdated method call in template (Thanks @kandoio) #391
* Customer is correctly purged when subscriber is deleted, regardless of how the deletion happened (Thanks @lskillen) #396
* Test webhooks are now properly captured and logged. No more bounced requests to Stripe! (Thanks @jameshiew) #408
* CancelSubscriptionView redirect is now more flexible (Thanks @jleclanche) #418
* Customer.sync_cards() (Thanks @jleclanche) #438
* Many stability fixes, bugfixes, and code cleanup (Thanks @jleclanche)
* Support syncing cancelled subscriptions (Thanks @jleclanche) #443
* Improved admin interface (Thanks @jleclanche with @jameshiew) #451
* Support concurrent TEST + LIVE API keys (Fix webhook event processing for both modes) (Thanks @jleclanche) #461
* Added Stripe Dashboard link to admin change panel (Thanks @jleclanche) #465
* Implemented ``Plan.amount_in_cents`` (Thanks @jleclanche) #466
* Implemented ``Subscription.reactivate()`` (Thanks @jleclanche) #470
* Added ``Plan.human_readable_price`` (Thanks @jleclanche) #498
* (Re)attach the Subscriber when we find it's id attached to a customer on Customer sync (Thanks @jleclanche) #500
* Made API version configurable (with dj-stripe recommended default) (Thanks @lskillen) #504


0.8.0 (2015-12-30)
---------------------
* better plan ordering documentation (Thanks @cjrh)
* added a confirmation page when choosing a subscription (Thanks @chrissmejia, @areski)
* setup.py reverse dependency fix (#258/#268) (Thanks @ticosax)
* Dropped official support for Django 1.7 (no code changes were made)
* Python 3.5 support, Django 1.9.1 support
* Migration improvements (Thanks @michi88)
* Fixed "Invoice matching query does not exist" bug (#263) (Thanks @mthornhill)
* Fixed duplicate content in account view (Thanks @areski)

0.7.0 (2015-09-22)
---------------------
* dj-stripe now responds to the invoice.created event (Thanks @wahuneke)
* dj-stripe now cancels subscriptions and purges customers during sync if they were deleted from the stripe dashboard (Thanks @unformatt)
* dj-stripe now checks for an active stripe subscription in the ``update_plan_quantity`` call (Thanks @ctrengove)
* Event processing is now handled by "event handlers" - functions outside of models that respond to various event types and subtypes. Documentation on how to tie into the event handler system coming soon. (Thanks @wahuneke)
* Experimental Python 3.5 support
* Support for Django 1.6 and lower is now officially gone.
* Much, much more!

0.6.0 (2015-07-12)
---------------------

* Support for Django 1.6 and lower is now deprecated.
* Improved test harness now tests coverage and pep8
* SubscribeFormView and ChangePlanView no longer populate self.error with form errors
* InvoiceItems.plan can now be null (as it is with individual charges), resolving #140 (Thanks @awechsler and @MichelleGlauser for help troubleshooting)
* Email templates are now packaged during distribution.
* sync_plans now takes an optional api_key
* 100% test coverage
* Stripe ID is now returned as part of each model's str method (Thanks @areski)
* Customer model now stores card expiration month and year (Thanks @jpadilla)
* Ability to extend subscriptions (Thanks @TigerDX)
* Support for plan heirarchies (Thanks @chrissmejia)
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
* Deprecated the ``djstripe.forms.StripeSubscriptionSignupForm``. Making this form work easily with both ``dj-stripe`` and ``django-allauth`` required too much abstraction. It will be removed in the 0.5.0 release.
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
* Add ``created`` field to all ModelAdmins to help with internal auditing (Thanks Kulbir Singh)

0.3.1 (2013-11-14)
----------------------

* Cancellation fix (Thanks Yasmine Charif)
* Add setup.cfg for wheel generation (Thanks Charlie Denton)

0.3.0 (2013-11-12)
----------------------

* Fully tested against Django 1.6, 1.5, and 1.4
* Fix boolean default issue in models (from now on they are all default to ``False``).
* Replace duplicated code with ``djstripe.utils.user_has_active_subscription``.

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
