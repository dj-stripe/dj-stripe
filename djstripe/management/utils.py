"""Helper functions for Django Admin Management Commands"""

from django.db import models as django_models

from .. import enums, models


def get_list_kwargs_pm(default_list_kwargs):
    """Returns sequence of kwrags to sync Payment Methods for
    all Stripe Accounts"""

    all_list_kwargs = []
    payment_method_types = enums.PaymentMethodType.__members__

    for def_kwarg in default_list_kwargs:
        stripe_account = def_kwarg.get("stripe_account")
        api_key = def_kwarg.get("api_key")
        for stripe_customer in models.Customer.api_list(
            stripe_account=stripe_account, api_key=api_key
        ):
            for type in payment_method_types:
                all_list_kwargs.append(
                    {"customer": stripe_customer.id, "type": type, **def_kwarg}
                )

    return all_list_kwargs


def get_list_kwargs_src(default_list_kwargs):
    """Returns sequence of kwargs to sync Sources for
    all Stripe Accounts"""

    all_list_kwargs = []
    for def_kwarg in default_list_kwargs:
        stripe_account = def_kwarg.get("stripe_account")
        api_key = def_kwarg.get("api_key")
        for stripe_customer in models.Customer.api_list(
            stripe_account=stripe_account, api_key=api_key
        ):
            all_list_kwargs.append({"id": stripe_customer.id, **def_kwarg})

    return all_list_kwargs


def get_list_kwargs_si(default_list_kwargs):
    """Returns sequence of kwrags to sync Subscription Items for
    all Stripe Accounts"""

    all_list_kwargs = []
    for def_kwarg in default_list_kwargs:
        stripe_account = def_kwarg.get("stripe_account")
        api_key = def_kwarg.get("api_key")
        for subscription in models.Subscription.api_list(
            stripe_account=stripe_account, api_key=api_key
        ):
            all_list_kwargs.append({"subscription": subscription.id, **def_kwarg})
    return all_list_kwargs


def get_list_kwargs_country_spec(default_list_kwargs):
    """Returns sequence of kwrags to sync Country Specs for
    all Stripe Accounts"""

    all_list_kwargs = []
    for def_kwarg in default_list_kwargs:
        all_list_kwargs.append({"limit": 50, **def_kwarg})

    return all_list_kwargs


def get_list_kwargs_txcd(default_list_kwargs):
    """Returns sequence of kwargs to sync Tax Codes for
    all Stripe Accounts"""

    # tax codes are the same for all Stripe Accounts
    return [{}]


def get_list_kwargs_trr(default_list_kwargs):
    """Returns sequence of kwrags to sync Transfer Reversals for
    all Stripe Accounts"""
    all_list_kwargs = []
    for def_kwarg in default_list_kwargs:
        stripe_account = def_kwarg.get("stripe_account")
        api_key = def_kwarg.get("api_key")
        for transfer in models.Transfer.api_list(
            stripe_account=stripe_account, api_key=api_key
        ):
            all_list_kwargs.append({"id": transfer.id, **def_kwarg})

    return all_list_kwargs


def get_list_kwargs_fee_refund(default_list_kwargs):
    """Returns sequence of kwrags to sync Application Fee Refunds for
    all Stripe Accounts"""
    all_list_kwargs = []
    for def_kwarg in default_list_kwargs:
        stripe_account = def_kwarg.get("stripe_account")
        api_key = def_kwarg.get("api_key")
        for fee in models.ApplicationFee.api_list(
            stripe_account=stripe_account, api_key=api_key
        ):
            all_list_kwargs.append({"id": fee.id, **def_kwarg})

    return all_list_kwargs


def get_list_kwargs_tax_id(default_list_kwargs):
    """Returns sequence of kwrags to sync Tax Ids for
    all Stripe Accounts"""
    all_list_kwargs = []
    for def_kwarg in default_list_kwargs:
        stripe_account = def_kwarg.get("stripe_account")
        api_key = def_kwarg.get("api_key")
        for customer in models.Customer.api_list(
            stripe_account=stripe_account, api_key=api_key
        ):
            all_list_kwargs.append({"id": customer.id, **def_kwarg})

    return all_list_kwargs


def get_list_kwargs_sis(default_list_kwargs):
    """Returns sequence of kwrags to sync Usage Record Summarys for
    all Stripe Accounts"""
    all_list_kwargs = []
    for def_kwarg in default_list_kwargs:
        stripe_account = def_kwarg.get("stripe_account")
        api_key = def_kwarg.get("api_key")
        for subscription in models.Subscription.api_list(
            stripe_account=stripe_account, api_key=api_key
        ):
            for subscription_item in models.SubscriptionItem.api_list(
                subscription=subscription.id,
                stripe_account=stripe_account,
                api_key=api_key,
            ):
                all_list_kwargs.append({"id": subscription_item.id, **def_kwarg})

    return all_list_kwargs


# todo add a parent model, related model args to make the . chanin explicit?
def util(model, expand=[]):
    rel_fields = []
    try:
        # get all forward and reverse relations for given cls
        for field in model.expand_fields:
            expand.append(f"data.{field}")

            field_inst = model._meta.get_field(field)

            # get expand_fields on Forward FK and OneToOneField relations on the current model
            if isinstance(
                field_inst, (django_models.ForeignKey, django_models.OneToOneField)
            ):

                rel_fields.append(field_inst)

    except AttributeError:
        pass
    # print(expand)
    return rel_fields, expand


