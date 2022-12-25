"""
dj-stripe Utilities Tests.
"""
import time
from datetime import datetime
from decimal import Decimal
from unittest import skipIf
from unittest.mock import patch

from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from djstripe.constants import CURRENCY_SIGILS
from djstripe.utils import (
    convert_tstamp,
    get_friendly_currency_amount,
    get_supported_currency_choices,
)

TZ_IS_UTC = time.tzname == ("UTC", "UTC")


class TestTimestampConversion(TestCase):
    def test_conversion(self):
        stamp = convert_tstamp(1365567407)
        self.assertEqual(stamp, datetime(2013, 4, 10, 4, 16, 47, tzinfo=timezone.utc))

    # NOTE: These next two tests will fail if your system clock is not in UTC
    # Travis CI is, and coverage is good, so...

    @skipIf(not TZ_IS_UTC, "Skipped because timezone is not UTC.")
    @override_settings(USE_TZ=False)
    def test_conversion_no_tz(self):
        stamp = convert_tstamp(1365567407)
        self.assertEqual(stamp, datetime(2013, 4, 10, 4, 16, 47))


class TestGetSupportedCurrencyChoices(TestCase):
    @patch(
        "stripe.CountrySpec.retrieve",
        return_value={"supported_payment_currencies": ["usd", "cad", "eur"]},
    )
    @patch(
        "stripe.Account.retrieve",
        return_value={"country": "US"},
        autospec=True,
    )
    def test_get_choices(
        self, stripe_account_retrieve_mock, stripe_countryspec_retrieve_mock
    ):
        # Simple test to test sure that at least one currency choice tuple is returned.

        currency_choices = get_supported_currency_choices(None)
        stripe_account_retrieve_mock.assert_called_once_with(api_key=None)
        stripe_countryspec_retrieve_mock.assert_called_once_with("US", api_key=None)
        self.assertGreaterEqual(
            len(currency_choices), 1, "Currency choices pull returned an empty list."
        )
        self.assertEqual(
            tuple, type(currency_choices[0]), "Currency choices are not tuples."
        )
        self.assertIn(("usd", "USD"), currency_choices, "USD not in currency choices.")


