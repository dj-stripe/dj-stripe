"""
Django Administration Custom Actions Module
"""
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.utils import quote
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.text import capfirst

from . import views
from .forms import CustomActionForm


class CustomActionMixin:

    # So that actions get shown even if there are 0 instances
    # https://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.show_full_result_count
    show_full_result_count = False

    def get_urls(self):
        custom_urls = [
            path(
                "action/<str:action_name>/<str:model_name>/",
                self.admin_site.admin_view(views.ConfirmCustomAction.as_view()),
                name="djstripe_custom_action",
            ),
        ]
        return custom_urls + super().get_urls()

    def get_admin_action_context(self, queryset, action_name, form_class):

        context = {
            "action_name": action_name,
            "model_name": self.model._meta.model_name,
            "info": [],
            "queryset": queryset,
            "changelist_url": reverse(
                f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist"
            ),
            "ACTION_CHECKBOX_NAME": helpers.ACTION_CHECKBOX_NAME,
            "form": form_class(
                initial={
                    helpers.ACTION_CHECKBOX_NAME: queryset.values_list("pk", flat=True)
                },
                model_name=self.model._meta.model_name,
                action_name=action_name,
            ),
        }

        if action_name == "_sync_all_instances":
            context["form"] = form_class(
                initial={helpers.ACTION_CHECKBOX_NAME: [action_name]},
                model_name=self.model._meta.model_name,
                action_name=action_name,
            )

        else:
            for obj in queryset:
                admin_url = reverse(
                    f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
                    None,
                    (quote(obj.pk),),
                )
                context["info"].append(
                    format_html(
                        '{}: <a href="{}">{}</a>',
                        capfirst(obj._meta.verbose_name),
                        admin_url,
                        obj,
                    )
                )
        return context

    def get_actions(self, request):
        """
        Returns _resync_instances only for
        models with a defined model.stripe_class.retrieve
        """
        actions = super().get_actions(request)

        # ensure we return "_resync_instances" ONLY for
        # models that have a GET method
        if not getattr(self.model.stripe_class, "retrieve", None):
            actions.pop("_resync_instances", None)

        return actions

    @admin.action(description="Re-Sync Selected Instances")
    def _resync_instances(self, request, queryset):
        """Admin Action to resync selected instances"""
        context = self.get_admin_action_context(
            queryset, "_resync_instances", CustomActionForm
        )
        return render(request, "djstripe/admin/confirm_action.html", context)

    @admin.action(description="Sync All Instances for all API Keys")
    def _sync_all_instances(self, request, queryset):
        """Admin Action to Sync All Instances"""
        context = self.get_admin_action_context(
            queryset, "_sync_all_instances", CustomActionForm
        )
        return render(request, "djstripe/admin/confirm_action.html", context)

    def changelist_view(self, request, extra_context=None):
        # we fool it into thinking we have selected some query
        # since we need to sync all instances
        post = request.POST.copy()
        if (
            helpers.ACTION_CHECKBOX_NAME not in post
            and post.get("action") == "_sync_all_instances"
        ):
            post[helpers.ACTION_CHECKBOX_NAME] = None
            request._set_post(post)
        return super().changelist_view(request, extra_context)
