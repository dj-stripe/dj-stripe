# Using with Docker

When developing locally with Docker, you can run the [Stripe CLI](https://stripe.com/docs/cli)
as a sidecar container that forwards Stripe webhook events to your Django app. This
is the containerised equivalent of [local webhook testing](local_webhook_testing.md).

Here is a sample `docker-compose.yaml` with a Postgres database, your Django app
(running dj-stripe), and the Stripe CLI:

```yaml
volumes:
  postgres-data: {}

services:
  db:
    image: postgres:16
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=myproject
      - POSTGRES_USER=myproject
      - POSTGRES_PASSWORD=changeme

  web:
    build:
      context: .
      dockerfile: { PATH_TO_DOCKERFILE }
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      - STRIPE_TEST_SECRET_KEY=sk_test_******
      - DATABASE_URL=postgres://myproject:changeme@db:5432/myproject

  stripe:
    image: stripe/stripe-cli:latest
    command:
      [
        "listen",
        "-H",
        "x-djstripe-webhook-secret: whsec_******",
        "--forward-to",
        "http://web:8000/stripe/webhook/{uuid}/",
      ]
    depends_on:
      - web
    environment:
      - STRIPE_API_KEY=sk_test_******
      - STRIPE_DEVICE_NAME=djstripe_docker
```

Replace the URL path (`stripe/`) with whatever prefix you mounted
[dj-stripe's URLs](../installation.md) under, and `{uuid}` with your webhook
endpoint's UUID.

_NOTE_: Pass the Stripe CLI's webhook signing secret to dj-stripe via the
`x-djstripe-webhook-secret` header, as shown above. Obtain the secret from
`stripe listen --print-secret`. See
[local webhook testing](local_webhook_testing.md) for how dj-stripe uses this
header to verify signatures.
