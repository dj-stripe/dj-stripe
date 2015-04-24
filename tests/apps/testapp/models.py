from django.db.models.base import Model
from django.db.models.fields import EmailField, CharField


class Organization(Model):
    """ Model used to test the new custom model setting."""
    email = EmailField()


class StaticEmailOrganization(Model):
    """ Model used to test the new custom model setting."""
    name = CharField(max_length=200, unique=True)

    @property
    def email(self):
        return "static@example.com"


class NoEmailOrganization(Model):
    """ Model used to test the new custom model setting."""
    name = CharField(max_length=200, unique=True)
