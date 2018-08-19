from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView,CreateAPIView
from .models import User
from .serializers import UserCreateSerializer
# Create your views here.


class UsernameCountView(APIView):
    def get(self,request,username):
        count = User.objects.filter(user_name = username).count()
        Response({
            'user_name':username,
            'count':count
        })


class MobileCountView(APIView):
    def get(self,request,mobile):
        count = User.objects.filter(mobile = mobile).count()
        Response({
            'mobile':mobile,
            'count':count
        })

class UserCreateView(CreateAPIView):
    # 完成用户的注册
    serializer_class = UserCreateSerializer