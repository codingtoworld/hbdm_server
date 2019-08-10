# -*- coding: utf-8 -*-

import json
import requests
import decimal
import math
import os
import time
try:
    from urllib.parse import urlparse
    from urllib.parse import urlencode
except ImportError:
    from urlparse import urlparse
    from urllib import urlencode


def http_get_request(url, params=None, add_to_headers=None):
    headers = {
        "Accept": "application/json",
        # 'Content-Type': 'application/json',
        'Accept-Language': 'zh-cn',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71',
    }
    if add_to_headers:
        headers.update(add_to_headers)
    if params is not None:
        postdata = urlencode(params)
        url = url + "&" + postdata if url.find('?') >= 0 else url + "?" + postdata

    try:
        sess_req = requests.Session()
        response = sess_req.get(url, headers=headers, timeout=30)
        # response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print("%s\r\n%s" % (url, response.content))
            return False
    except BaseException as e:
        print("httpGet failed, detail is:%s" % str(e))
        return False


def http_post_request(url, params=None, add_to_headers=None):
    headers = {
        "Accept": "application/json",
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71',
    }
    if add_to_headers:
        headers.update(add_to_headers)
    postdata = None
    if params is not None:
        postdata = json.dumps(params)

    try:
        response = requests.post(url, postdata, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print("%s\r\n%s" % (url, response.content))
            return False
    except BaseException as e:
        print("httpPost failed, detail is: %s" % str(e))
        return


def set_price(price, _type=10.0):
    ps = price.split('.')
    ln = len(ps[1])
    ctx = decimal.Context()
    ctx.prec = ln
    num = math.pow(10, ln)
    offset = _type/num
    price = float(price) + offset
    d2 = ctx.create_decimal(repr(price))
    return '{:.{prec}f}'.format(d2, prec=ln)


def half_price(high, low):
    rise_price = high - low
    if rise_price == 0:
        return high
    ps = float_to_string(rise_price).split('.')
    ln = len(ps[1])
    num = math.pow(10, ln)
    if (rise_price * num) % 2 != 0:
        rise_price = ((rise_price * num) + 1) / (2 * num)
    else:
        rise_price = rise_price / 2
    f_price = low + rise_price
    return float('{:.{prec}f}'.format(f_price, prec=ln))


def price_percent(price, percent=1.5):
    rise_price = (price * percent) / 100
    f_price = price + rise_price
    return float('{:.{prec}f}'.format(f_price, prec=8))


def float_to_string(number, precision=20):
    return '{0:.{prec}f}'.format(
        number, prec=precision,
    ).rstrip('0').rstrip('.') or '0'


def load_json(json_file):
    curr_date = time.strftime("%Y%m%d", time.localtime())
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    log_path = os.path.join(base_path, 'logs', curr_date)
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    try:
        with open(os.path.join(log_path, json_file)) as f:
            _json = json.loads(f.read())
    except (IOError, ValueError):
        _json = []
    return _json


def save_json(_json, json_file):
    curr_date = time.strftime("%Y%m%d", time.localtime())
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    log_path = os.path.join(base_path, 'logs', curr_date)
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    try:
        with open(os.path.join(log_path, json_file), 'w') as f:
            f.write(json.dumps(_json))
    except (IOError, TypeError):
        pass


def getcfg_quant(symbal):
    """
    获取当前 symbal 策略配置文件JSON内容
    :param symbal:
    :return:
    """
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    quant_file = os.path.join(base_path, 'config', symbal+'.json')
    default_cfg = {
        'trade_status': 0,
        'buy_price': 0,
        'sell_price': 0,
        'stop_price': 0,
        'buy_time': 0,
        'sell_time': 0,
        'quant': ''
    }
    try:
        with open(quant_file) as f:
            _json = json.load(f)
            f.close()
            return _json if 'trade_status' in _json.keys() else default_cfg
    except (IOError, ValueError):
        return default_cfg


def setcfg_quant(symbal, j_quant):
    """
    保存当前 symbal 策略配置文件JSON内容
    :param symbal:
    :param j_quant 当前quant 字典json内容
    :return:
    """
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    quant_file = os.path.join(base_path, 'config', symbal+'.json')
    try:
        with open(quant_file, 'w') as f:
            json.dump(j_quant, f)
            f.close()
    except (IOError, TypeError):
        # print("%s %s" % (str(IOError), str(TypeError)))
        pass


if __name__ == '__main__':
    a = {'trade_status': 1, 'buy_price': 0, 'stop_price': 0}
    b = getcfg_quant('qqq')
    print(b)
    setcfg_quant('bbb', a)
