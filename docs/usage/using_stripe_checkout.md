# Create a Stripe Checkout Session


For your convenience, dj-stripe has provided an example implementation on how to use `Checkouts` [here](https://github.com/dj-stripe/dj-stripe/blob/master/tests/apps/example/views.py#L24)


Please note that in order for dj-stripe to create a link between your `customers` and your `subscribers`, you need to add the
```{eval-rst}
:py:attr:`djstripe.settings.DjstripeSettings.SUBSCRIBER_CUSTOMER_KEY` (``DJSTRIPE_SUBSCRIBER_CUSTOMER_KEY``)
``` 
key to the `metadata` parameter of `Checkout`. This has also been demonstrated in the aforementioned [example](https://github.com/dj-stripe/dj-stripe/blob/master/tests/apps/example/views.py#L65)
