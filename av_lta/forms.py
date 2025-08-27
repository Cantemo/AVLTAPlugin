import json

from django import forms
from django.utils.safestring import SafeString
from django.utils.translation import gettext as _
from portal.externals.VidiRest.objects.storage import VSStorage
from portal.vidispine.istorage import StorageHelper


class SettingsForm(forms.Form):
    AV_LTA_APPS_URL = forms.CharField(
        label=_("LTA Apps URL"), help_text=_("URL to the LTA deployment to proxy to"), required=False
    )
    AV_LTA_PUBLISH_SHAPE_TAG = forms.CharField(
        label=_("Publish shape tag"),
        help_text=_("Shape tag to use when creating a new shape when publishing a subtitle"),
        required=False,
    )
    AV_LTA_FORCE_FULL_DOMAIN = forms.BooleanField(
        label=_("Use full domain"),
        help_text=_("Enable to use full absolute urls in the launch template"),
        required=False,
    )
    AV_LTA_EXTRA_SETTINGS = forms.CharField(
        label=_("Launch template settings"),
        help_text=SafeString(
            _(
                "Settings to always include in each Launch Template. Must be valid a valid JSON object. Read more about the available settings <a href='https://apps.accurate.video/docs/validate/reference/launch-template-settings' target='blank'>here</a>"
            )
        ),
        required=False,
        widget=forms.Textarea,
    )
    AV_LTA_TARGET_STORAGE_ID = forms.ChoiceField(
        choices=[("VX-1", "VX-1")],
        label=_("Target storage ID"),
        help_text=_(
            "ID of the storage to use when storing subtitle files. Defaults to the first storage of the origin file if not set."
        ),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.base_fields["AV_LTA_TARGET_STORAGE_ID"].choices = self.get_storage_choices()
        super().__init__(*args, **kwargs)

    def get_storage_choices(self) -> list[tuple[str, str]]:
        storage_helper = StorageHelper()
        storages: list[VSStorage] = storage_helper.getAllStorages()
        return [("", _("Default"))] + list((storage.getId(), storage.getId()) for storage in storages)

    def clean_AV_LTA_APPS_URL(self):
        url = self.cleaned_data.get("AV_LTA_APPS_URL")
        if url and not url.endswith("/"):
            url += "/"
        return url

    def clean_AV_LTA_EXTRA_SETTINGS(self):
        data = self.cleaned_data["AV_LTA_EXTRA_SETTINGS"]
        if not data:
            return data
        try:
            json.loads(data)
        except ValueError:
            raise forms.ValidationError("Invalid JSON")
        return data
