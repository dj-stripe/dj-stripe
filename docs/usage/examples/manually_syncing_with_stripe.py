def example():
	import djstripe.models
	import djstripe.settings
	import stripe

	# stripe API return value is a dict-like object
	stripe_data = stripe.Product.create(
		api_key=djstripe.settings.STRIPE_SECRET_KEY,
		name="Monthly membership base fee",
		type="service",
	)

	# sync_from_stripe_data to save it to the database,
	# and recursively update any referenced objects
	djstripe_obj = djstripe.models.Product.sync_from_stripe_data(stripe_data)

	return djstripe_obj
