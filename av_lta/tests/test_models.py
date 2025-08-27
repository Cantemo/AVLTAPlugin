from django.db import IntegrityError
from django.db import transaction
from portal.plugins.av_lta.models import Settings
from portal.utils.test_case import PortalBaseTestCase


class TestSettingsModel(PortalBaseTestCase):
    def setUp(self):
        Settings.objects.filter(key__startswith="TEST_").delete()

    def tearDown(self):
        Settings.objects.filter(key__startswith="TEST_").delete()

    def test_create_settings(self):
        setting = Settings.objects.create(key="TEST_KEY", value="test_value")

        self.assertEqual(setting.key, "TEST_KEY")
        self.assertEqual(setting.value, "test_value")

        retrieved_setting = Settings.objects.get(key="TEST_KEY")
        self.assertEqual(retrieved_setting.key, "TEST_KEY")
        self.assertEqual(retrieved_setting.value, "test_value")

    def test_key_unique_constraint(self):
        Settings.objects.create(key="TEST_UNIQUE", value="value1")

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                Settings.objects.create(key="TEST_UNIQUE", value="value2")

    def test_value_nullable(self):
        setting = Settings.objects.create(key="TEST_NULL_VALUE", value=None)

        self.assertEqual(setting.key, "TEST_NULL_VALUE")
        self.assertIsNone(setting.value)

        retrieved_setting = Settings.objects.get(key="TEST_NULL_VALUE")
        self.assertEqual(retrieved_setting.key, "TEST_NULL_VALUE")
        self.assertIsNone(retrieved_setting.value)

    def test_value_blank(self):
        setting = Settings.objects.create(key="TEST_BLANK_VALUE", value="")

        self.assertEqual(setting.key, "TEST_BLANK_VALUE")
        self.assertEqual(setting.value, "")

        retrieved_setting = Settings.objects.get(key="TEST_BLANK_VALUE")
        self.assertEqual(retrieved_setting.key, "TEST_BLANK_VALUE")
        self.assertEqual(retrieved_setting.value, "")

    def test_update_settings(self):
        setting = Settings.objects.create(key="TEST_UPDATE", value="initial_value")

        setting.value = "updated_value"
        setting.save()

        retrieved_setting = Settings.objects.get(key="TEST_UPDATE")
        self.assertEqual(retrieved_setting.value, "updated_value")

    def test_max_key_length(self):
        max_length_key = "X" * 255
        setting = Settings.objects.create(key=max_length_key, value="test_value")

        self.assertEqual(setting.key, max_length_key)

        with transaction.atomic():
            with self.assertRaises(Exception):
                Settings.objects.create(key="X" * 256, value="test_value")
