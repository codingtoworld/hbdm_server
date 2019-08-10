#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import math
import time
import threading
from sys import argv
from zope.interface import Interface, Attribute, implementer
from twisted.python.components import registerAdapter
from twisted.internet import reactor
from twisted.web.server import Site, Session, NOT_DONE_YET
from twisted.web.static import File
from twisted.web.resource import Resource
from twisted.internet import ssl
from OpenSSL import crypto
from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol
from autobahn.twisted.resource import WebSocketResource
from config import *
from utils.googleCode import Google_Verify_Result
from utils.daemon import Daemon


class EchoServerProtocol(WebSocketServerProtocol):
    path = None
    host = None

    def onOpen(self):
        self.factory.register(self)

    def onConnect(self, request):
        _path = request.path
        self.path = _path[1:] if _path.startswith('/') else _path  # BTCUSDT
        self.host = request.host

    def onMessage(self, payload, isBinary):
        if not isBinary:
            # msg = "Echo - {}".format(payload.decode('utf8'))
            if self.host == '127.0.0.1':    # 内部客户端发送的，转发给其他所有客户端
                self.factory.broadcast(payload)
            # self.sendMessage(msg.encode('utf8'))

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)


class EchoServerFactory(WebSocketServerFactory):

    """
    Simple broadcast server broadcasting any message it receives to all
    currently connected clients.
    """

    def __init__(self):
        WebSocketServerFactory.__init__(self, None)
        self.clients = []

    def register(self, client):
        if client not in self.clients:
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            self.clients.remove(client)

    def broadcast(self, msg):
        # print("broadcasting message '{}' ..".format(msg))
        oMsg = json.loads(msg)
        if 'symbol' in oMsg:
            for c in self.clients:
                if c.path == 'wss' and c.host != '127.0.0.1':
                    c.sendMessage(msg)


class SignInPage(Resource):
    isLeaf = True

    def render_GET(self, request):
        session = request.getSession()
        sess = ISession(session)
        tpl = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'htdocs', 'login.html')
        str = open(tpl, 'r').read()
        return str.encode('utf-8')

    def render_POST(self, request):
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        email = request.args[b"username"][0].decode('utf-8')
        gcode = request.args[b"authcode"][0].decode('utf-8')
        if email in USERS_CONFIG:
            google_secret = USERS_CONFIG[email]['GOOGLE_CODE']
            if Google_Verify_Result(google_secret, gcode):
                data = {'code': 200, 'status': 'success'}
                session = request.getSession()
                # print(session.uid)
                sess = ISession(session)
                sess.username = email
            else:
                data = {'code': 400, 'status': 'error'}
        else:
            data = {'code': 404, 'status': 'error'}
        return json.dumps(data).encode('utf-8')


class SignOutPage(Resource):
    isLeaf = True

    def render_GET(self, request):
        request.getSession().expire()
        request.redirect("/")
        request.finish()
        return NOT_DONE_YET


class SymbolPage(Resource):
    isLeaf = True

    def render_GET(self, request):
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        d = MARKETS.keys()
        symbols = []
        for _symbol in d:
            symbols.insert(0, {'symbol': _symbol})
        return json.dumps(symbols).encode('utf-8')


class SetLostPage(Resource):
    isLeaf = True

    def render_GET(self, request):
        global thd_datas, thd_mutex
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        session = request.getSession()
        sess = ISession(session)
        log = {'user': None, 'code': 404}
        if sess.username != '':
            auto_close = request.args[b"auto_close"][0].decode('utf-8')     # 自动平仓开关
            log = {'user': sess.username, 'code': 200, 'auto_close': auto_close}
            stop_price = request.args[b"stop_price"][0].decode('utf-8')  # 设置止损部位价格
            _symbol = request.args[b"symbol"][0].decode('utf-8')  # 交易品种 BTC
            _period = request.args[b"period"][0].decode('utf-8')
            sym = "%s_%s" % (_symbol, _period)
            updater = {
                sym: {
                    'auto_close': int(auto_close),
                    'stop_price': float(stop_price)
                }
            }
            thd_mutex.acquire()     # 上锁
            if sess.username in thd_datas:
                if sym in thd_datas[sess.username]:
                    thd_datas[sess.username][sym].update(updater[sym])
                else:
                    thd_datas[sess.username].update(updater)
            else:
                thd_datas[sess.username] = updater.copy()
            thd_mutex.release()

        return json.dumps(log).encode('utf-8')


