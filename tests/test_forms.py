"""
dj-stripe form tests
"""
import pytest
from django.forms.utils import ErrorDict

from djstripe import enums
from djstripe.forms import APIKeyAdminCreateForm
from tests import FAKE_PLATFORM_ACCOUNT

from .test_apikey import RK_LIVE, RK_TEST, SK_LIVE, SK_TEST

pytestmark = pytest.mark.django_db


class TestAPIKeyAdminCreateForm:
    @pytest.mark.parametrize("secret", [SK_TEST, SK_LIVE, RK_TEST, RK_LIVE])
    def test__post_clean(self, secret, monkeypatch):

        form = APIKeyAdminCreateForm(data={"name": "Test Secret Key", "secret": secret})

        # Manually invoking internals of Form.full_clean() to isolate
        # Form._post_clean
        form._errors = ErrorDict()
        form.cleaned_data = {}
        form._clean_fields()
        form._clean_form()

        # assert form is valid but instance is not yet saved in the db.
        assert form.instance.pk is None
        assert form.is_valid() is True

        # assert that the instance does not have the owner account populated
        assert form.instance.djstripe_owner_account is None

        # Invoke _post_clean()
        form._post_clean()

        if secret.startswith("sk_"):
            assert form.instance.type == enums.APIKeyType.secret
            assert (
                form.instance.djstripe_owner_account.id == FAKE_PLATFORM_ACCOUNT["id"]
            )
        elif secret.startswith("rk_"):
            assert form.instance.type == enums.APIKeyType.restricted
            assert form.instance.djstripe_owner_account is None
