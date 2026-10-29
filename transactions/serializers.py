from rest_framework import serializers

from .models import Category, Transaction, TransactionType


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "type"]


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "type",
            "amount",
            "category",
            "category_name",
            "description",
            "date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_type(self, value):
        if value not in TransactionType.values:
            raise serializers.ValidationError(
                f"Type must be one of: {', '.join(TransactionType.values)}."
            )
        return value

    def validate(self, attrs):
        # On PATCH, some fields may be missing from attrs — fall back to the
        # existing instance's values so the cross-field check still works.
        category = attrs.get("category", getattr(self.instance, "category", None))
        tx_type = attrs.get("type", getattr(self.instance, "type", None))

        if category and tx_type and category.type != tx_type:
            raise serializers.ValidationError(
                {
                    "category": (
                        f"Category '{category.name}' is an {category.type} category "
                        f"and cannot be used for a {tx_type} transaction."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
