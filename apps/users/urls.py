from django.urls import path
from apps.users.views.profile import UserProfileViewSet
from apps.users.views.registration import RegistrationView
from apps.users.views.logout import LogoutView

urlpatterns = [
    path('me/', UserProfileViewSet.as_view({'get': 'me'}), name='user-me'),
    path('register/', RegistrationView.as_view(), name='user-register'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
]
