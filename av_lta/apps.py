from django.apps import AppConfig


class AVLTAConfig(AppConfig):
    name = "portal.plugins.av_lta"
    verbose_name = "Accurate.Video LTA Plugin"

    def ready(self):
        from .permissions import create_or_update_roles

        create_or_update_roles()
