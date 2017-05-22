from enum import Enum as _Enum
from django.utils.decorators import classproperty


class Enum(_Enum):
    @classproperty
    def choices(cls):
        return tuple((cls.keys.get(k, k), v.value) for k, v in cls.__members__.items())

    @classproperty
    def keys(cls):
        # Returns a mapping of key overrides.
        # This allows using syntactically-incorrect values as keys,
        # such as keywords ("pass") or spaces ("Diners Club").
        # This cannot be an attribute, otherwise it would show up as a choice.
        return {}


class CardTokenizationMethod(Enum):
    apple_pay = "Apple Pay"
    android_pay = "Android Pay"
