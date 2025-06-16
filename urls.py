import logging

from django.urls import re_path

from . import views

log = logging.getLogger(__name__)

urlpatterns = [
    re_path(r'^open$', views.OpenApplicationView.as_view(), name='open'),
    re_path(r'^get_launch_template$', views.LaunchTemplateView.as_view(), name='get_launch_template'),
    re_path(r'^publish$', views.SubtitlePublishView.as_view(), name='publish'),
    re_path(r'^apps/(?P<path>.*)?', views.ProxyLTAView.as_view(), name='av_apps'),
]
