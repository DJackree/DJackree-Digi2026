"""Routes: browser page under ``/chatbot/`` plus POST JSON endpoints used by the page."""

from django.urls import path

from chatbot import views

app_name = "chatbot"

urlpatterns = [
    path("chatbot/", views.chat_home, name="chat_home"),
    path("chatbot/messages/", views.post_message, name="post_message"),
    path("chatbot/sessions/new/", views.new_session, name="new_session"),
]
