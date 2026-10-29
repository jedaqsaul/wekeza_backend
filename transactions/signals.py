from django.db.models.signals import post_migrate
from django.dispatch import receiver

DEFAULT_CATEGORIES = {
    "income": ["Salary", "Business", "Freelance", "Investment", "Other"],
    "expense": [
        "Food",
        "Transport",
        "Rent",
        "Utilities",
        "Shopping",
        "Entertainment",
        "Healthcare",
        "Education",
        "Other",
    ],
}


@receiver(post_migrate)
def seed_default_categories(sender, **kwargs):
    # Only run for this app's migrations.
    if sender.name != "transactions":
        return

    from .models import Category

    for category_type, names in DEFAULT_CATEGORIES.items():
        for name in names:
            Category.objects.get_or_create(name=name, type=category_type)
