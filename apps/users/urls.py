from django.urls import path
from apps.users.views.profile import UserProfileViewSet

urlpatterns = [
    path('me/', UserProfileViewSet.as_view({'get': 'me'}), name='user-me'),
]
