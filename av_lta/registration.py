import logging

from portal.generic.plugin_interfaces import IAppRegister, IPluginBootstrap
from portal.pluginbase.core import Plugin, implements
from portal.utils.apps import is_app_enabled

app_id = "se.codemill.portal.av_lta"

log = logging.getLogger(__name__)


class AVLTARegisterPlugin(Plugin):
    implements(IAppRegister)

    def __init__(self):
        self.name = self.__class__.__name__
        self.plugin_guid = '0e3124bc-1f37-49cc-adf5-ae2fc3b8bf42'

    def __call__(self):
        from .__init__ import __version__ as versionnumber
        _app_dict = {
            'name': 'Accurate.Video LTA Plugin',
            'version': versionnumber,
            'author': 'Codemill AB',
            'author_url': 'www.codemill.se',
            'notes': 'Copyright © 2022-2024. All rights reserved.',
            'enabled': is_app_enabled(app_id),
            'app_id': app_id,
        }
        return _app_dict


AVLTARegisterPlugin()


class AVLTAPluginBootstrap(Plugin):
    implements(IPluginBootstrap)

    def bootstrap(self):
        if is_app_enabled(app_id):
            from . import plugin  # noqa


AVLTAPluginBootstrap()
