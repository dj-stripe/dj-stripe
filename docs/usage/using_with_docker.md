# Using with Docker

A [Docker image](https://hub.docker.com/r/stripe/stripe-cli) allows you to run the Stripe CLI in a container.

Here is a sample `docker-compose.yaml` file that sets up all the services to use `Stripe CLI` in a `dockerised django container (with djstripe)`


```yaml
version: "3.9"


volumes:
    postgres-data: {}


services:

  db:
    image: postgres:12
    volumes:
      - postgres-data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=random_number
      - POSTGRES_USER=root
      - POSTGRES_PASSWORD=random_number


  web:
    build:
      context: .
      dockerfile: <PATH_TO_DOCKERFILE>
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
        # Stripe specific keys
        - STRIPE_PUBLIC_KEY=pk_test_******
        - STRIPE_SECRET_KEY=sk_test_******
        - DJSTRIPE_TEST_WEBHOOK_SECRET=whsec_******

        # Database Specific Settings
        - DJSTRIPE_TEST_DB_VENDOR=postgres
        - DJSTRIPE_TEST_DB_PORT=5432
        - DJSTRIPE_TEST_DB_USER=root
        - DJSTRIPE_TEST_DB_NAME=random_number
        - DJSTRIPE_TEST_DB_PASS=random_number
        - DJSTRIPE_TEST_DB_HOST=db

  stripe:
    image: stripe/stripe-cli:v1.7.4
    # In case Stripe CLI is used to perform local webhook testing, set x-djstripe-webhook-secret custom header to output of Stripe CLI.
    command: ["listen", "-H", "x-djstripe-webhook-secret: whsec_******", "--forward-to", "http://web:8000/djstripe/webhook/"]
    depends_on:
      - web
    environment:
      - STRIPE_API_KEY=sk_test_******
      - STRIPE_DEVICE_NAME=djstripe_docker

```

!!! note

    In case the `Stripe CLI` is used to perform local webhook testing, set `x-djstripe-webhook-secret` Custom Header in Stripe `listen` to the `Webhook Signing Secret` output of `Stripe CLI`. That is what Stripe expects and uses to create the `stripe-signature` header.
