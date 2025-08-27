import logging
from typing import Optional

import requests
from django.conf import settings
from requests import Response

log = logging.getLogger(__name__)


def get_vidispine_url(path: str) -> str:
    return f"{settings.VIDISPINE_URL}:{settings.VIDISPINE_PORT}/API{path}"


def get_vidispine_auth() -> tuple[str, str]:
    return settings.VIDISPINE_USERNAME, settings.VIDISPINE_PASSWORD


def vidispine_request(method: str, path: str, runas: Optional[str] = None, **kwargs) -> Response:
    headers = kwargs.pop("headers", {})
    headers["Accept"] = "application/json"
    if runas is not None:
        headers["RunAs"] = str(runas)
    full_path = get_vidispine_url(path)
    response = requests.request(method, full_path, auth=get_vidispine_auth(), headers=headers, **kwargs)
    if not response.ok:
        log.error(
            f"Vidispine ERROR: {method} {full_path}\n{headers=}\n{kwargs=}\n{response.status_code=}\n{response.content.decode()}"
        )
    response.raise_for_status()
    return response


def import_shape_raw(
    item_id: str,
    data: bytes,
    tag: Optional[str] = None,
    storage_id: Optional[str] = None,
    filename: Optional[str] = None,
    transfer_priority: Optional[int] = None,
    transfer_id: Optional[str] = None,
    notification: Optional[str] = None,
    notification_data: Optional[str] = None,
    priority: Optional[str] = None,
    jobmetadata: Optional[list[str]] = None,
    runas: Optional[str] = None,
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
    return vidispine_request("POST", f"/item/{item_id}/shape/raw", params=params, data=data, runas=runas)


def update_or_create_file_data(file_id: str, data: bytes, runas: Optional[str] = None) -> Response:
    return vidispine_request("POST", f"/file/{file_id}/data", data=data, runas=runas)


def import_shape_from_existing_file(
    item_id: str,
    file_id: str,
    allow_reimport: Optional[bool] = False,
    tag: Optional[str] = None,
    storage_id: Optional[str] = None,
    notification: Optional[str] = None,
    notification_data: Optional[str] = None,
    priority: Optional[str] = None,
    jobmetadata: Optional[list[str]] = None,
    runas: Optional[str] = None,
) -> Response:
    params = dict(
        fileId=file_id,
        allowReimport=allow_reimport,
        tag=tag,
        storageId=storage_id,
        notification=notification,
        notificationData=notification_data,
        priority=priority,
        jobmetadata=jobmetadata,
    )
    return vidispine_request("POST", f"/item/{item_id}/shape", params=params, runas=runas)
