from django.urls import path

from . import views

urlpatterns = [
    path("public/meta/", views.MetaView.as_view(), name="public-meta"),
    path("attempts/", views.StartAttemptView.as_view(), name="attempt-start"),
    path("attempts/<uuid:attempt_id>/", views.AttemptStateView.as_view(), name="attempt-state"),
    path("attempts/<uuid:attempt_id>/answers/", views.SaveAnswersView.as_view(), name="attempt-answers"),
    path("attempts/<uuid:attempt_id>/stages/<int:stage>/start/", views.StartStageView.as_view(), name="stage-start"),
    path("attempts/<uuid:attempt_id>/stages/<int:stage>/finish/", views.FinishStageView.as_view(),
         name="stage-finish"),
]
