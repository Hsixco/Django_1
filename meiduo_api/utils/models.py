from django.db import models


class BaseModel(models.Model):
    # 为模型类补充字段
    create_time = models.DateTimeField(auto_now_add=True,verbose_name = '创建时间')
    update_time = models.DateTimeField(auto_now = True,verbose_name = '更新时间')

    class Meta:
        # 抽象，用于继承，迁移数据库是不会创建表
        abstract = True