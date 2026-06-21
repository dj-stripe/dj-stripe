"""
Classification of Stripe ``InvalidRequestError`` exceptions.

When dj-stripe syncs an object from Stripe — whether the top-level object of a
webhook event or a related object reached through a foreign key — it retrieves
that object from the API. The object (or a nested reference) is frequently no
longer retrievable at processing time: it was deleted, detached, created and
then deleted before the webhook ran, or lives on a connected account the
platform key can't reach. In every such case the desired behaviour is the same:
treat the object as absent (leave the FK null, or skip the event) and continue,
rather than crashing the whole webhook.

This module owns the single decision "is this error an absent-object error, or a
real failure I must re-raise?". Both retrieve sites (``StripeModel.
_get_or_create_from_stripe_object`` and ``event_handlers._handle_crud_like_event``)
funnel their classification through :func:`object_is_absent` so the two cannot
drift apart.

Design: an allowlist that is *closed by default*. An error is only treated as
absent if it matches an explicit, named entry below; everything else (auth
failures, rate limits, network errors, genuine bugs) re-raises. We prefer
Stripe's structured fields (``code``, ``param``) over its human-readable
``message``; message text is only matched for quirks that don't surface as a
clean ``resource_missing`` error, and there it is paired with a structured field
(``param``) so a reworded *real* error can't trip it.

Adding the next known "object is gone" case should be a single :class:`AbsentObjectCase`
row plus a unit test feeding a captured real error.
"""

from __future__ import annotations

from dataclasses import dataclass

from stripe import InvalidRequestError


@dataclass(frozen=True)
class AbsentObjectCase:
    """
    A recognised "the referenced object is gone" error signature.

    A case matches an error only if *every* field that is set on the case
    matches the error (logical AND), and at least one field is set (so an
    empty case never matches anything).
    """

    label: str
    """Human-readable reason this error is considered benign; used in logs."""

    code: str | None = None
    """Match ``error.code`` exactly, eg. ``"resource_missing"``."""

    param: str | None = None
    """Match ``error.param`` exactly, eg. ``"payment_method"``."""

    message_contains: str | None = None
    """Substring that must appear in ``str(error)``. Last resort: only for
    quirks Stripe doesn't expose through a clean ``code``."""

    def matches(self, error: InvalidRequestError) -> bool:
        checks = []
        if self.code is not None:
            checks.append(getattr(error, "code", None) == self.code)
        if self.param is not None:
            checks.append(getattr(error, "param", None) == self.param)
        if self.message_contains is not None:
            checks.append(self.message_contains in str(error))
        return bool(checks) and all(checks)


# Closed-by-default allowlist of errors we treat as "object is absent, skip it".
# Order is irrelevant: a match against any entry is enough.
ABSENT_OBJECT_CASES: list[AbsentObjectCase] = [
    # Canonical "no such object". Stripe sets code="resource_missing" (HTTP 404)
    # and phrases the message "No such <object>: <id>". Either signal alone is
    # reliable — real API errors carry both, but synthetic/older errors may only
    # carry one — so we accept either. This single pair replaces what used to be
    # a per-object ladder of "No such charge" / "No such application fee" /
    # "No such payment_method" / "No such subscription_item" branches, and covers
    # any future object type for free.
    #   #1218 (object deleted before its created/updated webhook was processed)
    #   #2010 (object only exists on a connected account)
    #   #2025 (subscription_item removed by a schedule phase change)
    AbsentObjectCase(label="resource missing (code)", code="resource_missing"),
    AbsentObjectCase(label="resource missing (message)", message_contains="No such "),
    # Quirks that are NOT a clean resource_missing 404. Matched conjunctively
    # (param + message) so a reworded real error can't be silently swallowed.
    AbsentObjectCase(
        # A subscription_item removed during a SubscriptionSchedule phase change
        # can be reported with this wording rather than "No such ...". (#2025)
        label="stale subscription item",
        param="subscription_item",
        message_contains="Invalid subscription_item id",
    ),
    AbsentObjectCase(
        # A detached legacy source (src_…) is wrapped as a payment_method but
        # 404s on the payment_methods endpoint with this message and no
        # resource_missing code. (#1068)
        label="detached legacy source",
        param="payment_method",
        message_contains="A source must be attached to a customer",
    ),
]


def object_is_absent(error: InvalidRequestError) -> bool:
    """
    Return whether ``error`` means the referenced object is gone and should be
    treated as absent (skip it and continue) rather than re-raised.

    Closed by default: returns ``False`` for any error not matched by an
    explicit :data:`ABSENT_OBJECT_CASES` entry, so genuine failures propagate.
    """
    return any(case.matches(error) for case in ABSENT_OBJECT_CASES)
