from rest_framework import serializers
from goods.models import SKU


class CartSerializer(serializers.Serializer):
    sku_id = serializers.IntegerField(min_value=1)
    count = serializers.IntegerField(min_value=1)
    selected = serializers.BooleanField(default=True)

    def validate_sku_id(self, value):
        try:
            sku = SKU.objects.get(pk=value)
        except:
            raise serializers.ValidationError('商品编号无效')
        return value


class CartSKUSerializer(serializers.ModelSerializer):
    count = serializers.IntegerField()
    selected = serializers.BooleanField()

    class Meta:
        model = SKU
        fields = ['id', 'name', 'price', 'default_image_url', 'count', 'selected']


class CartDeleteSerializer(serializers.Serializer):
    sku_id = serializers.IntegerField(min_value=1)

    def validate_sku_id(self, value):
        try:
            SKU.objects.get(pk=value)
        except:
            raise serializers.ValidationError('商品编号无效')
        return value


class CartSelectAllSerializer(serializers.Serializer):
    selected = serializers.BooleanField()