class LogCheckPage(Resource):
    isLeaf = True

    def render_GET(self, request):
        global thd_datas
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        session = request.getSession()
        sess = ISession(session)
        log = {'user': None, 'code': 404}
        if sess.username != '':
            log = {'user': sess.username, 'code': 200}

            api_key = USERS_CONFIG[sess.username]['API_KEY']
            api_sec = USERS_CONFIG[sess.username]['SECRET_KEY']
            from api.HuobiDMService import HuobiDM
            api = HuobiDM(API_URL, api_key, api_sec)

            cpi = api.get_contract_position_info()  # 获取当前的合约单
            rates = []
            if cpi['status'] == 'ok':
                for c in cpi['data']:       # 所有生效的合约
                    if c['volume'] > 0:     # 有持仓订单
                        ctype = {v: k for k, v in CT_TYPES.items()}
                        symbol = c['symbol'] + '_' + ctype[c['contract_type']]
                        profit_rate = round(100 * c['profit_rate'], 2)      # 当前收益率
                        max_profit = 0
                        net_profit = 0
                        if sess.username in thd_datas:
                            if symbol in thd_datas[sess.username] and 'max_profit' in thd_datas[sess.username][symbol]:
                                max_profit = thd_datas[sess.username][symbol]['max_profit']
                                net_profit = thd_datas[sess.username][symbol]['net_profit']

                        # 用户配置中设置了止损价，自动设置止损
                        stop_loss = USERS_CONFIG[sess.username]['STOP_LOSS']
                        c_log = {'symbol': symbol, 'max_profit': max_profit,
                                 'net_profit': net_profit, 'profit_rate': profit_rate, 'warning': False}
                        if (stop_loss + net_profit) < 0:   # 当到达止损位置时，客户端发出警告
                            c_log.update({'warning': True})
                        rates.append(c_log)
            if len(rates) > 0:
                log.update({'rates': rates})

        return json.dumps(log).encode('utf-8')


class GetCoinsPage(Resource):
    isLeaf = True

    def render_GET(self, request):
        global gtb_prices, thd_datas
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        session = request.getSession()
        sess = ISession(session)
        log = {'msg': u"用户%s侦测失败，交易提交失败！" % sess.username, 'code': 404}
        if (sess.username != '') and (sess.username in USERS_CONFIG):
            _symbol = request.args[b"symbol"][0].decode('utf-8')
            _period = request.args[b"period"][0].decode('utf-8')    # CW, NW, CQ
            api_key = USERS_CONFIG[sess.username]['API_KEY']
            api_sec = USERS_CONFIG[sess.username]['SECRET_KEY']
            from api.HuobiDMService import HuobiDM
            api = HuobiDM(API_URL, api_key, api_sec)
            cpi = api.get_contract_position_info(_symbol)
            symbol = _symbol + '_' + _period
            if cpi['status'] == 'ok':
                if len(cpi['data']) > 0:
                    log = {'code': 200, 'data': cpi['data'][0], 'ts': cpi['ts']}
                else:   # 不持有本合约,计算对手价成交和当前价格成交的溢价情况
                    # 获取对手价成交和当前价成交溢价情况

                    tinfo = api.get_contract_trade(symbol)
                    depths = api.get_contract_depth(symbol=symbol, type='step0')
                    _price = float(tinfo['tick']['data'][0]['price'])
                    _buy1 = depths['tick']['bids'][0][0]
                    _sell1 = depths['tick']['asks'][0][0]
                    premium_buy = round(100.00 * ((_sell1 - _price) / _price), 2)   # 开多对手价溢价
                    premium_sell = round(100.00 * ((_price - _buy1) / _buy1), 2)   # 开空对手价溢价
                    log = {'code': 201, 'msg': "不持有本合约", 'ts': cpi['ts'],
                           'premium_buy': premium_buy, 'premium_sell': premium_sell}
                # 更新支撑，止损位置
                if sess.username in gtb_prices and symbol in gtb_prices[sess.username]:
                    log.update(gtb_prices[sess.username][symbol])
                # 更新止损位置，是否启动系统止损
                if sess.username in thd_datas and symbol in thd_datas[sess.username]:
                    log.update(thd_datas[sess.username][symbol])
                return json.dumps(log).encode('utf-8')

            else:
                log = {'code': 400, 'msg': "数据获取错误，请重试！"}
        return json.dumps(log).encode('utf-8')


