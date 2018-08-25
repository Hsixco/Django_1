from rest_framework import serializers
from rest_framework_jwt.settings import api_settings

from .models import User,Address
import re
from django_redis import get_redis_connection
from celery_tasks.email.tasks import send_verify_email


class UserCreateSerializer(serializers.Serializer):
    # 用户编号，只输出
    id = serializers.IntegerField(read_only=True)
    # 用户名
    username = serializers.CharField(
        min_length=5,
        max_length=20,
        error_messages={
            'min_length': '用户名不能少于5个字符',
            'max_length': '用户名不能大于20个字符'
        }
    )
    # 手机号
    mobile = serializers.CharField()
    # 密码
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=20,
        error_messages={
            'min_length': '密码长度不能小于8个字符',
            'max_length': '密码长度不能大于20个字符'
        }
    )
    # 确认密码
    password2 = serializers.CharField(
        write_only=True,
        min_length=8,
        max_length=20,
        error_messages={
            'min_length': '确认密码长度不能小于8个字符',
            'max_length': '确认密码长度不能大于20个字符'
        }
    )
    # 是否同意协议
    allow = serializers.CharField(write_only=True)
    # 短信验证码，只输入
    sms_code = serializers.CharField(write_only=True)

    # 增加代码1：token字段
    token = serializers.CharField(label='登录状态token', read_only=True)

    def validate_username(self, value):
        # 要求用户名中必须包含字母
        if not re.search(r'[a-zA-Z]', value):  # 123a45sdafdsf6
            raise serializers.ValidationError('用户名必须包含字母')
        # 验证用户名是否存在
        count = User.objects.filter(username=value).count()
        if count > 0:
            raise serializers.ValidationError('用户名存在')
        return value

    def validate_mobile(self, value):
        # 验证手机号格式
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        # 判断手机号是否存在
        count = User.objects.filter(mobile=value).count()
        if count > 0:
            raise serializers.ValidationError('手机号存在')
        return value

    def validate_sms_code(self, value):
        if not re.match(r'^\d{6}$', value):
            raise serializers.ValidationError('短信验证码格式错误')
        return value

    def validate_allow(self, value):
        if not value:
            raise serializers.ValidationError('请同意协议')
        return value

    # 验证多个属性
    def validate(self, attrs):
        # 验证两次密码是否一致
        password = attrs.get('password')
        password2 = attrs.get('password2')
        if password != password2:
            raise serializers.ValidationError('两次密码不一致')
        # 判断短信验证码是否正确
        redis_cli = get_redis_connection('verify_code')
        key = 'sms_code_' + attrs.get('mobile')
        sms_code_redis = redis_cli.get(key)
        sms_code_request = attrs.get('sms_code')
        if not sms_code_redis:
            raise serializers.ValidationError('验证码已过期')
        redis_cli.delete(key)  # 强制验证码失效
        if sms_code_redis.decode() != sms_code_request:
            raise serializers.ValidationError('短信验证码错误')

        return attrs

    def create(self, validated_data):
        user = User()
        user.username = validated_data.get('username')
        user.mobile = validated_data.get('mobile')
        user.set_password(validated_data.get('password'))
        user.save()

        # 增加代码2：生成记录登录状态的token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        user.token = token

        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """
    用户详细信息序列化器
    """

    class Meta:
        model = User
        fields = ('id', 'username', 'mobile', 'email', 'email_active')


class EmailSerializer(serializers.ModelSerializer):
    """
    邮箱序列化器
    """

    class Meta:
        model = User
        fields = ('id', 'email')
        extra_kwargs = {
            'email': {
                'required': True
            }
        }

    def update(self, instance, validated_data):
        email = validated_data['email']
        instance.email = validated_data['email']
        instance.save()

        # 生成验证链接
        verify_url = instance.generate_verify_email_url()
        print(verify_url)
        # 发送验证邮件
        send_verify_email.delay(email, verify_url)

        return instance


class UserAddressSerializer(serializers.ModelSerializer):
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label='省id',required=True)
    city_id = serializers.IntegerField(label='市id',required=True)
    district_id = serializers.IntegerField(label='区id',required=True)

    class Meta:
        model = Address
        exclude = ('user','is_deleted','create_time','update_time')

    def validate_mobile(self, value):
        """
        验证手机号
        """
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式错误')
        return value

    def create(self, validated_data):
        """
        保存
        """
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class AddressTitleSerializer(serializers.ModelSerializer):
    """
    地址标题
    """

    class Meta:
        model = Address
        fields = ('title',)