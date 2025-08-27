import json

from django import forms
from django.utils.safestring import SafeString
from django.utils.translation import gettext as _


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
