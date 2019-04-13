# encoding: UTF-8

'''
This file defines the constants and base classes of strategy trading module
'''

# 
from trader.vtConstant import EMPTY_UNICODE, EMPTY_STRING, EMPTY_FLOAT, EMPTY_INT

# Constants
STR_ORDER_PLACE = 'place'
STR_ORDER_CANCEL = 'cancel'
# Directions
STR_ORDER_BUY = 'Buy'
STR_ORDER_SELL = 'Sell'
STR_ORDER_SHORT = 'Short'
STR_ORDER_COVER = u'Cover'

# Database Names
SETTING_DB_NAME = 'VnTrader_Setting_Db'
POSITION_DB_NAME = 'VnTrader_Position_Db'

TICK_DB_NAME = 'VnTrader_Tick_Db'
DAILY_DB_NAME = 'VnTrader_Daily_Db'
MINUTE_DB_NAME = 'VnTrader_1Min_Db'

# Engine types
ENGINETYPE_BACKTESTING = 'backtesting'  
ENGINETYPE_TRADING = 'trading'


class StopOrder(object):
    """本地停止单"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.vtSymbol = EMPTY_STRING
        self.orderType = EMPTY_UNICODE
        self.direction = EMPTY_UNICODE
        self.offset = EMPTY_UNICODE
        self.price = EMPTY_FLOAT
        self.volume = EMPTY_INT

        self.strategy = None  # 下停止单的策略对象
        self.stopOrderID = EMPTY_STRING  # 停止单的本地编号
        self.status = EMPTY_STRING  # 停止单状态