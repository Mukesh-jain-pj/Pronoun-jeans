from django.urls import path
from .views import (
    CartDetailView, CartItemUpdateView, CartItemDetailView,
    CheckoutView, OrderHistoryView,
    AgentCommissionsListView, AgentLedgerSummaryView,
)

urlpatterns = [
    # Cart
    path('cart/',              CartDetailView.as_view(),      name='cart-detail'),
    path('cart/update/',       CartItemUpdateView.as_view(),  name='cart-item-update'),
    path('cart/items/<int:pk>/', CartItemDetailView.as_view(), name='cart-item-detail'),

    # Checkout & history
    path('checkout/', CheckoutView.as_view(),    name='checkout'),
    path('history/',  OrderHistoryView.as_view(), name='order-history'),

    # Agent
    path('agent/commissions/', AgentCommissionsListView.as_view(), name='agent-commissions'),
    path('agent/ledger/',      AgentLedgerSummaryView.as_view(),   name='agent-ledger'),
]