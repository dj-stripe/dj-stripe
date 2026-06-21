"""
Tests for djstripe._stripe_errors.object_is_absent — the single classifier that
decides whether a Stripe InvalidRequestError means "the object is gone, skip it"
versus a real error that must propagate.
"""

from stripe import InvalidRequestError

from djstripe._stripe_errors import object_is_absent


def _err(message, *, code=None, param=None, http_status=None):
    return InvalidRequestError(
        message=message, param=param, code=code, http_status=http_status
    )


class TestObjectIsAbsent:
    def test_resource_missing_code(self):
        # The canonical signal, regardless of object type or wording.
        assert object_is_absent(
            _err("anything", code="resource_missing", http_status=404)
        )

    def test_no_such_message_for_every_object_type(self):
        # The "No such <object>" wording is matched even when no code is set,
        # which covers the historical per-type branches in one row.
        for message in (
            "No such charge: 'py_1'",
            "No such application fee: 'fee_1'",
            "No such payment_method: 'card_1'",
            "No such PaymentMethod: 'card_1'",
            "No such subscription_item: 'si_1'",
            "No such price: 'price_1'",
        ):
            assert object_is_absent(_err(message)), message

    def test_detached_legacy_source_quirk(self):
        # Not a resource_missing error: matched by param + message together.
        assert object_is_absent(
            _err(
                "A source must be attached to a customer to be used as a "
                "`payment_method`.",
                param="payment_method",
            )
        )

    def test_invalid_subscription_item_quirk(self):
        assert object_is_absent(
            _err("Invalid subscription_item id: si_gone", param="subscription_item")
        )

    def test_real_errors_propagate(self):
        # None of these mean "object absent"; the classifier must return False so
        # they re-raise instead of silently corrupting the local mirror.
        assert not object_is_absent(_err("Invalid API Key provided", code="api_key"))
        assert not object_is_absent(
            _err("Too many requests", code="rate_limit", http_status=429)
        )
        assert not object_is_absent(_err("a similar object exists in test mode"))
        assert not object_is_absent(
            _err("Your card was declined", code="card_declined")
        )

    def test_quirk_message_without_matching_param_does_not_match(self):
        # The conjunctive guard: the source-attached message on an unexpected
        # param must NOT be swallowed, so a reworded real error can't sneak in.
        assert not object_is_absent(
            _err(
                "A source must be attached to a customer to be used as a "
                "`payment_method`.",
                param="something_else",
            )
        )
