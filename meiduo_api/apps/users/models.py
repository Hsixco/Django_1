from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    # 添加手机号字段
    mobile = models.CharField(max_length=11, verbose_name='手机号')

    class Meta:
        db_table = 'tb_table'  # 表名
        verbose_name = '用户'
        verbose_name_plural = verbose_name