class TopDownPage(Resource):
    isLeaf = True
    """
    设置当前品种的压力和支撑位价格，该价格存放在全局变量gtb_prices中
    GET 获取
    POST 设置
    """

    def render_GET(self, request):
        global gtb_prices
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        session = request.getSession()
        sess = ISession(session)
        log = {'err_msg': u"用户%s侦测失败，交易提交失败！" % sess.username, 'status': 'error', 'code': 404}
        if (sess.username != '') and (sess.username in USERS_CONFIG):
            _symbol = request.args[b"symbol"][0].decode('utf-8')  # 交易品种 BTC
            _period = request.args[b"period"][0].decode('utf-8')
            sym = "%s_%s" % (_symbol, _period)
            if sess.username in gtb_prices and sym in gtb_prices[sess.username]:
                log = {'status': 'ok', 'code': 200}.update(gtb_prices[sess.username][sym])
        return json.dumps(log).encode('utf-8')

    def render_POST(self, request):
        global gtb_prices
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        session = request.getSession()
        sess = ISession(session)
        log = {'err_msg': u"用户%s侦测失败，交易提交失败！" % sess.username, 'status': 'error', 'code': 404}
        if (sess.username != '') and (sess.username in USERS_CONFIG):
            _symbol = request.args[b"symbol"][0].decode('utf-8')
            _period = request.args[b"period"][0].decode('utf-8')
            sym = "%s_%s" % (_symbol, _period)
            _top = request.args[b"top"][0].decode('utf-8')
            _down = request.args[b"down"][0].decode('utf-8')
            if sess.username not in gtb_prices:
                gtb_prices[sess.username] = {}
            gtb_prices[sess.username].update({
                sym: {
                    'top': float(_top) if _top != '' else 0,
                    'down': float(_down) if _down != '' else 0
                }
            })
            log = {'status': 'ok', 'code': 200}
        return json.dumps(log).encode('utf-8')


class CancelPage(Resource):
    isLeaf = True
    """
    取消所有委托订单
    """
    def render_GET(self, request):
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        session = request.getSession()
        sess = ISession(session)
        log = {'err_msg': u"用户%s侦测失败，交易提交失败！" % sess.username, 'status': 'error', 'err_code': 404}
        if (sess.username != '') and (sess.username in USERS_CONFIG):
            _symbol = request.args[b"symbol"][0].decode('utf-8')  # 交易品种 BTC
            api_key = USERS_CONFIG[sess.username]['API_KEY']
            api_sec = USERS_CONFIG[sess.username]['SECRET_KEY']

            from api.HuobiDMService import HuobiDM
            api = HuobiDM(API_URL, api_key, api_sec)
            log = api.cancel_all_contract_order(symbol=_symbol)

        return json.dumps(log).encode('utf-8')


