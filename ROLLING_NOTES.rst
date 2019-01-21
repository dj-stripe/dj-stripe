============
scratch pad
============

djstripe_init/sync_customers.py
-------------------------------

The adjustments being made to djstripe_init_customers.py and djstripe_sync_customers.py are
necessary due to a non-obvious and painful side-effect that has accrued quite the casualty count
to date, and it can boiled down to the following statement:

Upgrading your dj-stripe? Needing to pull down your Stripe customers into a new Django instance? Want to perform this basic task and not unwitting duplicate your entire customer base and get that egg all over your face? Well look no further than core.py:456, and understand that the Customer.get_or_create() calls that occur within the init and sync scripts will forcibly recreate your customer accounts on Stripe whenever there isn't a subscriber(auth_user) and djstripe_customer pair within the local instance. 

In other words, until the init/sync scripts are updated to route around this obstacle, you should avoid using Customers.objects.get_or_create() unless you're certain that you've all the customers locally stored that you're currently managing in production. 



Current Approach
----------------

One can get around this issue and sync their remote customer account information to their local
subscriber/user information, syncing up both locally and remotely without setting anything on fire, by following the steps below:

1. Create a webhook in Stripe production environment that will allow Stripe to POST back to you - make sure this is working before continuing on to the next step

	This should be something as simple as https://yoursite.com/stripe/webhook added on https://dashboard.stripe.com/account/webhooks, depending on how you configured dj-stripe in your urls.py conf


2. Run the djstripe_annotate_customers command

	If you're upgrading from an older version of dj-stripe, you won't have the djstripe_subscriber metadata attribute annotated on your Stripe customer accounts, so as this command is running, and as the customer accounts are being updated so that their metadata contains a djstripe_subscriber attribute whose value corresponds to the id/pk of their subscriber model (for most of us, this is auth_user), Stripe is POSTing back to you via your webhook, and customer accounts are being created locally as the remote customer accounts are being annotated. 

	The metadata.updated attribute within this command is simply meant to safeguard against instances where some customer accounts may already have the djstripe_subscriber metadata (for example, you botch your first pass, but only after 10 customers or so, and this will make sure you can have a clean second go. third. fourth. fml.)

	No remote duplication, no fire in production, and repopulation of live data in local test/dev environments, hooray. 

3. Now run the other djstripe commands

	3.1 djstripe_sync_plans_from_stripe 
	3.2 djstripe_init_customers
	3.3 djstripe_sync_customers commands

	They'll do what they're meant to do, but now without the tragic side-effect duplicating your entire customer base in your production Stripe environment.


Bonus:

	For those who got bit by this before February, 2018, remember how it also automatically charged their credit cards for subscription they had previously canceled? 

	Wasn't that fun? 

	And by fun, didn't you just want to die?

	Yeah...