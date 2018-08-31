import pickle
import base64


def dumps(cart_dict):
    # 将数据序列化为bytes
    cart_bytes = pickle.dumps(cart_dict)
    # 将数据进行base64编码
    cart_64 = base64.b64encode(cart_bytes)
    # 将编码后的数据转换为字符串
    cart_str = cart_64.decode()

    return cart_str


def loads(cart_str):
    # 将字符串解码为bytes
    cart_64 = cart_str.encode()
    # 将bytes进行base64解码
    cart_bytes = base64.b64decode(cart_64)
    # 将解码的bytes转换为dict格式
    cart_dict = pickle.loads(cart_bytes)

    return cart_dict