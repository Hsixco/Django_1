from django_redis import get_redis_connection
from goods.serializers import SKU
from carts.serializers import CartSKUSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import CreateAPIView
from .serializers import OrderSaveSerializer

class OrderSettlementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self,request):
        # 连接redis
        redis_cli = get_redis_connection('cart')
        # 获取商品信息
        cart_dict = redis_cli.hgetall('cart%d' % request.user.id)
        cart_dict2 = {}
        for k,v in cart_dict.items():
            cart_dict2[int(k)] = int(v)
        #获取选中的商品
        cart_selected = redis_cli.smembers('cart_selected%d' % request.user.id)
        # 查询商品对象
        skus = SKU.objects.filter(pk__in=cart_selected)
        for sku in skus:
            sku.count = cart_dict2.get(sku.id)
            sku.selected = True
        serializer = CartSKUSerializer(skus,many=True)
        result = {
            'skus':serializer.data,
            'freight':10
        }
        return Response(result)


class OrderSaveView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSaveSerializer
