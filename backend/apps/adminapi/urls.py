from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register("attempts", views.AttemptViewSet, basename="admin-attempts")
router.register("branches", views.BranchViewSet, basename="admin-branches")
router.register("subjects", views.SubjectViewSet, basename="admin-subjects")
router.register("questions", views.QuestionViewSet, basename="admin-questions")

urlpatterns = [
    path("auth/csrf/", views.CsrfView.as_view()),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("dashboard/", views.DashboardView.as_view()),
    path("settings/", views.SettingsView.as_view()),
    path("", include(router.urls)),
]