class TradePage(Resource):
    isLeaf = True

    """
        :symbol: "BTC","ETH"..
        :contract_type: "this_week", "next_week", "quarter"
        :price             必填   价格
        :volume            必填  委托数量（张）
        :direction         必填  "buy" "sell"
        :offset            必填   "open", "close"
        :lever_rate        必填  杠杆倍数
        :order_price_type  必填   "limit"限价， "opponent" 对手价
        备注：按照symbol+contract_type去下单。
    """
    def render_GET(self, request):
        global thd_datas, thd_mutex
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        session = request.getSession()
        sess = ISession(session)
        log = {'err_msg': u"用户%s侦测失败，交易提交失败！" % sess.username, 'status': 'error', 'err_code': 404}
        if (sess.username != '') and (sess.username in USERS_CONFIG):
            _symbol = request.args[b"symbol"][0].decode('utf-8')  # 交易品种 BTC
            _period = request.args[b"period"][0].decode('utf-8')  # CW, NW, CQ
            symbol_p = "%s_%s" % (_symbol, _period)
            _contract_type = CT_TYPES[_period]
            _direction = request.args[b"direction"][0].decode('utf-8')  # 交易方向 buy 多|sell 空
            _offset = request.args[b"offset"][0].decode('utf-8')  # 交易目的"open"开仓, "close"平仓
            # 'market', 'buy1', 'sell1', 'opponent' "limit"限价， "opponent" 对手价
            _opt_id = int(request.args[b"order_price_type"][0].decode('utf-8'))
            _opt = QT_PRICES[_opt_id]
            api_key = USERS_CONFIG[sess.username]['API_KEY']
            api_sec = USERS_CONFIG[sess.username]['SECRET_KEY']

            thd_mutex.acquire()  # 上锁
            if sess.username not in thd_datas:
                thd_datas[sess.username] = {symbol_p: {'max_profit': 0, 'net_profit': 0, 'auto_close': 1}}
            else:
                thd_datas[sess.username][symbol_p] = {'max_profit': 0, 'net_profit': 0, 'auto_close': 1}
            thd_mutex.release()

            from api.HuobiDMService import HuobiDM
            api = HuobiDM(API_URL, api_key, api_sec)
            # 获取当前仓位信息：
            cw = api.get_contract_position_info(_symbol)
            if cw['status'] == 'ok':
                # 获取当前成交价格
                params = {
                    'symbol': _symbol,
                    'period': _period,
                    'contract_type': _contract_type,
                    'direction': _direction,
                    'offset': _offset,
                    'price_type': _opt,
                    'client_order_id': int(time.time())
                }

                if len(cw['data']) > 0:     # 持有仓位，只能平仓
                    cwinfo = cw['data'][0]
                    price = self.get_price(api, params)
                    params.update({
                        'price': price,
                        'lever_rate': cwinfo['lever_rate'],
                        'volume': cwinfo['volume'],
                        'price_type': 'limit'  # 'opponent' if params['price_type'] == 'O' else 'limit'
                    })
                    if cwinfo['direction'] == 'buy':    # 持有多单, 卖出平多
                        log = self.contract_order(api, 'sell', 'close', params)
                    if cwinfo['direction'] == 'sell':  # 持有空单，买入平空
                        log = self.contract_order(api, 'buy', 'close', params)
                else:                       # 目前空仓，可以开仓
                    # 获取当前可用的币数值,杠杆和可买手数
                    coins = api.get_contract_account_info(_symbol)
                    lever_rate = coins['data'][0]['lever_rate']
                    coin_amount = coins['data'][0]['margin_available']
                    price = self.get_price(api, params)
                    volume = int((coin_amount * price * lever_rate) / MARKETS[_symbol]['usd'])
                    # 限制过量交易
                    max_open_amount = USERS_CONFIG[sess.username]['MAX_OPEN_AMOUNT']
                    volume = volume if volume < max_open_amount else max_open_amount
                    params.update({
                        'lever_rate': lever_rate,
                        'volume': volume,
                        'price': price,
                        'price_type': 'limit'  # 'opponent' if params['price_type'] == 'O' else 'limit'
                    })
                    if _direction == 'buy':  # 开多
                        log = self.contract_order(api, 'buy', 'open', params)
                    if _direction == 'sell':  # 开空
                        log = self.contract_order(api, 'sell', 'open', params)

        return json.dumps(log).encode('utf-8')

    def get_price(self, api, params):
        # op = self.get_one_point(params['symbol'])
        if params['price_type'] == 'C':  # market市价,获取当前成交价
            tinfo = api.get_contract_trade("%s_%s" % (params['symbol'], params['period']))
            return float(tinfo['tick']['data'][0]['price'])
        elif params['price_type'] == 'O':   # 对手价
            # depths = api.get_contract_depth(symbol="%s_%s" % (params['symbol'], params['period']), type='step5')
            _plimits = api.get_contract_price_limit(params['symbol'], CT_TYPES[params['period']])
            high_price = _plimits['data'][0]['high_limit'] * 0.98
            low_price = _plimits['data'][0]['low_limit'] * 1.02
            if params['direction'] == 'buy':    # 获取卖2价
                return round(high_price, MARKETS[params['symbol']]['u'])
            else:
                return round(low_price, MARKETS[params['symbol']]['u'])
        elif params['price_type'] == 'B':
            depths = api.get_contract_depth(symbol="%s_%s" % (params['symbol'], params['period']), type='step0')
            return round((depths['tick']['bids'][0][0]), MARKETS[params['symbol']]['u'])
        elif params['price_type'] == 'S':
            depths = api.get_contract_depth(symbol="%s_%s" % (params['symbol'], params['period']), type='step0')
            return round((depths['tick']['asks'][0][0]), MARKETS[params['symbol']]['u'])
        elif params['price_type'] == 'H':
            symbol = "%s_%s" % (params['symbol'], params['period'])
            kline = api.get_contract_kline(symbol, '1min', 2)
            return kline['data'][0]['high']
        elif params['price_type'] == 'L':
            symbol = "%s_%s" % (params['symbol'], params['period'])
            kline = api.get_contract_kline(symbol, '1min', 2)
            return kline['data'][0]['low']
        elif params['price_type'] == 'K':
            symbol = "%s_%s" % (params['symbol'], params['period'])
            kline = api.get_contract_kline(symbol, '1min', 2)
            return kline['data'][0]['open']
        elif params['price_type'] == 'G':
            symbol = "%s_%s" % (params['symbol'], params['period'])
            kline = api.get_contract_kline(symbol, '1min', 2)
            return kline['data'][0]['close']
        elif params['price_type'] == 'F':   # 强行平仓价针对瀑布极端行情，按照超越对手价格委托
            # depths = api.get_contract_depth(symbol="%s_%s" % (params['symbol'], params['period']), type='step5')
            _plimits = api.get_contract_price_limit(params['symbol'], CT_TYPES[params['period']])
            high_price = _plimits['data'][0]['high_limit'] * 0.98
            low_price = _plimits['data'][0]['low_limit'] * 1.02

            if params['direction'] == 'buy':  # 获取卖2价
                return round(high_price, MARKETS[params['symbol']]['u'])
            else:
                return round(low_price, MARKETS[params['symbol']]['u'])
        else:
            return 0

    def contract_order(self, api, direction, offset, params):
        """
        开多
        :param params   交易参数
        :param api:
        :param direction
        :param offset
        :return:
        """
        r = api.send_contract_order(
            symbol=params['symbol'],
            contract_type=params['contract_type'],
            client_order_id=params['client_order_id'],
            price=params['price'],
            volume=int(params['volume']),
            direction=direction,
            offset=offset,
            lever_rate=params['lever_rate'],
            order_price_type=params['price_type']
        )
        return r

    @staticmethod
    def get_one_point(_symbol):  # 当前品种的最小usd 1个点
        rd = math.pow(10, MARKETS[_symbol]['u'])
        return float(1 / rd)


