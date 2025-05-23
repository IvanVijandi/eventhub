from django.contrib.auth.views import LogoutView
from django.contrib import admin
from django.urls import path
from django.contrib import admin
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("accounts/register/", views.register, name="register"),
    path("accounts/logout/", LogoutView.as_view(), name="logout"),
    path("accounts/login/", views.login_view, name="login"),
    path("events/", views.events, name="events"),
    path("events/create/", views.event_form, name="event_form"),
    path("events/<int:id>/buy-ticket/", views.buy_ticket, name="buy_ticket"),
    path("tickets/", views.tickets, name="tickets"),
    path("tickets/<int:id>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:id>/delete/", views.ticket_delete, name="ticket_delete"),
    path("tickets/<int:id>/edit/", views.ticket_edit, name="ticket_edit"),
    path("events/<int:event_id>/edit/", views.event_form, name="event_edit"),
    path("events/<int:event_id>/", views.event_detail, name="event_detail"),
    path("events/<int:event_id>/delete/", views.event_delete, name="event_delete"),
    path("events/<int:event_id>/ratings/create/", views.create_rating, name="create_rating"),
    path("ratings/<int:rating_id>/edit/", views.edit_rating, name="edit_rating"),
    path("ratings/<int:rating_id>/delete/", views.delete_rating, name="delete_rating"),
    path("events/<int:event_id>/comment/", views.add_comment, name="add_comment"),
    path("events/<int:event_id>/comment/<int:comment_id>/delete/", views.delete_comment, name="delete_comment"),
    path("events/<int:event_id>/comment/<int:comment_id>/update/", views.update_comment, name="update_comment"),
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/create/", views.notification_create, name="notification_create"),
    path("notifications/<int:notification_id>/edit/", views.notification_edit, name="notification_edit"),
    path("notifications/<int:notification_id>/", views.notification_detail, name="notification_detail"),
    path("notifications/<int:notification_id>/delete/", views.notification_delete, name="notification_delete"),
    path("notifications/<int:notification_id>/read/", views.notification_mark_read, name="notification_mark_read"),
    path('notifications/mark_all_read/', views.mark_all_notifications_read, name='notification_mark_all_read'),

    # Categories
    path("categories/", views.categories, name="categories"),
    path("categories/create/", views.category_form, name="category_form"),
    path("categories/<int:category_id>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:category_id>/delete/", views.category_delete, name="category_delete"),

    # Refund Requests
    path("tickets/<int:id>/refund/", views.refund_form, name="refund_form"),
    path("refund/organizer/", views.organizer_refund_requests, name="organizer_refund"),
    path("refund/organizer/<int:id>/edit/", views.refund_edit_form, name="refund_edit_form"),
    path("refund/approve/<int:id>/", views.approve_refund_request, name="refund_approve"),
    path("refund/reject/<int:id>/", views.reject_refund_request, name="refund_reject"),
    path("refund/<int:id>/delete", views.refund_delete, name="refund_delete"),
    path("refund/view/<int:id>/", views.view_refund_request, name="refund_view"),

    # Venues
    path("venues/", views.venues, name="venues"),
    path("venues/create/", views.venue_form, name="venue_form"),
    path("venues/<int:id>/delete/", views.venue_delete, name="venue_delete"),
    path("venues/<int:id>/edit/", views.venue_edit, name="venue_edit"),
]
