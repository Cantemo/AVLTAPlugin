import logging

from portal.api import client
from portal.pluginbase.core import PluginError

log = logging.getLogger(__name__)


def create_or_update_roles():
    root_role = "av_lta_role"
    role_data = {
        "name": root_role,
        "label": "AV LTA Roles",
        "children": [
            {
                "name": "av_lta_role_subtitle",
                "label": "Subtitle",
                "children": [],
            },
        ],
    }
    log.info(f"Create/update role tree {root_role}")
    response = client.post(user="admin", url="/API/v2/groups/roles/create/", json=role_data)
    if response.status_code != 200:
        raise PluginError(f"Failed to create role {root_role}: {response.status_code} - {response.content}")
