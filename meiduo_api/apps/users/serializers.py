from rest_framework import serializers
from .models import User
import re
from django_redis import get_redis_connection


class UserCreateSerializer(serializers.Serializer):
    """
    id
    用户名
    手机号
    密码
    确认密码
    短信验证码
    是否同意协议
    """
    # 定义
    # id.编号
    id = serializers.IntegerField(read_only=True)
    # 用户名
    username = serializers.CharField(min_length=5,max_length=20,error_messages={
        'min_length':'用户名不能少于5个字符',
        'max_length':'用户名不能大于20个字符'
    })
    # 手机号
    mobile = serializers.CharField()
    # 密码
    password = serializers.CharField(write_only=True,min_length=8,max_length=20,error_messages={
        'min_length':'密码不能少于8个字符',
        'max_length':'密码不能多于20个字符'
    })
    # 确认密码
    password2 = serializers.CharField(write_only=True, min_length=8, max_length=20, error_messages={
        'min_length': '密码不能少于8个字符',
        'max_length': '密码不能多于20个字符'
    })
    sms_code = serializers.CharField(write_only=True)
    allow = serializers.CharField(write_only=True)

    # 验证
    def validate_username(self,value):
        count = User.objects.filter(username=value).count()
        if  count>0:
            raise serializers.ValidationError('用户名已存在')
        return value

    def valiadte_mobile(self,value):
        # 验证手机号格式
        if not re.match(r'1[3-9]\d{9}$',value):
            raise  serializers.ValidationError('手机号码格式不正确')
        # 判断手机号是否存在
        count = User.objects.filter(mobile=value).count()
        if count>0:
            raise serializers.ValidationError('手机号已被注册')

    def validate_sms_code(self,value):
        # 验证验证码
        if not re.match(r'^\d{6}$',value):
            raise serializers.ValidationError('验证码格式不正确')

    def validate_allow(self,value):
        if not value:
            raise serializers.ValidationError('请同意协议')

    # 验证多个属性
    def validate(self, attrs):
        # 1.验证密码与确认密码
        password = attrs.get('password')
        password2 = attrs.get('password2')
        if password != password2:
            raise serializers.ValidationError('两次输入的密码不一致')
        # 2.验证短信验证码
        # 连接redis数据库
        redis_cli = get_redis_connection('verify_code')
        # 拼接key
        key = 'sms_code_' + attrs.get('mobile')
        # 从redis中根据key查找value
        sms_code_redis = redis_cli.get(key)
        # 获取请求中的验证码
        sms_code_reques = attrs.get('sms_code')
        # 判断验证码是否超过5分钟
        if not sms_code_redis:
            raise serializers.ValidationError('验证码已过期')
        # 强制验证码失效
        redis_cli.delete(key)
        # 将redis中保存的验证码与request中的验证码进行匹配
        if sms_code_redis.decode() != sms_code_reques:
            raise serializers.ValidationError('验证码不正确')

    #     将用户信息添加到数据库
        def create(self,valiate_data):
            # valiate是验证过的数据
            # 创建对象
            user = User()
            # 获取用户名
            user.username = valiate_data.get('username')
            # 将密码加密
            user.set_password(valiate_data.get('password'))
            # 获取手机号
            user.mobile = valiate_data.get('mobile')
            # 将获取到的内容添加到数据库
            user.save()
            # 返回数据
            return user