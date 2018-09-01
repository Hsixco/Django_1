from django_redis import get_redis_connection
from utils import sw_json


def merge_cart_cookie2redis(request,response,user_id):
    # 读取Cookie
    cart = request.COOKIES.get('cart')
    if not cart:
        return response
    cart_dict = sw_json.loads(cart)

    # 写入Redis
    redis_cli = get_redis_connection('cart')
    pl = redis_cli.pipeline()
    # 遍历字典
    for sku_id,item in cart_dict.items():
        pl.hset('cart%d' % user_id,sku_id,item.get('count'))
        if item.get('selected'):
            pl.sadd('cart_selected%d' % user_id,sku_id)
        else:
            pl.srem('cart_selected%d' % user_id,sku_id)
        pl.execute()

    # 删除Cookie
    response.delete_cookie('cart')
    # 响应
    return response