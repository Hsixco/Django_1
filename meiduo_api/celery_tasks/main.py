from celery import Celery

# 配置
import os
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_api.settings'
# 创建app应用
app = Celery('meiduo')
# 导入celery配置
app.config_from_object('celery_tasks.config')
# 自动注册celery任务
app.autodiscover_tasks(
    ['celery_tasks.sms',
     'celery_tasks.email',
     ]
)