# ----------------- session 相关

def longTimeoutSession(*args, **kwargs):
    session = Session(*args, **kwargs)
    session.sessionTimeout = 36000
    return session


class ISession(Interface):
    username = Attribute("The unique identifier for this session.")


@implementer(ISession)
class UserSession(object):

    def __init__(self, session):
        self.username = ""


registerAdapter(UserSession, Session, ISession)


def trade_server():
    root = File("./htdocs")
    # for _symbol in MARKETS.keys(): root.putChild(str.encode(_symbol), resource)
    factory = EchoServerFactory()
    factory.protocol = EchoServerProtocol
    factory.startFactory()  # when wrapped as a Twisted Web resource, start the underlying factory manually
    resource = WebSocketResource(factory)
    root.putChild(b"wss", resource)

    root.putChild(b"symbols", SymbolPage())     # 用于向页面传递交易对接口
    root.putChild(b"signin", SignInPage())      # 登录页面
    root.putChild(b"logout", SignOutPage())     # 登出页面
    root.putChild(b"logchk", LogCheckPage())    # 登陆状态检测接口
    root.putChild(b"setlost", SetLostPage())    # 设置全局变量是否自动止损
    root.putChild(b"trade", TradePage())        # 交易接口
    root.putChild(b"cancel", CancelPage())      # 取消所有订单
    root.putChild(b"contract", GetCoinsPage())  # 获取最新价格接口
    root.putChild(b"topdown", TopDownPage())    # 获取和设置当前品种的压力和支撑价格
    # use TLS
    privkey = open('cert/server.key', 'rt').read()
    certif = open('cert/fullchain.cer', 'rt').read()
    privkeypyssl = crypto.load_privatekey(crypto.FILETYPE_PEM, privkey)
    certifpyssl = crypto.load_certificate(crypto.FILETYPE_PEM, certif)
    contextFactory = ssl.CertificateOptions(privateKey=privkeypyssl, certificate=certifpyssl)

    site = Site(root)
    site.sessionFactory = longTimeoutSession
    reactor.listenSSL(SRV_PORT, site, contextFactory)
    # reactor.listenTCP(SRV_PORT, site)
    reactor.run()


class RunDaemon(Daemon):
    def run(self):
        trade_server()


if __name__ == '__main__':
    deploy_dir = '/home/wwwroot/hbdm.com'
    os.chdir(deploy_dir)
    thd_mutex = threading.Lock()    # 进程数据共享，全局变量
    thd_datas = {}
    gtb_prices = {}    # 保存不同用户设置的不同品种的压力支撑价格 top_bottom_prices
    top_counter = down_counter = {}  # 用于记录当前时刻跌破支撑或是突破压力位的突破次数
    daemon = RunDaemon(stdfile='srv-hbdm', work_dir=deploy_dir)
    if len(argv) == 2:
        if 'start' == argv[1]:
            daemon.start()
        elif 'stop' == argv[1]:
            daemon.stop()
        elif 'restart' == argv[1]:
            daemon.restart()
        else:
            print("Unknown command")
            exit(2)
        exit(0)
    else:
        print("usage: %s start|stop|restart" % argv[0])
        exit(2)
