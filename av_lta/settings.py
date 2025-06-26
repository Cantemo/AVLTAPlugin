import os

from django.conf import settings

from .models import Settings
from .utils import str_to_bool


class PluginSettings(object):
    AV_LTA_APPS_URL = "https://apps.dev.svc.accurate.video/"
    AV_LTA_FORCE_FULL_DOMAIN = False
    AV_LTA_PUBLISH_SHAPE_TAG = "av-subtitle"
    AV_LTA_EXTRA_SETTINGS = ""

    def __getattribute__(self, name):
        db_setting_value = None
        try:
            default_value = super(PluginSettings, self).__getattribute__(name)
        except AttributeError:
            default_value = None
        expected_type = type(default_value)
        try:
            setting = Settings.objects.get(key=name)
            db_setting_value = setting.value
        except Settings.DoesNotExist:
            pass
        value = db_setting_value or \
            getattr(settings, name, None) or \
            os.getenv(name, None) or \
            default_value
        if expected_type == bool:
            return str_to_bool(value)
        return value

    def __setattr__(self, key, value):
        if getattr(self, key, None) == value:
            return
        if type(value) == bool:
            value = str(value).lower()
        Settings.objects.update_or_create(
            key=key,
            defaults=dict(value=value)
        )

plugin_settings = PluginSettings()
