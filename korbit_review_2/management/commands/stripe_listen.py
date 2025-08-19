import shutil
import subprocess
import sys
from uuid import uuid4

from django.core.management.base import BaseCommand
from django.urls import reverse

from djstripe.enums import WebhookEndpointStatus
from djstripe.models import Account, WebhookEndpoint
from djstripe.settings import djstripe_settings

STRIPE_BINARY_NAME = "stripe"


def stripe_binary_exists():
    return bool(shutil.which(STRIPE_BINARY_NAME))


class Command(BaseCommand):
    help = "Run `stripe listen` and forward webhooks to dj-stripe"

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            metavar="host",
            nargs=1,
            default="localhost",
            type=str,
            help="The host on which Django is running (defaults to localhost).",
        )
        parser.add_argument(
            "--port",
            metavar="port",
            nargs=1,
            default=8000,
            type=int,
            help="The port on which Django is running (defaults to 8000).",
        )

    def handle(self, *args, **options):
        host = options["host"]
        port = options["port"]

        if not stripe_binary_exists():
            self.stderr.write(
                f"The Stripe CLI binary '{STRIPE_BINARY_NAME}' is not installed."
            )
            return sys.exit(1)

        # stripe listen --print-secret
        # Get the webhook signing secret
        process = subprocess.Popen(
            [STRIPE_BINARY_NAME, "listen", "--skip-update", "--print-secret"],
            stdout=subprocess.PIPE,
            text=True,
        )
        assert process.stdout

        # Read first line of output
        secret = process.stdout.readline().strip()

        if not secret.startswith("whsec_"):
            # Not a webhook secret, print it and subsequent output
            self.stderr.write(secret)
            for line in process.stdout:
                self.stderr.write(line.strip())

            self.stderr.write(
                "Error: Could not get webhook secret. If you just logged in, run this command again."
            )

            return sys.exit(1)

        base_url = f"http://{host}:{port}"

        endpoint = WebhookEndpoint.objects.filter(
            id__startswith="djstripe_whfwd_", secret=secret
        ).first()
        if not endpoint:
            endpoint_uuid = uuid4()
            path = reverse(
                "djstripe:djstripe_webhook_by_uuid", kwargs={"uuid": endpoint_uuid}
            )
            path_suffix = f"webhook/{endpoint_uuid}"
            endpoint = WebhookEndpoint.objects.create(
                id=f"djstripe_whfwd_{endpoint_uuid.hex}",
                api_version=djstripe_settings.STRIPE_API_VERSION,
                enabled_events=["*"],
                secret=secret,
                status=WebhookEndpointStatus.enabled,
                url=base_url + path.replace(path_suffix, ""),
                djstripe_owner_account=Account.objects.first(),
                djstripe_uuid=endpoint_uuid,
                livemode=False,
            )

        endpoint_url = endpoint.url + f"webhook/{endpoint.djstripe_uuid}"

        try:
            self.stdout.write(f"Forwarding Stripe webhooks to {endpoint_url}")
            subprocess.run(
                [
                    STRIPE_BINARY_NAME,
                    "listen",
                    "--skip-update",
                    "--forward-to",
                    endpoint_url,
                ]
            )
        except KeyboardInterrupt:
            pass
        finally:
            endpoint.delete()