# todo simplfy this code by spliting ontop 1-2 functions


def get_default_list_kwargs_new(model, accounts_set, api_key: str):
    """Returns default sequence of kwargs to sync
    all Stripe Accounts"""
    expand = []

    related_fields, expand = util(model, expand)

    try:
        for field in related_fields:
            related_fields_new, expand = util(field.related_model, expand=expand)
            for related_model_expand_field_inst in related_fields_new:
                try:
                    # need to prepend "field_name." to each of the entry in the expand_fields list
                    related_model_expand_fields = map(
                        lambda i: f"data.{field.name}.{related_model_expand_field_inst.name}.{i}",
                        related_model_expand_field_inst.related_model.expand_fields,
                    )

                    expand = [
                        *expand,
                        *related_model_expand_fields,
                    ]
                except AttributeError:
                    continue

    except AttributeError:
        pass

    if expand:
        default_list_kwargs = [
            {
                "expand": expand,
                "stripe_account": account,
                "api_key": api_key,
            }
            for account in accounts_set
        ]

    else:
        default_list_kwargs = [
            {
                "stripe_account": account,
                "api_key": api_key,
            }
            for account in accounts_set
        ]
    print("expand:", expand)

    return default_list_kwargs


# todo simplfy this code by spliting ontop 1-2 functions
def get_default_list_kwargs(model, accounts_set, api_key: str):  # noqa: C901
    """Returns default sequence of kwargs to sync
    all Stripe Accounts"""
    expand = []

    try:
        # get all forward and reverse relations for given cls
        for field in model.expand_fields:
            # add expand_field on the current model
            expand.append(f"data.{field}")

            field_inst = model._meta.get_field(field)

            # get expand_fields on Forward FK and OneToOneField relations on the current model
            if isinstance(
                field_inst, (django_models.ForeignKey, django_models.OneToOneField)
            ):

                try:
                    for (
                        related_model_expand_field
                    ) in field_inst.related_model.expand_fields:
                        # add expand_field on the current model
                        expand.append(f"data.{field}.{related_model_expand_field}")

                        related_model_expand_field_inst = (
                            field_inst.related_model._meta.get_field(
                                related_model_expand_field
                            )
                        )

                        # get expand_fields on Forward FK and OneToOneField relations on the current model
                        if isinstance(
                            related_model_expand_field_inst,
                            (
                                django_models.ForeignKey,
                                django_models.OneToOneField,
                            ),
                        ):

                            try:
                                # need to prepend "field_name." to each of the entry in the expand_fields list
                                related_model_expand_fields = map(
                                    lambda i: f"data.{field_inst.name}.{related_model_expand_field}.{i}",
                                    related_model_expand_field_inst.related_model.expand_fields,
                                )

                                expand = [
                                    *expand,
                                    *related_model_expand_fields,
                                ]
                            except AttributeError:
                                continue
                except AttributeError:
                    continue

    except AttributeError:
        pass

    if expand:
        default_list_kwargs = [
            {
                "expand": expand,
                "stripe_account": account,
                "api_key": api_key,
            }
            for account in accounts_set
        ]

    else:
        default_list_kwargs = [
            {
                "stripe_account": account,
                "api_key": api_key,
            }
            for account in accounts_set
        ]

    return default_list_kwargs


# todo convert get_list_kwargs into a generator to make the code memory effecient.
# todo handle supoorting double + nested fields like data.invoice.subscriptions.customer etc?
def get_list_kwargs(model, api_key: str):
    """
    Returns a sequence of kwargs dicts to pass to model.api_list

    This allows us to sync models that require parameters to api_list

    :param model:
    :return: Sequence[dict]
    """

    list_kwarg_handlers_dict = {
        "PaymentMethod": get_list_kwargs_pm,
        "Source": get_list_kwargs_src,
        "SubscriptionItem": get_list_kwargs_si,
        "CountrySpec": get_list_kwargs_country_spec,
        "TransferReversal": get_list_kwargs_trr,
        "ApplicationFeeRefund": get_list_kwargs_fee_refund,
        "TaxCode": get_list_kwargs_txcd,
        "TaxId": get_list_kwargs_tax_id,
        "UsageRecordSummary": get_list_kwargs_sis,
    }

    # get all Stripe Accounts for the given platform account.
    # note that we need to fetch from Stripe as we have no way of knowing that the ones in the local db are up to date
    # as this can also be the first time the user runs sync.
    accs_set = get_stripe_account(api_key=api_key)

    default_list_kwargs = get_default_list_kwargs(model, accs_set, api_key=api_key)

    default_list_kwargs_new = get_default_list_kwargs_new(
        model, accs_set, api_key=api_key
    )
    # assert default_list_kwargs == default_list_kwargs_new

    handler = list_kwarg_handlers_dict.get(
        model.__name__, lambda _: default_list_kwargs
    )

    return handler(default_list_kwargs)


def get_stripe_account(api_key: str, *args, **kwargs):
    """Get set of all stripe account ids including the Platform Acccount"""
    accs_set = set()

    # special case, since own account isn't returned by Account.api_list
    stripe_platform_obj = models.Account.stripe_class.retrieve(api_key=api_key)
    accs_set.add(stripe_platform_obj.id)

    for stripe_connected_obj in models.Account.api_list(api_key=api_key, **kwargs):
        accs_set.add(stripe_connected_obj.id)

    return accs_set
