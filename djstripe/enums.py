from enum import Enum as _Enum
from django.utils.decorators import classproperty


class Enum(_Enum):
    @classproperty
    def choices(cls):
        return tuple((k, v.value) for k, v in cls.__members__.items())


class CardTokenizationMethod(Enum):
    apple_pay = "Apple Pay"
    android_pay = "Android Pay"
