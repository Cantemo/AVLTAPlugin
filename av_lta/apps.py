import logging

from django.apps import AppConfig
from django.db.utils import ProgrammingError
from portal.pluginbase.core import PluginError

log = logging.getLogger(__name__)


class AVLTAConfig(AppConfig):
    name = "portal.plugins.av_lta"
    verbose_name = "Accurate.Video LTA Plugin"

    def ready(self):
        from .permissions import create_or_update_roles

        try:
            create_or_update_roles()
        except Exception:
            log.exception("AVLTA Plugin: Could not create roles")
