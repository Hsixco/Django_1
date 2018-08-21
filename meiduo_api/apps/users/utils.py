from django.contrib.auth.backends import ModelBackend
from .models import User

def jwt_response_payload_handler(token,user=None,request=None):
    return {
        'token':token,
        'user_id':user.id,
        'username':user.username
    }


class UsernameMobileModelBackend(ModelBackend):
    def authenticate(self,request=None,username = None,password = None,**kwargs):
        try:
            # 如果是手机号，与mobile属性对比
            user = User.objects.get(mobile = username)
        except:
            try:
                # 如果是用户名与username对比
                user = User.objects.get(username = username)
            except:
                return None
        # 如果查询到用户对象，则判断密码是否正确
        if user.check_password(password):
            return user
        else:
            return None