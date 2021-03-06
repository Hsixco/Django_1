from rest_framework import serializers
from .models import OrderInfo, OrderGoods
from datetime import datetime
from django_redis import get_redis_connection
from goods.models import SKU
from django.db import transaction

class OrderSaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderInfo
        fields = ['order_id', 'address', 'pay_method']
        # 只读，表示只用于输出
        read_only_fields = ['order_id']
        # 对现有字段进行有效性验证
        extra_kwargs = {
            'address': {
                # 只写，表示只用于输入，接收客户端的值
                'write_only': True,
                # 必须传递此值
                'required': True
            },
            'pay_method': {
                'write_only': True,
                'required': True
            }
        }

    def create(self, validated_data):
        # 涉及到的表：tb_order_info,tb_order_goods,tb_goods,tb_sku
        user = self.context['request'].user
        with transaction.atomic():
            #开启事务
            sid=transaction.savepoint()
            # 1.创建OrderInfo对象
            order = OrderInfo()
            order.order_id = datetime.now().strftime('%Y%m%d%H%M%S') + '%09d' % user.id
            order.user = user
            order.address = validated_data.get('address')
            order.total_count = 0
            order.total_amount = 0
            order.freight = 10
            order.pay_method = validated_data.get('pay_method')
            if validated_data.get('pay_method') == 1:  # 货到付款
                order.status = 2  # 状态为待发货
            else:
                order.status = 1  # 使用其它支付方式，则状态为待付款
            order.save()
            # 2.查询redis中所有选中的商品
            redis_cli = get_redis_connection('cart')
            #查询商品及数量
            cart_hash = redis_cli.hgetall('cart%d' % user.id)
            cart_dict = {int(k): int(v) for k, v in cart_hash.items()}
            #查询选中的商品
            cart_set = redis_cli.smembers('cart_selected%d' % user.id)
            cart_selected = [int(sku_id) for sku_id in cart_set]
            # 3.遍历
            skus = SKU.objects.filter(pk__in=cart_selected)
            total_count = 0
            total_amount = 0
            for sku in skus:
                # 3.1判断库存是否足够,库存不够则抛异常
                count = cart_dict.get(sku.id)  # 购买数量
                if sku.stock < count:
                    #回滚事务
                    transaction.savepoint_rollback(sid)
                    raise serializers.ValidationError('库存不足')

                # 3.2修改商品的库存、销量

                new_stock = sku.stock - count
                new_sales = sku.sales + count
                ret = SKU.objects.filter(id=sku.id, stock=new_stock).update(stock=new_sales, sales=new_sales)
                if ret == 0:
                    continue
                # 3.3修改SPU的总销量
                goods = sku.goods  # 获取当前sku对应的spu
                goods.sales += count
                goods.save()

                # 3.4创建OrderGoods对象
                OrderGoods.objects.create(
                    order = order,
                    sku = sku,
                    count = count,
                    price = sku.price

                )


                # 3.5计算总金额、总数量
                total_count += count
                total_amount += count * sku.price

            # 4.修改总金额、总数量
            order.total_count = total_count
            order.total_amount = total_amount
            order.save()
            #提交事务
            transaction.savepoint_commit(sid)

        # 5.删除redis中选中的商品数据
        pl = redis_cli.pipeline()
        pl.hdel('cart%d' % user.id, *cart_selected)
        pl.srem('cart_selected%d' % user.id, *cart_selected)
        pl.execute()

        return order
