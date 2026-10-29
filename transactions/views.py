from decimal import Decimal

from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from rest_framework import generics, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import TransactionFilter
from .models import Category, Transaction, TransactionType
from .serializers import CategorySerializer, TransactionSerializer

ZERO = Decimal("0.00")


def _money():
    return Coalesce(Sum("amount"), ZERO, output_field=DecimalField(max_digits=12, decimal_places=2))


class CategoryListView(generics.ListAPIView):
    """GET /api/categories/ — list all categories, optionally ?type=income|expense."""

    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    filterset_fields = ["type"]
    pagination_class = None


class TransactionViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for the authenticated user's own transactions.

    GET    /api/transactions/
    POST   /api/transactions/
    GET    /api/transactions/<id>/
    PUT    /api/transactions/<id>/
    PATCH  /api/transactions/<id>/
    DELETE /api/transactions/<id>/
    """

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = TransactionFilter
    search_fields = ["description"]
    ordering_fields = ["date", "amount", "created_at"]

    def get_queryset(self):
        # A user can only ever see/act on their own transactions.
        return (
            Transaction.objects.filter(user=self.request.user)
            .select_related("category")
        )


class RecentTransactionsView(generics.ListAPIView):
    """GET /api/transactions/recent/ — the user's most recent transactions (unpaginated, capped)."""

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        try:
            limit = int(self.request.query_params.get("limit", 5))
        except (TypeError, ValueError):
            limit = 5
        limit = max(1, min(limit, 50))
        return (
            Transaction.objects.filter(user=self.request.user)
            .select_related("category")
            .order_by("-date", "-created_at")[:limit]
        )


class DashboardSummaryView(APIView):
    """
    GET /api/dashboard/summary/

    Returns the authenticated user's financial summary, calculated
    entirely on the backend.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Transaction.objects.filter(user=request.user)

        total_income = qs.filter(type=TransactionType.INCOME).aggregate(total=_money())["total"]
        total_expenses = qs.filter(type=TransactionType.EXPENSE).aggregate(total=_money())["total"]
        balance = total_income - total_expenses

        expenses_by_category = list(
            qs.filter(type=TransactionType.EXPENSE)
            .values("category__id", "category__name")
            .annotate(total=_money())
            .order_by("-total")
        )
        income_by_category = list(
            qs.filter(type=TransactionType.INCOME)
            .values("category__id", "category__name")
            .annotate(total=_money())
            .order_by("-total")
        )

        def _format(rows):
            return [
                {"category_id": r["category__id"], "category": r["category__name"], "total": r["total"]}
                for r in rows
            ]

        return Response(
            {
                "total_income": total_income,
                "total_expenses": total_expenses,
                "balance": balance,
                "transaction_count": qs.count(),
                "expenses_by_category": _format(expenses_by_category),
                "income_by_category": _format(income_by_category),
            }
        )
