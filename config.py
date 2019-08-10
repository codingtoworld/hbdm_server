#!/usr/bin/env python
# -*- coding: utf-8 -*-
SRV_PORT = 443
API_URL = 'https://api.hbdm.com'

MARKETS = {
    'BTC':      {'usd': 100, 'c': 4, 'u': 2},       # 1张需要的美金数目，btc精确小数点，usd精确小数点
    'ETH':      {'usd': 10, 'c': 4, 'u': 3},
    'BCH':      {'usd': 10, 'c': 4, 'u': 3},
    'EOS':      {'usd': 10, 'c': 4, 'u': 3},
    'LTC':      {'usd': 10, 'c': 4, 'u': 3},
    'TRX':      {'usd': 10, 'c': 2, 'u': 5},
    'XRP':      {'usd': 10, 'c': 2, 'u': 4}
}


QT_PRICES = [
    "C",     # 当前成交价
    "S",     # 卖一价
    "B",     # 买一价
    "O",     # 对手价,
    "H",     # 上一个一分钟K线最高
    "L",     # 上一个一分钟K线最低
    "K",     # 上一个一分钟K线开盘价
    "G",     # 上一个一分钟K线收盘价
    " ",     # 系统保留
    "F",     # 强行平仓
]

CT_TYPES = {
    "CW": "this_week",
    "NW": "next_week",
    "CQ": "quarter"
}
USERS_CONFIG = {
    "coddingtoworld": {
        "GOOGLE_CODE": "",      # Google Authorized Code
        "API_KEY": "",          # 火币用户API KEY，需要在火币账户后台添加获取
        "SECRET_KEY": "",       # 火币用户SECRET_KEY，需要在火币账户后台添加获取
        "STOP_LOSS": 0.2,       # 净利润小于-0.2%时，自定义触发平仓止损点
        # 限制过量交易，每次最大开仓的口数，用于资金管理，比方20倍杠杆可以开100口的保证金，最多开50口
        # 比方入账10美金，20倍杠杆除BTC，其他的都可以开20口，这时，需要设置成10，这样你赔了后，下次下单还是同样口数
        "MAX_OPEN_AMOUNT": 10
    }
}
