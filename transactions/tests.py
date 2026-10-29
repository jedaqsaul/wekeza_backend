from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category, Transaction, TransactionType

User = get_user_model()


class TransactionTestBase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="jane@example.com", password="StrongPass123", name="Jane")
        self.other_user = User.objects.create_user(email="bob@example.com", password="StrongPass123", name="Bob")

        self.salary, _ = Category.objects.get_or_create(name="Salary", type=TransactionType.INCOME)
        self.food, _ = Category.objects.get_or_create(name="Food", type=TransactionType.EXPENSE)
        self.transport, _ = Category.objects.get_or_create(name="Transport", type=TransactionType.EXPENSE)

        self.authenticate(self.user)

    def authenticate(self, user):
        login = self.client.post(reverse("auth-login"), {"email": user.email, "password": "StrongPass123"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")


class TransactionCRUDTests(TransactionTestBase):
    def test_create_transaction(self):
        url = reverse("transaction-list")
        payload = {
            "type": "expense",
            "amount": "1500.50",
            "category": self.food.id,
            "description": "Groceries",
            "date": "2026-08-01",
        }
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Transaction.objects.first().user, self.user)

    def test_create_transaction_negative_amount_fails(self):
        url = reverse("transaction-list")
        payload = {"type": "expense", "amount": "-5", "category": self.food.id, "date": "2026-08-01"}
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_transaction_zero_amount_fails(self):
        url = reverse("transaction-list")
        payload = {"type": "expense", "amount": "0", "category": self.food.id, "date": "2026-08-01"}
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_transaction_mismatched_category_type_fails(self):
        url = reverse("transaction-list")
        # income type, but category is an expense category
        payload = {"type": "income", "amount": "100", "category": self.food.id, "date": "2026-08-01"}
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_transaction_invalid_type_fails(self):
        url = reverse("transaction-list")
        payload = {"type": "not-a-type", "amount": "100", "category": self.food.id, "date": "2026-08-01"}
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_transactions(self):
        Transaction.objects.create(
            user=self.user, type=TransactionType.EXPENSE, amount=Decimal("10.00"),
            category=self.food, date=date(2026, 8, 1),
        )
        response = self.client.get(reverse("transaction-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_retrieve_transaction(self):
        tx = Transaction.objects.create(
            user=self.user, type=TransactionType.EXPENSE, amount=Decimal("10.00"),
            category=self.food, date=date(2026, 8, 1),
        )
        response = self.client.get(reverse("transaction-detail", args=[tx.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["amount"]), Decimal("10.00"))

    def test_update_transaction(self):
        tx = Transaction.objects.create(
            user=self.user, type=TransactionType.EXPENSE, amount=Decimal("10.00"),
            category=self.food, date=date(2026, 8, 1),
        )
        response = self.client.patch(reverse("transaction-detail", args=[tx.id]), {"amount": "20.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        tx.refresh_from_db()
        self.assertEqual(tx.amount, Decimal("20.00"))

    def test_delete_transaction(self):
        tx = Transaction.objects.create(
            user=self.user, type=TransactionType.EXPENSE, amount=Decimal("10.00"),
            category=self.food, date=date(2026, 8, 1),
        )
        response = self.client.delete(reverse("transaction-detail", args=[tx.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Transaction.objects.filter(id=tx.id).exists())

    def test_transactions_require_authentication(self):
        self.client.credentials()  # clear auth
        response = self.client.get(reverse("transaction-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TransactionOwnershipTests(TransactionTestBase):
    def test_user_cannot_see_other_users_transactions(self):
        other_tx = Transaction.objects.create(
            user=self.other_user, type=TransactionType.EXPENSE, amount=Decimal("50.00"),
            category=self.food, date=date(2026, 8, 1),
        )
        response = self.client.get(reverse("transaction-list"))
        ids = [t["id"] for t in response.data["results"]]
        self.assertNotIn(other_tx.id, ids)

    def test_user_cannot_retrieve_other_users_transaction(self):
        other_tx = Transaction.objects.create(
            user=self.other_user, type=TransactionType.EXPENSE, amount=Decimal("50.00"),
            category=self.food, date=date(2026, 8, 1),
        )
        response = self.client.get(reverse("transaction-detail", args=[other_tx.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_update_other_users_transaction(self):
        other_tx = Transaction.objects.create(
            user=self.other_user, type=TransactionType.EXPENSE, amount=Decimal("50.00"),
            category=self.food, date=date(2026, 8, 1),
        )
        response = self.client.patch(reverse("transaction-detail", args=[other_tx.id]), {"amount": "999"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_cannot_delete_other_users_transaction(self):
        other_tx = Transaction.objects.create(
            user=self.other_user, type=TransactionType.EXPENSE, amount=Decimal("50.00"),
            category=self.food, date=date(2026, 8, 1),
        )
        response = self.client.delete(reverse("transaction-detail", args=[other_tx.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Transaction.objects.filter(id=other_tx.id).exists())


class TransactionFilteringTests(TransactionTestBase):
    def setUp(self):
        super().setUp()
        Transaction.objects.create(
            user=self.user, type=TransactionType.INCOME, amount=Decimal("5000"),
            category=self.salary, description="August salary", date=date(2026, 8, 1),
        )
        Transaction.objects.create(
            user=self.user, type=TransactionType.EXPENSE, amount=Decimal("200"),
            category=self.food, description="Supermarket run", date=date(2026, 8, 5),
        )
        Transaction.objects.create(
            user=self.user, type=TransactionType.EXPENSE, amount=Decimal("100"),
            category=self.transport, description="Uber rides", date=date(2026, 8, 10),
        )

    def test_filter_by_type(self):
        response = self.client.get(reverse("transaction-list"), {"type": "income"})
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_category(self):
        response = self.client.get(reverse("transaction-list"), {"category": self.food.id})
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_date_range(self):
        response = self.client.get(
            reverse("transaction-list"), {"date_from": "2026-08-04", "date_to": "2026-08-06"}
        )
        self.assertEqual(response.data["count"], 1)

    def test_search_by_description(self):
        response = self.client.get(reverse("transaction-list"), {"search": "Uber"})
        self.assertEqual(response.data["count"], 1)


class DashboardSummaryTests(TransactionTestBase):
    def test_summary_calculations(self):
        Transaction.objects.create(
            user=self.user, type=TransactionType.INCOME, amount=Decimal("5000"),
            category=self.salary, date=date(2026, 8, 1),
        )
        Transaction.objects.create(
            user=self.user, type=TransactionType.EXPENSE, amount=Decimal("200"),
            category=self.food, date=date(2026, 8, 5),
        )
        Transaction.objects.create(
            user=self.user, type=TransactionType.EXPENSE, amount=Decimal("100"),
            category=self.transport, date=date(2026, 8, 10),
        )
        # A transaction belonging to another user must never affect this total.
        Transaction.objects.create(
            user=self.other_user, type=TransactionType.INCOME, amount=Decimal("99999"),
            category=self.salary, date=date(2026, 8, 1),
        )

        response = self.client.get(reverse("dashboard-summary"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data["total_income"]), Decimal("5000.00"))
        self.assertEqual(Decimal(response.data["total_expenses"]), Decimal("300.00"))
        self.assertEqual(Decimal(response.data["balance"]), Decimal("4700.00"))
        self.assertEqual(response.data["transaction_count"], 3)
        self.assertEqual(len(response.data["expenses_by_category"]), 2)

    def test_summary_with_no_transactions_returns_zeroes(self):
        response = self.client.get(reverse("dashboard-summary"))
        self.assertEqual(Decimal(response.data["total_income"]), Decimal("0.00"))
        self.assertEqual(Decimal(response.data["total_expenses"]), Decimal("0.00"))
        self.assertEqual(response.data["transaction_count"], 0)


class RecentTransactionsTests(TransactionTestBase):
    def test_recent_transactions_ordered_and_limited(self):
        for i in range(10):
            Transaction.objects.create(
                user=self.user, type=TransactionType.EXPENSE, amount=Decimal("10.00"),
                category=self.food, date=date(2026, 8, i + 1),
            )
        response = self.client.get(reverse("transactions-recent"), {"limit": 3})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        # Most recent date first
        self.assertEqual(response.data[0]["date"], "2026-08-10")
