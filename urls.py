import logging

from django.urls import re_path
from . import views

log = logging.getLogger(__name__)

urlpatterns = [
    re_path(r'^get_launch_template$', views.LaunchTemplateView.as_view(), name='get_launch_template'),
    re_path('^open$', views.OpenApplicationView.as_view(), name='open'),
]
