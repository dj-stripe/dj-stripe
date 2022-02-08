# import pytest
# from django.core.checks import Error
# from django.test import TestCase, override_settings

# # errors = checked_object.check()
# # expected_errors = [
# #     Error(
# #         'an error',
# #         hint='A hint.',
# #         obj=checked_object,
# #         id='myapp.E001',
# #     )
# # ]
# # self.assertEqual(errors, expected_errors)


# class TestChecks(TestCase):
#     def foo_1(a, b, *args, **kwargs):
#         pass

#     def foo_2(a, *args):
#         pass

#     def foo_3(a, **kwargs):
#         pass

#     def foo_4(a):
#         pass

#     @override_settings(DJSTRIPE_WEBHOOK_EVENT_CALLBACK=foo_4)
#     def test_check_webhook_event_callback_accepts_api_key(self):
#         a = 5
#         breakpoint()
