from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import UpdateAPIView
from rest_framework import status

from .serializers import UserCreateSerializer
from .serializers import UserDetailSerializer
from .models import User
from .serializers import EmailSerializer
from rest_framework.mixins import CreateModelMixin,UpdateModelMixin
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.views import ObtainJSONWebToken

from . import constants
from . import serializers
from .serializers import UserAddressSerializer
from rest_framework.permissions import IsAuthenticated
from .serializers import AddUserBrowsingHistorySerializer

from goods.serializers import SKUSerializer
from django_redis import get_redis_connection
from goods.models import SKU
from carts.utils import merge_cart_cookie2redis



class UsernameCountView(APIView):
    def get(self, request, username):
        # 统计用户名个数
        count = User.objects.filter(username=username).count()

        return Response({
            'username': username,
            'count': count
        })


class MobileCountView(APIView):
    def get(self, request, mobile):
        # 统计手机号是否存在
        count = User.objects.filter(mobile=mobile).count()

        return Response({
            'mobile': mobile,
            'count': count
        })


class UserView(CreateAPIView):  # GenericAPIView,CreateModelMxin
    '''
    完成用户的注册
    '''
    serializer_class = UserCreateSerializer


class UserDetailView(RetrieveAPIView):  # RetriveModelMixin,GenericAPIView
    """
    用户详情
    """
    serializer_class = UserDetailSerializer
    # 要求登录后才能访问，指定权限认证
    permission_classes = [IsAuthenticated]

    # 当前不需要根据pk查询对象，而是获取登录的用户对象
    def get_object(self):
        # 当jwt完成登录验证后，会将对象保存到request对象中
        return self.request.user


class EmailView(UpdateAPIView):
    """
    保存用户邮箱
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EmailSerializer

    def get_object(self, *args, **kwargs):
        return self.request.user


class VerifyEmailView(APIView):
    """
    邮箱验证
    """

    def get(self, request):
        # 获取token
        token = request.query_params.get('token')
        if not token:
            return Response({'message': '缺少token'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证token
        user = User.check_verify_email_token(token)
        if user is None:
            return Response({'message': '链接信息无效'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user.email_active = True
            user.save()
            return Response({'message': 'OK'})


class AddressViewSet(CreateModelMixin, UpdateModelMixin, GenericViewSet):
    """
    用户地址新增与修改
    """
    serializer_class = serializers.UserAddressSerializer
    permissions = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    # GET /addresses/
    def list(self, request, *args, **kwargs):
        """
        用户地址列表数据
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data,
        })

    # POST /addresses/
    def create(self, request, *args, **kwargs):
        """
        保存用户地址数据
        """
        # 检查用户地址数据数目不能超过上限
        count = request.user.addresses.count()
        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({'message': '保存地址数据已达到上限'}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request, *args, **kwargs)

    # delete /addresses/<pk>/
    def destroy(self, request, *args, **kwargs):
        """
        处理删除
        """
        address = self.get_object()

        # 进行逻辑删除
        address.is_deleted = True
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    # put /addresses/pk/status/
    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """
        设置默认地址
        """
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)

    # put /addresses/pk/title/
    # 需要请求体参数 title
    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """
        修改标题
        """
        address = self.get_object()
        serializer = serializers.AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class UserBrowsingHistoryView(CreateAPIView):
    """
    用户浏览历史记录
    """
    serializer_class = AddUserBrowsingHistorySerializer
    permission_classes = [IsAuthenticated]

    def get(self,request):
        user_id = request.user.id
        redis_cli = get_redis_connection('history')
        sku_ids = redis_cli.lrange('history_%s' % user_id,0,-1)
        # 查询
        sku = []
        for sku_id in sku_ids:
            sku.append(SKU.objects.get(pk=sku_id))
        sku_serilaizer = SKUSerializer(sku,many=True)
        return Response(sku_serilaizer.data)


class UserAuthorizeView(ObtainJSONWebToken):
    def post(self, request, *args, **kwargs):
        response = super().post(request,*args,**kwargs)
        # 进行登录验证，
        if 'user_id' not in response.data:
            # 登录失败
            return response
        # 登录成功，进行合并
        user_id = response.data.get('user_id')
        response = merge_cart_cookie2redis(request,response,user_id)
        return response

