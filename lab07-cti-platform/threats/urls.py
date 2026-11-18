from django.urls import path
from . import views
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("search/", views.search, name="search"),
    path("threat/<str:tid>/", views.detail, name="detail"),
    path("vulnerabilities/", views.vulnerabilities, name="vulnerabilities"),
    path("vulnerability/<str:cve>/", views.vuln_detail, name="vuln_detail"),
    path("download/vulnerabilities.md", views.download_vulns, name="download_vulns"),
    path("merged/", views.merged, name="merged"),
    path("download/merged.md", views.download_merged, name="download_merged"),
    path("download/top.md", views.download_top, name="download_top"),
    path("download/search.md", views.download_search, name="download_search"),
    path("download/threat/<str:tid>.md", views.download_threat, name="download_threat"),
]
