from typing import Optional, Any

import requests
from django.conf import settings
from requests import Response


def get_vidispine_url(path: str) -> str:
    return f"{settings.VIDISPINE_URL}:{settings.VIDISPINE_PORT}/API{path}"


def get_vidispine_auth() -> tuple[str, str]:
    return settings.VIDISPINE_USERNAME, settings.VIDISPINE_PASSWORD


def vidispine_request(method: str, path: str, **kwargs) -> Response:
    response = requests.request(method, get_vidispine_url(path), auth=get_vidispine_auth(), **kwargs)
    response.raise_for_status()
    return response


def import_shape_raw(
        item_id: str,
        data: Any,
        tag: Optional[str] = None,
        storage_id: Optional[str] = None,
        filename: Optional[str] = None,
        transfer_priority: Optional[int] = None,
        transfer_id: Optional[str] = None,
        notification: Optional[str] = None,
        notification_data: Optional[str] = None,
        priority: Optional[str] = None,
        jobmetadata: Optional[list[str]] = None,
) -> Response:
    params = dict(
        tag=tag,
        storageId=storage_id,
        filename=filename,
        transferPriority=transfer_priority,
        transferId=transfer_id,
        notification=notification,
        notificationData=notification_data,
        priority=priority,
        jobmetadata=jobmetadata,
    )
    return vidispine_request("POST", f"/item/{item_id}/shape/raw", params=params, data=data)
