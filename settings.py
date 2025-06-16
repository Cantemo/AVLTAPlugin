import os
from typing import Any

from django.conf import settings


def get_setting(name, default: Any):
    return getattr(settings, name, None) or os.getenv(name, None) or default


AV_LTA_APPS_URL = get_setting("AV_LTA_APPS_URL", "https://apps.dev.svc.accurate.video/")
