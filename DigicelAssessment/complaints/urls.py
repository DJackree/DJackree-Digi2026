"""Public and staff URL paths for the complaint module.

Customers use ``/complaints/...``; agents use ``/agent/complaints/...``; admins use
``/admin-portal/complaints/...`` so routes do not clash with Django's ``/admin/``.
"""

from django.urls import path

from . import views

app_name = "complaints"

urlpatterns = [
    path("complaints/", views.customer_complaint_list, name="customer_complaint_list"),
    path("complaints/new/", views.customer_complaint_create, name="customer_complaint_create"),
    path(
        "complaints/<str:reference>/",
        views.customer_complaint_detail,
        name="customer_complaint_detail",
    ),
    path("agent/complaints/", views.agent_complaint_queue, name="agent_complaint_queue"),
    path(
        "agent/complaints/<str:reference>/",
        views.agent_complaint_detail,
        name="agent_complaint_detail",
    ),
    path(
        "agent/complaints/<str:reference>/status/",
        views.agent_update_status,
        name="agent_update_status",
    ),
    path(
        "agent/complaints/<str:reference>/notes/",
        views.agent_add_note,
        name="agent_add_note",
    ),
    path(
        "agent/complaints/<str:reference>/escalate/",
        views.agent_escalate,
        name="agent_escalate",
    ),
    path(
        "admin-portal/complaints/",
        views.admin_complaint_list,
        name="admin_complaint_list",
    ),
    path(
        "admin-portal/complaints/<str:reference>/",
        views.admin_complaint_detail,
        name="admin_complaint_detail",
    ),
    path(
        "admin-portal/complaints/<str:reference>/assign/",
        views.admin_assign_complaint,
        name="admin_assign_complaint",
    ),
    path(
        "admin-portal/complaints/<str:reference>/status/",
        views.admin_update_status,
        name="admin_update_status",
    ),
]
