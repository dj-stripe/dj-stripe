"""Helpers that patch the dozen ``stripe.<X>.retrieve`` calls
``sync_from_stripe_data`` walks to follow a fixture's foreign-key chain.

Most model tests need to sync a fixture whose FK references chain out to a
half-dozen other Stripe objects. Each test would otherwise stack 8-13
``@patch("stripe.X.retrieve", return_value=deepcopy(FAKE_X))`` decorators and
never actually inspect the resulting mocks. Use :func:`mock_stripe_world`
(context manager) or :func:`monkeypatch_stripe_world` (pytest-fixture variant)
instead.
"""

import contextlib
from copy import deepcopy
from unittest.mock import patch

import stripe

from . import (
    FAKE_BALANCE_TRANSACTION,
    FAKE_CARD_AS_PAYMENT_METHOD,
    FAKE_CHARGE,
    FAKE_CUSTOMER,
    FAKE_INVOICE,
    FAKE_INVOICEITEM,
    FAKE_PAYMENT_INTENT_I,
    FAKE_PLAN,
    FAKE_PLATFORM_ACCOUNT,
    FAKE_PRICE,
    FAKE_PRODUCT,
    FAKE_SUBSCRIPTION,
    FAKE_SUBSCRIPTION_ITEM,
    FAKE_TAX_RATE_EXAMPLE_1_VAT,
)


def _stripe_world_registry(**overrides):
    """Default registry of stripe class -> FAKE_X used by sync_from_stripe_data."""
    registry = {
        "Account": FAKE_PLATFORM_ACCOUNT,
        "BalanceTransaction": FAKE_BALANCE_TRANSACTION,
        "Charge": FAKE_CHARGE,
        "Customer": FAKE_CUSTOMER,
        "Invoice": FAKE_INVOICE,
        "InvoiceItem": FAKE_INVOICEITEM,
        "PaymentIntent": FAKE_PAYMENT_INTENT_I,
        "PaymentMethod": FAKE_CARD_AS_PAYMENT_METHOD,
        "Plan": FAKE_PLAN,
        "Price": FAKE_PRICE,
        "Product": FAKE_PRODUCT,
        "Subscription": FAKE_SUBSCRIPTION,
        "SubscriptionItem": FAKE_SUBSCRIPTION_ITEM,
        "TaxRate": FAKE_TAX_RATE_EXAMPLE_1_VAT,
    }
    registry.update(overrides)
    return registry


def monkeypatch_stripe_world(monkeypatch, **overrides):
    """Apply the stripe.<X>.retrieve registry via pytest's ``monkeypatch`` fixture.

    Use this in tests that already take ``monkeypatch`` as a fixture argument;
    use :func:`mock_stripe_world` (a context manager) elsewhere.
    """
    for class_name, fake in _stripe_world_registry(**overrides).items():
        # Bind ``fake`` per iteration to avoid the late-binding closure trap.
        monkeypatch.setattr(
            getattr(stripe, class_name),
            "retrieve",
            lambda *a, _f=fake, **kw: deepcopy(_f),
        )


@contextlib.contextmanager
def mock_stripe_world(**overrides):
    """Patch the stripe.<X>.retrieve calls that ``sync_from_stripe_data`` walks.

    Yields a dict of {class_name: MagicMock} so callers can inspect or further
    configure the patched mocks.

    ``overrides`` lets a test substitute a different fixture for one of the
    classes (e.g. ``Invoice=FAKE_INVOICE_II``) without touching the rest of
    the registry.
    """
    registry = _stripe_world_registry(**overrides)

    with contextlib.ExitStack() as stack:
        mocks = {}
        for class_name, fake in registry.items():
            mocks[class_name] = stack.enter_context(
                patch(
                    f"stripe.{class_name}.retrieve",
                    return_value=deepcopy(fake),
                    autospec=True,
                )
            )
        yield mocks
