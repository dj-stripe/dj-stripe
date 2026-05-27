"""
Compatibility shim for stripe-python >= 15.

In stripe 15.0.0, ``StripeObject`` stopped inheriting from ``dict`` and the
mapping-style methods it provided (``get``, ``items``, ``keys``, ``values``,
``pop``, ``setdefault``) were dropped. dj-stripe relies on those methods
across its sync code paths, so we restore them here.

This is a no-op against stripe <15: the inherited ``dict`` methods short-circuit
the ``hasattr`` checks below.
"""

from stripe import StripeObject

_MISSING = object()


def _get(self, key, default=None):
    return self[key] if key in self else default


def _items(self):
    return self._data.items()


def _keys(self):
    return self._data.keys()


def _values(self):
    return self._data.values()


def _pop(self, key, default=_MISSING):
    if key in self:
        value = self[key]
        del self[key]
        return value
    if default is _MISSING:
        raise KeyError(key)
    return default


def _setdefault(self, key, default=None):
    if key in self:
        return self[key]
    self[key] = default
    return default


for _name, _fn in (
    ("get", _get),
    ("items", _items),
    ("keys", _keys),
    ("values", _values),
    ("pop", _pop),
    ("setdefault", _setdefault),
):
    if not hasattr(StripeObject, _name):
        setattr(StripeObject, _name, _fn)

"""
Compatibility shim for stripe-python >= 15.

In stripe 15.0.0, ``StripeObject`` stopped inheriting from ``dict`` and the
mapping-style methods it provided (``get``, ``items``, ``keys``, ``values``,
``pop``, ``setdefault``) were dropped. dj-stripe relies on those methods
across its sync code paths, so we restore them here.

This is a no-op against stripe <15: the inherited ``dict`` methods short-circuit
the ``hasattr`` checks below.

"""

from stripe import StripeObject

_MISSING = object()


def _get(self, key, default=None):
    return self[key] if key in self else default


def _items(self):
    return self._data.items()


def _keys(self):
    return self._data.keys()


def _values(self):
    return self._data.values()


def _pop(self, key, default=_MISSING):
    if key in self:
        value = self[key]
        del self[key]
        return value
    if default is _MISSING:
        raise KeyError(key)
    return default


def _setdefault(self, key, default=None):
    if key in self:
        return self[key]
    self[key] = default
    return default


for _name, _fn in (
    ("get", _get),
    ("items", _items),
    ("keys", _keys),
    ("values", _values),
    ("pop", _pop),
    ("setdefault", _setdefault),
):
    if not hasattr(StripeObject, _name):
        setattr(StripeObject, _name, _fn)
