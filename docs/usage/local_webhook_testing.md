# Local Webhook Testing

To perform local webhook testing using the `Stripe CLI`, please do the following:

1. Set `-H` to `x-djstripe-webhook-secret` Custom Header in Stripe `listen` to the `Webhook Signing Secret` output of `Stripe CLI`. That is what Stripe expects and uses to create the `stripe-signature` header. Without that `webhook` validation will fail and you would get a `400` status code.

2. Set `--forward-to` to the `URL` you want stripe to forward the request to. New Style `UUID` urls are also supported from `v2.7` onwards.

3. Start the local `Stripe` server like so:

  ```bash

  stripe listen -H "x-djstripe-webhook-secret: <STRIPE_CLI_WEBHOOK_SIGNING_SECRET_OUTPUT>" --forward-to <URL>

  ```

4. `Stripe` events can now be triggered like so:

```bash

stripe trigger customer.created

```

**Note:**

    In case the `Stripe CLI` is used to perform local webhook testing, set `-H` to `x-djstripe-webhook-secret` Custom Header in Stripe `listen` to the `Webhook Signing Secret` output of `Stripe CLI`. That is what Stripe expects and uses to create the `stripe-signature` header.
