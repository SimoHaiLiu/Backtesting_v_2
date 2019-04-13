# encoding: UTF-8

"""
5m RSI simple strategy, for test only.

"""
import talib
from trader.vtObject import VtBarData
from trader.vtConstant import *
from trader.app.strategyTrading.strTemplate import (StrTemplate,
                                                    BarGenerator,
                                                    ArrayManager)


########################################################################
class RsiStrategy(StrTemplate):
    """RSI指标的一个分钟线交易策略"""
    className = 'RsiStrategy'
    author = u'Jed'

    # 策略参数
    rsiLength = 20  # 计算RSI的窗口数
    rsiEntry = 20  # RSI的开仓信号
    # trailingPercent = 0.8   # 百分比移动止损
    initBars = 150  # 初始化数据所用的天数
    fixedSize = 1  # 每次交易的数量

    # 策略变量
    rsiValue = 0  # RSI指标的数值
    rsiBuy = 0  # RSI买开阈值
    rsiSell = 0  # RSI卖开阈值
    intraTradeHigh = 0  # 移动止损用的持仓期内最高价
    intraTradeLow = 0  # 移动止损用的持仓期内最低价

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbols',
                 'rsiLength',
                 'rsiEntry']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'rsiValue',
               'rsiBuy',
               'rsiSell']

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos',
                'intraTradeHigh',
                'intraTradeLow']

    # ----------------------------------------------------------------------
    def __init__(self, strEngine, setting):
        """Constructor"""
        super(RsiStrategy, self).__init__(strEngine, setting)

        self.activeOrderDict = {}
        # 创建K线合成器对象
        self.bg = BarGenerator(self.onBar)  # , xmin=5, onXminBar=self.onXMinBar)
        self.am = ArrayManager(size=250)

        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）        

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeStrLog(u'%s策略初始化' % self.name)

        # 初始化RSI入场阈值
        self.rsiBuy = 50 - self.rsiEntry
        self.rsiSell = 50 + self.rsiEntry

        # self.qryOrder(openOnly=True)
        # self.qryPosition()

        for vtSymbol in self.vtSymbols:
            self.pos[vtSymbol] = 0.0
            ## 载入历史数据，并采用回放计算的方式初始化策略数值
        # initData = self.loadBar(self.initDays)
        # for bar in initData:
        # self.onBar(bar)

        # self.qryBar(limit=250)

        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeStrLog(u'%s策略启动' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeStrLog(u'%s策略停止' % self.name)
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # if not self.trading:
        #     if order.vtSymbol in self.vtSymbols and order.status in [STATUS_NOTTRADED, STATUS_PARTTRADED]:
        #         # record to local active order list
        #         if order.orderID != EMPTY_STRING: # not store the orders originated from web (not from client).
        #
        #             oId = order.vtOrderID.split('_')[1]
        #
        #             if oId not in self.activeOrderDict:
        #                 self.activeOrderDict[oId] = {}
        #             self.activeOrderDict[oId][order.orderType] = order
        #         else:
        #             pass
        #
        # else:
        #     # process the live orders when trading ON.
        #     if order.vtSymbol in self.vtSymbols and order.status not in [STATUS_UNKNOWN]:
        #         oId = order.vtOrderID.split('_')[0]
        #
        #         if oId not in self.activeOrderDict:
        #             self.activeOrderDict[oId] = {}
        #         self.activeOrderDict[oId][order.orderType] = order

        return

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        # 发出状态更新事件
        # if self.trading:
        #     if trade.orderID != EMPTY_STRING:
        #         oId = trade.orderID.split('_')
        #         if oId[1] in self.activeOrderDict:
        #             if oId[-1] == PRICETYPE_STOPLIMIT:
        #                 self.cancelOrder(self.activeOrderDict[oId[1]][PRICETYPE_LIMITIFTOUCHED].vtOrderID)
        #             elif oId[-1] == PRICETYPE_LIMITIFTOUCHED:
        #                 self.cancelOrder(self.activeOrderDict[oId[1]][PRICETYPE_STOPLIMIT].vtOrderID)
        #
        self.putEvent()

    # ----------------------------------------------------------------------
    def onPosition(self, position):

        # always update the pos dict based on the position info
        # position is an abs value so add the sign based on direction
        if position.vtSymbol in self.vtSymbols:

            if position.direction == DIRECTION_LONG:
                self.pos[position.vtSymbol] = position.position
            else:
                self.pos[position.vtSymbol] = -position.position

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """new bars available, calcs and logics here"""
        """the below is just an example, the code may not be executable!!!"""
        if not bar.lastBar:
            # print ' '.join(['1m', str(bar.open), str(bar.high), str(bar.low), str(bar.close), str(bar.volume), str(bar.date), str(bar.time)])
            # self.bg.updateBar(bar)

            priceTick = self.getPriceTick(bar.vtSymbol)
            # self.cancelAll()

            # 保存K线数据
            self.am.updateBar(bar)
            # print ' '.join(['1m', str(bar.open), str(bar.high), str(bar.low), str(bar.close), str(bar.volume), str(bar.date), str(bar.time), str(self.am.closeArray)])
            if not self.am.inited:
                return
            # 计算指标数值
            self.rsiValue = self.am.rsi(self.rsiLength, array=True)
            self.sma1 = talib.SMA(self.rsiValue, 100)
            self.sma2 = talib.SMA(self.rsiValue, 200)
            # print ' '.join(['1m', str(bar.open), str(bar.high), str(bar.low), str(bar.close), str(bar.volume), str(bar.date), str(bar.time), str(self.rsiValue[-1]), str(self.sma1[-1]), str(self.sma2[-1])])
            # 判断是否要进行交易
            if not self.trading:
                return

            if self.sma1[-1] >= 50:
                if self.pos[bar.vtSymbol] <= 0:
                    self.buy(bar.vtSymbol, bar.close + priceTick, self.fixedSize - self.pos[bar.vtSymbol],
                             PRICETYPE_LIMITPRICE)  # , bar.close-priceTick*9, bar.close+priceTick*11)#self.buy(bar.close+5, self.fixedSize)
            elif self.sma1[-1] < self.sma2[-1] and self.sma2[-1] < 50:
                if self.pos[bar.vtSymbol] >= 0:
                    self.sell(bar.vtSymbol, bar.close - priceTick, self.fixedSize + self.pos[bar.vtSymbol],
                              PRICETYPE_LIMITPRICE)  # , bar.close+priceTick*9, bar.close-priceTick*11)#self.short(bar.close-5, self.fixedSize)

            # self.putEvent()
        else:
            # print ' '.join(['1m-last his bar', str(bar.open), str(bar.high), str(bar.low), str(bar.close), str(bar.volume), str(bar.date), str(bar.time)])
            self.bg.setBar(bar)
            self.inited = True

    # ----------------------------------------------------------------------
    def onXMinBar(self, bar):
        # print ' '.join(['5m', str(bar.open), str(bar.high), str(bar.low), str(bar.close), str(bar.volume), str(bar.date), str(bar.time)])

        # 持有多头仓位
        # elif self.pos[bar.vtSymbol] > 0:
        # if self.rsiValue > self.rsiSell:
        # self.sell(bar.vtSymbol, bar.close-priceTick, self.fixedSize+self.pos[bar.vtSymbol], PRICETYPE_LIMITPRICE, bar.close+priceTick*9, bar.close-priceTick*11)

        ## 持有空头仓位
        # elif self.pos[bar.vtSymbol] < 0:
        # if self.rsiValue < self.rsiBuy:
        # self.buy(bar.vtSymbol, bar.close+priceTick, self.fixedSize-self.pos[bar.vtSymbol], PRICETYPE_LIMITPRICE, bar.close-priceTick*9, bar.close+priceTick*11)#

        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass

    # ----------------------------------------------------------------------
    def onTimer(self):
        pass
