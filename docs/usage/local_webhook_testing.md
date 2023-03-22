# Local Webhook Testing

The [Stripe CLI][cli] allows receiving webhooks events from Stripe on your local machine via a direct connection to Stripe's API.

Set the `--forward-to` flag to the URL of a local webhook endpoint
you created via the Django admin or the Stripe Dashboard.
New Style `UUID` urls are also supported from `v2.7` onwards.
For example:

```sh
stripe listen --forward-to http://localhost:8000/stripe/webhook/<UUID>
```

The [signatures of events sent by Stripe to the webhooks are verified][signatures]
to prevent third-parties from interacting with the endpoints.
Events will be signed with a webhook secret different from existing endpoints
(because Stripe CLI doesn't require a webhook endpoint to be set up).
You can obtain this secret by looking at the output of `stripe listen`
or by running `stripe listen --print-secret`.

In order to let dj-stripe know about the secret key to verify the signature,
it can be passed as an HTTP header;
dj-stripe looks for a header called `X-Djstripe-Webhook-Secret`:

```sh
stripe listen \
  --forward-to http://localhost:8000/djstripe/webhook/<UUID> \
  -H "x-djstripe-webhook-secret: $(stripe listen --print-secret)"
```

From now on, whenever you make changes on the Stripe Dashboard,
the webhook endpoint you specified with `--forward-to` will called
with the respective changes.

!!! hint
    If the webhook secret is not passed to dj-stripe,
    signature validation will fail with an HTTP status code 400
    and the message "Failed to verify header".

Stripe events can now be triggered like so:

```sh
stripe trigger customer.created
```

[cli]: https://stripe.com/docs/cli
[signatures]: https://stripe.com/docs/webhooks/signatures
