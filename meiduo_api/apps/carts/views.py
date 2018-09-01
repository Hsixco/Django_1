from rest_framework.response import Response
from .serializers import CartSerializer, CartSKUSerializer, CartDeleteSerializer, CartSelectAllSerializer
from rest_framework.views import APIView
from utils import sw_json
from . import constants
from goods.models import SKU
from rest_framework import serializers
from rest_framework import status
from django_redis import get_redis_connection


class CartView(APIView):
    def perform_authentication(self, request):
        # 取消dispatch()前的身份验证
        pass

    def post(self, request):
        # 进行反序列化，验证
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取验证后的数据
        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')

        # 进行身份验证
        try:
            user = request.user
        except:
            user = None

        response = Response(serializer.validated_data)

        if user is None:
            # 未登录
            # 读取购物车中的数据
            cart = request.COOKIES.get('cart')
            if cart:
                cart_dict = sw_json.loads(cart)
            else:
                cart_dict = {}
            # 判断购物车中是否有此商品
            if sku_id in cart_dict:
                # 将数量相加
                count_cart = cart_dict.get(sku_id).get('count')
                cart_dict[sku_id]['count'] = count + count_cart
            else:
                # 添加商品
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': True
                }
            cart_str = sw_json.dumps(cart_dict)
            response.set_cookie('cart', cart_str, max_age=constants.CART_COOKIE_EXPIRES)
        else:
            # 登录则向Redis中存数据
            redis_cli = get_redis_connection('cart')
            redis_cli.hincrby('cart%d' % user.id, sku_id, count)

        return response

    def get(self, request):
        try:
            user = request.user
        except:
            user = None

        if user is None:
            cart = request.COOKIES.get('cart')
            if cart:
                cart_dict = sw_json.loads(cart)
            else:
                cart_dict = {}
        else:
            redis_cli = get_redis_connection('cart')
            cart_redis = redis_cli.hgetall('cart%d' % user.id)
            cart_dict = {}
            '''
            {sku_id:count}===>
            {
                sku_id:{
                    count:***
                }
            }
            '''
            for sku_id in cart_redis:
                cart_dict[int(sku_id)] = {
                    'count': int(cart_redis[sku_id])
                }
            cart_selected = redis_cli.smembers('cart_selected%d' % user.id)
            cart_selected = [int(sku_id) for sku_id in cart_selected]
            for sku_id in cart_dict:
                if sku_id in cart_selected:
                    cart_dict[sku_id]['selected'] = True
                else:
                    cart_dict[sku_id]['selected'] = False

        skus = SKU.objects.filter(id__in=cart_dict.keys())
        for sku in skus:
            sku_dict = cart_dict.get(sku.id)
            sku.count = sku_dict.get('count')
            sku.selected = sku_dict.get('selected')

        serializer = CartSKUSerializer(skus, many=True)

        return Response(serializer.data)

    def put(self, request):
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sku_id = serializer.validated_data.get('sku_id')
        count = serializer.validated_data.get('count')
        selected = serializer.validated_data.get('selected')

        response = Response(serializer.validated_data)

        try:
            user = request.user
        except:
            user = None

        if user is None:
            cart = request.COOKIES.get('cart')
            if not cart:
                raise serializers.ValidationError('购物车为空')

            cart_dict = sw_json.loads(cart)
            if sku_id in cart_dict:
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected
                }
            cart_str = sw_json.dumps(cart_dict)
            response.set_cookie('cart', cart_str, max_age=constants.CART_COOKIE_EXPIRES)
        else:
            redis_cli = get_redis_connection('cart')
            redis_cli.hset('cart%d' % user.id, sku_id, count)
            if selected:
                redis_cli.sadd('cart_selected%d' % user.id, sku_id)
            else:
                redis_cli.srem('cart_selected%d' % user.id, sku_id)

        return response

    def delete(self, request):
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data.get('sku_id')

        try:
            user = request.user
        except:
            user = None

        response = Response(status=status.HTTP_204_NO_CONTENT)

        if user is None:
            cart = request.COOKIES.get('cart')
            if not cart:
                raise serializers.ValidationError('购物车无数据，不需要删除')
            cart_dict = sw_json.loads(cart)
            if sku_id in cart_dict:
                del cart_dict[sku_id]
            cart_str = sw_json.dumps(cart_dict)
            response.set_cookie('cart', cart_str, max_age=constants.CART_COOKIE_EXPIRES)
        else:
            redis_cli = get_redis_connection('cart')
            pl = redis_cli.pipeline()
            pl.hdel('cart%d' % user.id,sku_id)
            pl.srem('cart_selected%d'% user.id,sku_id)
            pl.execute()

        return response


class CartSelectAllView(APIView):
    def perform_authentication(self, request):
        pass

    def put(self, request):
        serializer = CartSelectAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = serializer.validated_data.get('selected')

        try:
            user = request.user
        except:
            user = None

        response = Response({'message': 'OK'})

        if user is None:
            cart = request.COOKIES.get('cart')
            if not cart:
                raise serializers.ValidationError('暂无购物车数据')
            cart_dict = sw_json.loads(cart)
            for sku_id in cart_dict:
                cart_dict[sku_id]['selected'] = selected
            cart_str = sw_json.dumps(cart_dict)
            response.set_cookie('cart', cart_str, max_age=constants.CART_COOKIE_EXPIRES)
        else:
            redis_cli = get_redis_connection('cart')
            sku_ids = redis_cli.hkeys('cart%d' % user.id)
            if selected:
                redis_cli.sadd('cart_selected%d' % user.id, sku_ids)
            else:
                redis_cli.srem('cart_selected%d' % user.id, sku_ids)

        return response
