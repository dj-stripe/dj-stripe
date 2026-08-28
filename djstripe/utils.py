"""
Utility functions related to the djstripe app.
"""

import datetime
from contextlib import contextmanager
from contextvars import ContextVar

import stripe
from django.apps import apps
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db.models.query import QuerySet
from django.utils import timezone


def get_supported_currency_choices(api_key):
    """
    Pull a stripe account's supported currencies and returns a choices tuple of those
    supported currencies.

    :param api_key: The api key associated with the account from which to pull data.
    :type api_key: str
    """
    account = stripe.Account.retrieve(api_key=api_key)
    supported_payment_currencies = stripe.CountrySpec.retrieve(
        account["country"], api_key=api_key
    )["supported_payment_currencies"]

    return [(currency, currency.upper()) for currency in supported_payment_currencies]


def clear_expired_idempotency_keys():
    from .models import IdempotencyKey

    threshold = timezone.now() - datetime.timedelta(hours=24)
    IdempotencyKey.objects.filter(created__lt=threshold).delete()


def convert_tstamp(response) -> datetime.datetime | None:
    """
    Convert a Stripe API timestamp response (unix epoch) to a native datetime.
    """
    if response is None:
        # Allow passing None to convert_tstamp()
        return response

    # Overrides the set timezone to UTC - I think...
    tz = get_timezone_utc() if settings.USE_TZ else None

    return datetime.datetime.fromtimestamp(response, tz)


# TODO: Finish this.
CURRENCY_SIGILS = {"CAD": "$", "EUR": "€", "GBP": "£", "USD": "$"}


def get_friendly_currency_amount(amount, currency: str) -> str:
    currency = currency.upper()
    sigil = CURRENCY_SIGILS.get(currency, "")
    amount_two_decimals = f"{amount:.2f}"
    return f"{sigil}{intcomma(amount_two_decimals)} {currency}"


class QuerySetMock(QuerySet):
    """
    A mocked QuerySet class that does not handle updates.
    Used by UpcomingInvoice.invoiceitems (deprecated) and UpcomingInvoice.lineitems.
    """

    @classmethod
    def from_iterable(cls, model, iterable):
        instance = cls(model)
        instance._result_cache = list(iterable)
        instance._prefetch_done = True
        return instance

    def _clone(self):
        return self.__class__.from_iterable(self.model, self._result_cache)

    def update(self):
        return 0

    def delete(self):
        return 0


def get_id_from_stripe_data(data):
    """
    Extract stripe id from stripe field data
    """

    if isinstance(data, str):
        # data like "sub_6lsC8pt7IcFpjA"
        return data
    if data:
        # data like {"id": sub_6lsC8pt7IcFpjA", ...}
        return data.get("id")


def get_model(model_name):
    return apps.get_app_config("djstripe").get_model(model_name)


def get_queryset(pks, model_name):
    model = get_model(model_name)
    return model.objects.filter(pk__in=pks)


_owner_account_cache: ContextVar[dict | None] = ContextVar(
    "djstripe_owner_account_cache", default=None
)


@contextmanager
def owner_account_cache():
    """Memoise API key -> owner ``Account`` lookups for the duration of the block.

    Every Stripe object dj-stripe converts resolves the ``Account`` that owns the
    API key it was fetched with, which costs a couple of queries per object (and,
    the first time round, a Stripe round trip). Objects fetched with the same key
    always resolve to the same account, so a bulk operation can hold on to the
    answer for its duration:

        with owner_account_cache():
            for data in stripe_charges:
                Charge.sync_from_stripe_data(data)

    dj-stripe applies this itself around ``djstripe_sync_models`` runs and around
    webhook processing; wrap your own bulk syncs in it too.

    The cache lives in a ``ContextVar``, so concurrent threads and asyncio tasks
    each get their own and never share entries. It is created on entry and
    dropped on exit.

    The one caveat is that ``asyncio`` copies the context when a task is
    created: a task spawned *inside* the block inherits the same cache and goes
    on using it for its own lifetime, even after the block has exited. Don't
    spawn tasks that outlive the block if you need the cache to be gone when it
    ends.
    """
    token = _owner_account_cache.set({})
    try:
        yield
    finally:
        _owner_account_cache.reset(token)


def get_timezone_utc():
    """
    Returns the UTC timezone.
    """
    return datetime.UTC
