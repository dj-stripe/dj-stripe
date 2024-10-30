"""
dj-stripe Exceptions.
"""


class MultipleSubscriptionException(Exception):
    """Raised when a Customer has multiple Subscriptions and only one is expected."""

    pass


class StripeObjectManipulationException(Exception):
    """
    Raised when an attempt to manipulate a non-standalone stripe object is made
     not through its parent object.
    """

    pass


class InvalidStripeAPIKey(ValueError):
    """
    Raised when a clearly-invalid Stripe API key is used.
    """

    pass


class ImpossibleAPIRequest(Exception):
    """
    Raised when dj-stripe attempts to make an impossible API request
    """

    pass
