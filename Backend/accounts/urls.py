from django.urls import path
from .views import (
    RegisterView, RequestAccessView, ProfileView,
    AddressListCreateView, AddressDetailView,
    AgentBuyersListView, AgentBuyerDetailView,
)

urlpatterns = [
    # Auth
    path('register/',       RegisterView.as_view(),      name='register'),
    path('request-access/', RequestAccessView.as_view(), name='request-access'),

    # Buyer profile & addresses
    path('profile/',            ProfileView.as_view(),           name='profile'),
    path('addresses/',          AddressListCreateView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', AddressDetailView.as_view(),     name='address-detail'),

    # Agent
    path('agent/buyers/',          AgentBuyersListView.as_view(),  name='agent-buyers'),
    path('agent/buyers/<int:pk>/', AgentBuyerDetailView.as_view(), name='agent-buyer-detail'),
]