class TestUtils(TestCase):
    def test_get_friendly_currency_amount(self):
        self.assertEqual(
            get_friendly_currency_amount(Decimal("1.001"), "usd"),
            f'{CURRENCY_SIGILS["USD"]}1.00 USD'
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "usd"),
            f'{CURRENCY_SIGILS["USD"]}10.00 USD'
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10.50"), "usd"),
            f'{CURRENCY_SIGILS["USD"]}10.50 USD'
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10.51"), "cad"),
            f'{CURRENCY_SIGILS["CAD"]}10.51 CAD'
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("9.99"), "eur"),
            f'{CURRENCY_SIGILS["EUR"]}9.99 EUR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "ars"),
            f'{CURRENCY_SIGILS["ARS"]}10.00 ARS',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "afn"),
            f'10.00 {CURRENCY_SIGILS["AFN"]} AFN',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "aed"),
            f'10.00 {CURRENCY_SIGILS["AED"]} AED',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "aud"),
            f'{CURRENCY_SIGILS["AUD"]}10.00 AUD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "azn"),
            f'{CURRENCY_SIGILS["AZN"]}10.00 AZN',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "bam"),
            f'{CURRENCY_SIGILS["BAM"]}10.00 BAM',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "bbd"),
            f'{CURRENCY_SIGILS["BBD"]}10.00 BBD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "bgn"),
            f'{CURRENCY_SIGILS["BGN"]}10.00 BGN',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "bmd"),
            f'{CURRENCY_SIGILS["BMD"]}10.00 BMD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "bnd"),
            f'{CURRENCY_SIGILS["BND"]}10.00 BND',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "bob"),
            f'{CURRENCY_SIGILS["BOB"]}10.00 BOB',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "brl"),
            f'{CURRENCY_SIGILS["BRL"]}10.00 BRL',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "bsd"),
            f'{CURRENCY_SIGILS["BSD"]}10.00 BSD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "bwp"),
            f'{CURRENCY_SIGILS["BWP"]}10.00 BWP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "byn"),
            f'{CURRENCY_SIGILS["BYN"]}10.00 BYN',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "bzd"),
            f'{CURRENCY_SIGILS["BZD"]}10.00 BZD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "chf"),
            f'10.00 {CURRENCY_SIGILS["CHF"]} CHF',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "clp"),
            f'{CURRENCY_SIGILS["CLP"]}10.00 CLP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "cny"),
            f'{CURRENCY_SIGILS["CNY"]}10.00 CNY',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "cop"),
            f'{CURRENCY_SIGILS["COP"]}10.00 COP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "crc"),
            f'{CURRENCY_SIGILS["CRC"]}10.00 CRC',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "czk"),
            f'{CURRENCY_SIGILS["CZK"]}10.00 CZK',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "dkk"),
            f'{CURRENCY_SIGILS["DKK"]}10.00 DKK',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "dop"),
            f'{CURRENCY_SIGILS["DOP"]}10.00 DOP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "egp"),
            f'{CURRENCY_SIGILS["EGP"]}10.00 EGP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "fjd"),
            f'{CURRENCY_SIGILS["FJD"]}10.00 FJD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "fkp"),
            f'{CURRENCY_SIGILS["FKP"]}10.00 FKP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "gel"),
            f'{CURRENCY_SIGILS["GEL"]}10.00 GEL',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "gip"),
            f'{CURRENCY_SIGILS["GIP"]}10.00 GIP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "gmd"),
            f'{CURRENCY_SIGILS["GMD"]}10.00 GMD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "gnf"),
            f'{CURRENCY_SIGILS["GNF"]}10.00 GNF',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "gtq"),
            f'{CURRENCY_SIGILS["GTQ"]}10.00 GTQ',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "gyd"),
            f'{CURRENCY_SIGILS["GYD"]}10.00 GYD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "hkd"),
            f'{CURRENCY_SIGILS["HKD"]}10.00 HKD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "hnl"),
            f'{CURRENCY_SIGILS["HNL"]}10.00 HNL',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "hrk"),
            f'{CURRENCY_SIGILS["HRK"]}10.00 HRK',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "htg"),
            f'{CURRENCY_SIGILS["HTG"]}10.00 HTG',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "huf"),
            f'{CURRENCY_SIGILS["HUF"]}10.00 HUF',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "idr"),
            f'{CURRENCY_SIGILS["IDR"]}10.00 IDR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "ils"),
            f'{CURRENCY_SIGILS["ILS"]}10.00 ILS',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "inr"),
            f'{CURRENCY_SIGILS["INR"]}10.00 INR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "isk"),
            f'10.00 {CURRENCY_SIGILS["ISK"]} ISK',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "jmd"),
            f'{CURRENCY_SIGILS["JMD"]}10.00 JMD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "jpy"),
            f'{CURRENCY_SIGILS["JPY"]}10.00 JPY',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "kes"),
            f'{CURRENCY_SIGILS["KES"]}10.00 KES',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "kgs"),
            f'{CURRENCY_SIGILS["KGS"]}10.00 KGS',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "khr"),
            f'{CURRENCY_SIGILS["KHR"]}10.00 KHR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "kmf"),
            f'{CURRENCY_SIGILS["KMF"]}10.00 KMF',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "krw"),
            f'{CURRENCY_SIGILS["KRW"]}10.00 KRW',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "kyd"),
            f'{CURRENCY_SIGILS["KYD"]}10.00 KYD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "kzt"),
            f'{CURRENCY_SIGILS["KZT"]}10.00 KZT',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "lak"),
            f'{CURRENCY_SIGILS["LAK"]}10.00 LAK',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "lbp"),
            f'10.00 {CURRENCY_SIGILS["LBP"]} LBP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "lkr"),
            f'{CURRENCY_SIGILS["LKR"]}10.00 LKR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "lrd"),
            f'{CURRENCY_SIGILS["LRD"]}10.00 LRD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "mga"),
            f'{CURRENCY_SIGILS["MGA"]}10.00 MGA',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "mkd"),
            f'{CURRENCY_SIGILS["MKD"]}10.00 MKD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "mmk"),
            f'{CURRENCY_SIGILS["MMK"]}10.00 MMK',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "mnt"),
            f'{CURRENCY_SIGILS["MNT"]}10.00 MNT',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "mop"),
            f'{CURRENCY_SIGILS["MOP"]}10.00 MOP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "mru"),
            f'{CURRENCY_SIGILS["MRU"]}10.00 MRU',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "mur"),
            f'{CURRENCY_SIGILS["MUR"]}10.00 MUR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "mwk"),
            f'{CURRENCY_SIGILS["MWK"]}10.00 MWK',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "mxn"),
            f'{CURRENCY_SIGILS["MXN"]}10.00 MXN',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "myr"),
            f'{CURRENCY_SIGILS["MYR"]}10.00 MYR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "mzn"),
            f'{CURRENCY_SIGILS["MZN"]}10.00 MZN',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "nad"),
            f'{CURRENCY_SIGILS["NAD"]}10.00 NAD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "ngn"),
            f'{CURRENCY_SIGILS["NGN"]}10.00 NGN',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "nio"),
            f'{CURRENCY_SIGILS["NIO"]}10.00 NIO',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "nok"),
            f'10.00 {CURRENCY_SIGILS["NOK"]} NOK',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "npr"),
            f'{CURRENCY_SIGILS["NPR"]}10.00 NPR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "nzd"),
            f'{CURRENCY_SIGILS["NZD"]}10.00 NZD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "pab"),
            f'{CURRENCY_SIGILS["PAB"]}10.00 PAB',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "pen"),
            f'{CURRENCY_SIGILS["PEN"]}10.00 PEN',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "pgk"),
            f'{CURRENCY_SIGILS["PGK"]}10.00 PGK',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "php"),
            f'{CURRENCY_SIGILS["PHP"]}10.00 PHP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "pkr"),
            f'{CURRENCY_SIGILS["PKR"]}10.00 PKR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "pln"),
            f'10.00 {CURRENCY_SIGILS["PLN"]} PLN',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "pyg"),
            f'{CURRENCY_SIGILS["PYG"]}10.00 PYG',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "qar"),
            f'10.00 {CURRENCY_SIGILS["QAR"]} QAR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "ron"),
            f'{CURRENCY_SIGILS["RON"]}10.00 RON',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "rsd"),
            f'{CURRENCY_SIGILS["RSD"]}10.00 RSD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "rub"),
            f'{CURRENCY_SIGILS["RUB"]}10.00 RUB',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "sar"),
            f'10.00 {CURRENCY_SIGILS["SAR"]} SAR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "sbd"),
            f'{CURRENCY_SIGILS["SBD"]}10.00 SBD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "scr"),
            f'{CURRENCY_SIGILS["SCR"]}10.00 SCR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "sek"),
            f'10.00 {CURRENCY_SIGILS["SEK"]} SEK',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "sgd"),
            f'{CURRENCY_SIGILS["SGD"]}10.00 SGD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "shp"),
            f'{CURRENCY_SIGILS["SHP"]}10.00 SHP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "sll"),
            f'{CURRENCY_SIGILS["SLL"]}10.00 SLL',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "sos"),
            f'{CURRENCY_SIGILS["SOS"]}10.00 SOS',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "srd"),
            f'{CURRENCY_SIGILS["SRD"]}10.00 SRD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "stn"),
            f'{CURRENCY_SIGILS["STN"]}10.00 STN',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "thb"),
            f'{CURRENCY_SIGILS["THB"]}10.00 THB',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "tjs"),
            f'{CURRENCY_SIGILS["TJS"]}10.00 TJS',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "top"),
            f'{CURRENCY_SIGILS["TOP"]}10.00 TOP',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "try"),
            f'{CURRENCY_SIGILS["TRY"]}10.00 TRY',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "ttd"),
            f'{CURRENCY_SIGILS["TTD"]}10.00 TTD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "twd"),
            f'{CURRENCY_SIGILS["TWD"]}10.00 TWD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "uah"),
            f'{CURRENCY_SIGILS["UAH"]}10.00 UAH',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "ugx"),
            f'{CURRENCY_SIGILS["UGX"]}10.00 UGX',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "uyu"),
            f'{CURRENCY_SIGILS["UYU"]}10.00 UYU',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "vnd"),
            f'{CURRENCY_SIGILS["VND"]}10.00 VND',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "vuv"),
            f'{CURRENCY_SIGILS["VUV"]}10.00 VUV',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "wst"),
            f'{CURRENCY_SIGILS["WST"]}10.00 WST',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "xcd"),
            f'{CURRENCY_SIGILS["XCD"]}10.00 XCD',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "yer"),
            f'10.00 {CURRENCY_SIGILS["YER"]} YER',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "zar"),
            f'{CURRENCY_SIGILS["ZAR"]}10.00 ZAR',
        )
        self.assertEqual(
            get_friendly_currency_amount(Decimal("10"), "zmw"),
            f'{CURRENCY_SIGILS["ZMW"]}10.00 ZMW',
        )
