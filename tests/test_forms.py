"""
dj-stripe form tests
"""
import pytest
from django import forms
from django.contrib.admin import helpers
from django.forms.utils import ErrorDict

from djstripe import enums, utils
from djstripe.admin.forms import APIKeyAdminCreateForm, CustomActionForm
from tests import FAKE_PLATFORM_ACCOUNT

from .fields.models import CustomActionModel
from .test_apikey import RK_LIVE, RK_TEST, SK_LIVE, SK_TEST

pytestmark = pytest.mark.django_db


class TestCustomActionForm:
    @pytest.mark.parametrize(
        "action_name", ["_sync_all_instances", "_resync_instances"]
    )
    def test___init__(self, action_name, monkeypatch):

        # monkeypatch utils.get_model
        def mock_get_model(*args, **kwargs):
            return model

        monkeypatch.setattr(utils, "get_model", mock_get_model)

        model = CustomActionModel

        # create instances to be used in the Django Admin Action
        inst_1 = model.objects.create(id="test")
        inst_2 = model.objects.create(id="test-2")
        pk_values = [inst_1.pk, inst_2.pk]

        form = CustomActionForm(
            model_name=CustomActionModel._meta.model_name,
            action_name=action_name,
        )

        # assert _selected_action_field has been added to the form
        _selected_action_field = form.fields[helpers.ACTION_CHECKBOX_NAME]
        assert _selected_action_field is not None

        # assert _selected_action_field is an instance of MultipleHiddenInput
        assert isinstance(_selected_action_field.widget, forms.MultipleHiddenInput)

        if action_name == "_sync_all_instances":
            assert _selected_action_field.choices == [
                ("_sync_all_instances", "_sync_all_instances")
            ]
        else:
            assert _selected_action_field.choices == list(zip(pk_values, pk_values))


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
