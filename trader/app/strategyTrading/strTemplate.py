# encoding: UTF-8

'''

This file defines the strategy template base class StrTemplate.
Inherit from this base when creating new strategies.
'''

from trader.vtConstant import *
from trader.vtUtility import BarGenerator, ArrayManager

from .strBase import *


########################################################################
class StrTemplate(object):
    """strategy template"""
    
    # strategy name and author
    className = 'StrTemplate'
    author = EMPTY_UNICODE
    
    # basic parameters
    name = EMPTY_UNICODE           # instance name
    vtSymbols = EMPTY_LIST        # symbol name list
    productClass = EMPTY_STRING    # spot, swap, futures, option, etc.
    currency = EMPTY_STRING        # base currency, usd, etc. not a must
    
    # 策略的基本变量，由引擎管理
    inited = False                 # is the strategy get initialized
    trading = False                # is the strategy get started
    
    # strategy position dict, each symbol (key) has a long/short positions (value)
    # initialize its keys with vtSymbols when creating an instance and onPosition
    # the long/short position values will be updated as a list
    # e.g. pos = {'BTC-PERPETUAL.DERIBIT.Swap':[25,-8], 'XBTUSD.BITMEX.Swap': [0, 10]}
    pos = {}                 
    
    # param list,
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbols',
                 'productClass']
    
    # variable list - for GUI
    varList = ['inited',
               'trading',
               'pos']
    
    
    # order template
    placeOrder = {'action': STR_ORDER_PLACE}
    cancelOrder = {'action': STR_ORDER_CANCEL, 'id': EMPTY_INT}
    
    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos']
    
    #----------------------------------------------------------------------
    def __init__(self, strEngine, setting):
        """Constructor"""
        self.strEngine = strEngine

        # 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]
    
    #----------------------------------------------------------------------
    def onInit(self):
        """call back on strategy initialized"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStart(self):
        """call back on strategy started"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onStop(self):
        """call back on strategy stoped"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onTick(self, tick):
        """call back on tickers"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onMarketTrade(self, mt):
        """call back on market trades"""
        raise NotImplementedError

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """call back on orders"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """call back on trades"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onPosition(self, position):
        """call back on positions"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onTimer(self):
        """call back on a 1s timer"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """call back on bars"""
        raise NotImplementedError
    
    #----------------------------------------------------------------------
    def buy(self, symbol, price, volume, priceType, stopLossPx=None, takeProfPx=None):
        """open long"""
        return self.sendOrder(symbol, STR_ORDER_BUY, price, volume, priceType, stopLossPx, takeProfPx)
    
    #----------------------------------------------------------------------
    def sell(self, symbol, price, volume, priceType, stopLossPx=None, takeProfPx=None):
        """close long"""
        return self.sendOrder(symbol, STR_ORDER_SELL, price, volume, priceType, stopLossPx, takeProfPx)     

    #----------------------------------------------------------------------
    def short(self, symbol, price, volume, priceType):
        """open short"""      
        return self.sendOrder(symbol, STR_ORDER_SHORT, price, volume, priceType)        
 
    #----------------------------------------------------------------------
    def cover(self, symbol, price, volume, priceType):
        """close short"""  
        return self.sendOrder(symbol, STR_ORDER_COVER, price, volume, priceType)

    #----------------------------------------------------------------------
    def sendOrder(self, symbol, orderType, price, volume, priceType, stopLossPx=None, takeProfPx=None):
        """send order"""
        vtOrderIDList = []
        if self.trading:
            return self.strEngine.sendOrder(symbol, orderType, price, volume, priceType, stopLossPx, takeProfPx, self)

        return vtOrderIDList
        
    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """cancel order"""
        if vtOrderID:
            self.strEngine.cancelOrder(vtOrderID)
            
    #----------------------------------------------------------------------
    def cancelAll(self):
        """cancel all"""
        self.strEngine.cancelAll(self.name)
 
    #----------------------------------------------------------------------
    def sendBatchOrder(self, orders):
        """send batch orders"""
        vtOrderIDList = []

        for order in orders:
            if 'place' in order['action']:
                if self.trading: 
                    vtOrderIDList.append(self.strEngine.sendOrder(order, self)) 
            elif 'cancel' in order['action']:
                if order['id']:
                    self.strEngine.cancelOrder(order['id'])

        return vtOrderIDList
    
    #----------------------------------------------------------------------
    def qryBar(self, interval='1m', limit=1000):
        self.strEngine.qryBar(self,interval,limit)
        
    #----------------------------------------------------------------------
    def qryOrder(self,openOnly=False):
        self.strEngine.qryOrder(self,openOnly)
     
    #----------------------------------------------------------------------
    def qryPosition(self):
        self.strEngine.qryPosition(self)
        
    #----------------------------------------------------------------------
    def insertTick(self, vtSymbol, tick):
        """insert ticks to db"""
        self.strEngine.insertData(self.tickDbName, vtSymbol, tick)
    
    #----------------------------------------------------------------------
    def insertBar(self, vtSymbol, bar):
        """向数据库中插入bar数据"""
        self.strEngine.insertData(self.barDbName, vtSymbol, bar)
        
    #----------------------------------------------------------------------
    def loadTick(self, vtSymbol, days):
        """load history ticks"""
        return self.strEngine.loadTick(self.tickDbName, vtSymbol, days)
    
    #----------------------------------------------------------------------
    def loadBar(self, vtSymbol, days):
        """load history bars"""
        return self.strEngine.loadBar(self.barDbName, vtSymbol, days)
    
    #----------------------------------------------------------------------
    def writeStrLog(self, content):
        """write log"""
        content = self.name + ':' + content
        self.strEngine.writeStrLog(content)
        
    #----------------------------------------------------------------------
    def putEvent(self):
        """put status update events"""
        self.strEngine.putStrategyEvent(self.name)
        
    #----------------------------------------------------------------------
    def getEngineType(self):
        """get engine type"""
        return self.strEngine.engineType
    
    #----------------------------------------------------------------------
    def saveSyncData(self):
        """save sync data to db"""
        if self.trading:
            self.strEngine.saveSyncData(self)
    
    #----------------------------------------------------------------------
    def getPriceTick(self, vtSymbol):
        """get prick tick info"""
        return self.strEngine.getPriceTick(vtSymbol)