from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryListView, DashboardSummaryView, RecentTransactionsView, TransactionViewSet

router = DefaultRouter()
router.register("transactions", TransactionViewSet, basename="transaction")

urlpatterns = [
    # Must come before the router's include so "recent" isn't swallowed by
    # the transactions/<pk>/ detail route.
    path("transactions/recent/", RecentTransactionsView.as_view(), name="transactions-recent"),
    path("categories/", CategoryListView.as_view(), name="categories-list"),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("", include(router.urls)),
]
