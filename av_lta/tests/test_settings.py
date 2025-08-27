import os
from unittest.mock import patch

from django.test import override_settings
from portal.plugins.av_lta.models import Settings
from portal.plugins.av_lta.settings import PluginSettings
from portal.utils.test_case import PortalBaseTestCase


class TestPluginSettings(PortalBaseTestCase):
    def setUp(self):
        self.settings = PluginSettings()
        Settings.objects.filter(key__startswith="TEST_").delete()

    def tearDown(self):
        Settings.objects.filter(key__startswith="TEST_").delete()

    def test_getattribute_class_attributes(self):
        PluginSettings.TEST_ATTR1 = "test_value1"
        PluginSettings.TEST_ATTR2 = "test_value2"

        try:
            self.assertEqual(self.settings.TEST_ATTR1, "test_value1")
            self.assertEqual(self.settings.TEST_ATTR2, "test_value2")
        finally:
            delattr(PluginSettings, "TEST_ATTR1")
            delattr(PluginSettings, "TEST_ATTR2")

    def test_getattribute_db_value(self):
        Settings.objects.create(key="TEST_SETTING", value="db_value")

        self.assertEqual(self.settings.TEST_SETTING, "db_value")

    @override_settings(TEST_SETTING="django_value")
    def test_getattribute_django_settings(self):
        self.assertEqual(self.settings.TEST_SETTING, "django_value")

    @patch.dict(os.environ, {"TEST_SETTING": "env_value"})
    def test_getattribute_env_var(self):
        self.assertEqual(self.settings.TEST_SETTING, "env_value")

    def test_getattribute_priority(self):
        PluginSettings.TEST_PRIORITY = "class_value"

        self.assertEqual(self.settings.TEST_PRIORITY, "class_value")

        with patch.dict(os.environ, {"TEST_PRIORITY": "env_value"}):
            self.assertEqual(self.settings.TEST_PRIORITY, "env_value")

        with override_settings(TEST_PRIORITY="django_value"):
            with patch.dict(os.environ, {"TEST_PRIORITY": "env_value"}):
                self.assertEqual(self.settings.TEST_PRIORITY, "django_value")

        Settings.objects.create(key="TEST_PRIORITY", value="db_value")
        with override_settings(TEST_PRIORITY="django_value"):
            with patch.dict(os.environ, {"TEST_PRIORITY": "env_value"}):
                self.assertEqual(self.settings.TEST_PRIORITY, "db_value")

        delattr(PluginSettings, "TEST_PRIORITY")

    def test_getattribute_boolean_conversion(self):
        self.assertEqual(self.settings.AV_LTA_FORCE_FULL_DOMAIN, False)
        self.settings.AV_LTA_FORCE_FULL_DOMAIN = True
        self.assertEqual(self.settings.AV_LTA_FORCE_FULL_DOMAIN, True)

        # No default to know type from, so should save as string and read as string
        self.settings.TEST_NEW_SETTING = True
        self.assertEqual(self.settings.TEST_NEW_SETTING, "true")

    def test_setattr_new_setting(self):
        self.settings.TEST_NEW_SETTING = "new_value"

        db_setting = Settings.objects.get(key="TEST_NEW_SETTING")
        self.assertEqual(db_setting.value, "new_value")
        self.assertEqual(self.settings.TEST_NEW_SETTING, "new_value")

    def test_setattr_update_setting(self):
        Settings.objects.create(key="TEST_UPDATE_SETTING", value="old_value")

        self.settings.TEST_UPDATE_SETTING = "new_value"

        db_setting = Settings.objects.get(key="TEST_UPDATE_SETTING")
        self.assertEqual(db_setting.value, "new_value")
        self.assertEqual(self.settings.TEST_UPDATE_SETTING, "new_value")

    def test_setattr_boolean_conversion(self):
        self.settings.TEST_BOOL_TRUE = True
        self.settings.TEST_BOOL_FALSE = False

        db_true = Settings.objects.get(key="TEST_BOOL_TRUE")
        db_false = Settings.objects.get(key="TEST_BOOL_FALSE")

        self.assertEqual(db_true.value, "true")
        self.assertEqual(db_false.value, "false")

    def test_setattr_no_change(self):
        Settings.objects.create(key="TEST_NO_CHANGE", value="value")

        with patch.object(Settings.objects, "update_or_create") as mock_update:
            self.settings.TEST_NO_CHANGE = "value"
            mock_update.assert_not_called()
