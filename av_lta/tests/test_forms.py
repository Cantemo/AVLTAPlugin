from portal.plugins.av_lta.forms import SettingsForm
from portal.utils.test_case import PortalBaseTestCase


class TestSettingsForm(PortalBaseTestCase):
    def test_form_valid_data(self):
        valid_data = {
            "AV_LTA_APPS_URL": "https://example.com",
            "AV_LTA_PUBLISH_SHAPE_TAG": "tag1",
            "AV_LTA_FORCE_FULL_DOMAIN": True,
            "AV_LTA_EXTRA_SETTINGS": '{"key": "value"}',
        }

        form = SettingsForm(data=valid_data)
        self.assertTrue(form.is_valid())

        minimal_data = {}
        form = SettingsForm(data=minimal_data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_json(self):
        invalid_data = {"AV_LTA_EXTRA_SETTINGS": "{invalid json}"}

        form = SettingsForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn("AV_LTA_EXTRA_SETTINGS", form.errors)
        self.assertEqual(form.errors["AV_LTA_EXTRA_SETTINGS"][0], "Invalid JSON")

    def test_clean_extra_settings_empty(self):
        form = SettingsForm(data={"AV_LTA_EXTRA_SETTINGS": ""})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["AV_LTA_EXTRA_SETTINGS"], "")

        form = SettingsForm(data={})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["AV_LTA_EXTRA_SETTINGS"], "")

    def test_clean_extra_settings_valid_json(self):
        valid_json = '{"key1": "value1", "key2": 42, "key3": [1, 2, 3]}'
        form = SettingsForm(data={"AV_LTA_EXTRA_SETTINGS": valid_json})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["AV_LTA_EXTRA_SETTINGS"], valid_json)

        form = SettingsForm(data={"AV_LTA_EXTRA_SETTINGS": "{}"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["AV_LTA_EXTRA_SETTINGS"], "{}")

        form = SettingsForm(data={"AV_LTA_EXTRA_SETTINGS": "[]"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["AV_LTA_EXTRA_SETTINGS"], "[]")

    def test_clean_extra_settings_invalid_json(self):
        invalid_json_values = [
            '{key: "value"}',  # Missing quotes around key
            '{"key": value}',  # Missing quotes around value
            '{"key": "value",}',  # Trailing comma
            "{key: value}",  # Missing quotes around both
            '{"incomplete": ',  # Incomplete JSON
            "[1, 2, 3,]",  # Trailing comma in array
        ]

        for invalid_json in invalid_json_values:
            form = SettingsForm(data={"AV_LTA_EXTRA_SETTINGS": invalid_json})
            self.assertFalse(form.is_valid())
            self.assertIn("AV_LTA_EXTRA_SETTINGS", form.errors)
            self.assertEqual(form.errors["AV_LTA_EXTRA_SETTINGS"][0], "Invalid JSON")

    def test_clean_av_lta_apps_url_appends_slash(self):
        """Tests that a trailing slash is correctly appended to a URL that lacks one."""
        form = SettingsForm(data={"AV_LTA_APPS_URL": "http://lta.example.com"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["AV_LTA_APPS_URL"], "http://lta.example.com/")

    def test_clean_av_lta_apps_url_with_existing_slash(self):
        """Tests that a URL with an existing trailing slash is not modified."""
        form = SettingsForm(data={"AV_LTA_APPS_URL": "http://lta.example.com/"})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["AV_LTA_APPS_URL"], "http://lta.example.com/")

    def test_clean_av_lta_apps_url_empty_or_missing(self):
        """Tests that the form is valid when the URL is an empty string or not provided."""
        # Test with an empty string
        form_empty = SettingsForm(data={"AV_LTA_APPS_URL": ""})
        self.assertTrue(form_empty.is_valid())
        self.assertEqual(form_empty.cleaned_data["AV_LTA_APPS_URL"], "")

        # Test with the field missing from data (since required=False)
        form_missing = SettingsForm(data={})
        self.assertTrue(form_missing.is_valid())
        self.assertEqual(form_missing.cleaned_data["AV_LTA_APPS_URL"], "")
