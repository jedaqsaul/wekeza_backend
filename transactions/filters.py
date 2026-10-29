import django_filters

from .models import Transaction, TransactionType


class TransactionFilter(django_filters.FilterSet):
    type = django_filters.ChoiceFilter(choices=TransactionType.choices)
    category = django_filters.NumberFilter(field_name="category_id")
    date = django_filters.DateFilter(field_name="date")
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Transaction
        fields = ["type", "category", "date", "date_from", "date_to"]
