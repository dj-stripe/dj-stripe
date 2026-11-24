"""
dj-stripe Admin Actions Tests.
"""

import warnings

import pytest
from django.contrib.admin import site
from django.contrib.auth import get_user_model

from djstripe import models
from djstripe.admin.actions import CustomActionMixin

try:
    from django.contrib.admin import ActionLocation
except ImportError:  # Django < 6.1 has no action locations
    ActionLocation = None

requires_action_locations = pytest.mark.skipif(
    ActionLocation is None, reason="Admin action locations were added in Django 6.1"
)

DJSTRIPE_MODEL_ADMINS = [
    pytest.param(model_admin, id=type(model_admin).__name__)
    for model, model_admin in site._registry.items()
    if model._meta.app_label == "djstripe"
]

CUSTOM_ACTION_MODEL_ADMINS = [
    param
    for param in DJSTRIPE_MODEL_ADMINS
    if isinstance(param.values[0], CustomActionMixin)
]


@pytest.fixture
def superuser():
    return get_user_model()(is_active=True, is_staff=True, is_superuser=True)


@pytest.fixture
def admin_request(rf, superuser):
    request = rf.get("/admin/")
    request.user = superuser
    return request


@pytest.mark.parametrize("model_admin", CUSTOM_ACTION_MODEL_ADMINS)
def test_change_list_actions(model_admin, admin_request):
    model = model_admin.model
    actions = model_admin.get_actions(admin_request)

    # Objects can only be re-synced when Stripe can retrieve them.
    can_retrieve = bool(getattr(model.stripe_class, "retrieve", None))
    assert ("_resync_instances" in actions) is can_retrieve
    # Discounts and Mandates cannot be listed, so they cannot be synced in bulk.
    can_list = model not in (models.Discount, models.Mandate)
    assert ("_sync_all_instances" in actions) is can_list
    # Webhook endpoints are never deleted in bulk.
    assert ("delete_selected" in actions) is (model is not models.WebhookEndpoint)
    assert ("_cancel" in actions) is (model is models.Subscription)


@pytest.mark.parametrize("model_admin", CUSTOM_ACTION_MODEL_ADMINS)
def test_popups_have_no_actions(model_admin, rf, superuser):
    request = rf.get("/admin/", {"_popup": "1"})
    request.user = superuser

    assert model_admin.get_actions(request) == {}


@requires_action_locations
@pytest.mark.parametrize("model_admin", DJSTRIPE_MODEL_ADMINS)
def test_admin_reaches_get_actions_without_deprecation_warning(
    model_admin, admin_request
):
    # Django 6.1 warns about get_actions() overrides that lack the
    # action_location parameter, and gives them no change form actions.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for location in ActionLocation:
            model_admin.get_action_choices(admin_request, action_location=location)


@requires_action_locations
@pytest.mark.parametrize("model_admin", DJSTRIPE_MODEL_ADMINS)
def test_get_actions_honours_action_location(model_admin, admin_request):
    offered = {
        location: model_admin.get_actions(admin_request, action_location=location)
        for location in ActionLocation
    }
    # Every action is offered at each location it declares, and only there.
    all_actions = {
        name: action for actions in offered.values() for name, action in actions.items()
    }
    for name, action in all_actions.items():
        for location in ActionLocation:
            declared = location in action.locations
            assert (name in offered[location]) is declared, f"{name} on {location}"

    # Without a location, get_actions() returns the change list actions, whose
    # names test_change_list_actions checks.
    assert list(offered[ActionLocation.CHANGE_LIST]) == list(
        model_admin.get_actions(admin_request)
    )
