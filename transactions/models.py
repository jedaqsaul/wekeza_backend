from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class TransactionType(models.TextChoices):
    INCOME = "income", "Income"
    EXPENSE = "expense", "Expense"


class Category(models.Model):
    """
    A transaction category, scoped to a type (income/expense) so the same
    label ("Other") can exist independently for each side.

    Categories are global/shared (not per-user) so the app ships with a
    sensible default set, but the model is intentionally simple to extend
    later (e.g. per-user custom categories) without breaking existing data.
    """

    name = models.CharField(max_length=50)
    type = models.CharField(max_length=10, choices=TransactionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["type", "name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "type"], name="unique_category_name_per_type"),
        ]
        indexes = [
            models.Index(fields=["type"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.type})"


class Transaction(models.Model):
    """A single income or expense record belonging to a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    type = models.CharField(max_length=10, choices=TransactionType.choices)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    description = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "type"]),
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.type} - {self.amount} ({self.date})"
