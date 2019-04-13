from trader.vtObject import VtOrderData
from trader.app.strategyTrading.strBase import *
from trader.app.strategyTrading.BacktestingBase import BacktestingEngine
from trader.app.strategyTrading.strHistoryData import loadBinanceCsv
from trader.vtConstant import *
import pandas as pd
import time


class BackTestEngine(BacktestingEngine):
    def sendOrder(self, symbol, orderType, price, volume, priceType, stopLossPx=None, takeProfPx=None, stopVol=None,
                  strategy=None):

        vtOrderIDList = []
        self.limitOrderCount += 1
        ts = str(int(time.time() * 1000000) + self.limitOrderCount)
        localID = '_'.join([ts, priceType])
        vtOrderID = '_'.join(['Main@BINANCE'.split('@')[-1], localID])
        vtOrderIDList.append(vtOrderID)
        order = VtOrderData()
        order.gatewayName = 'Main@BINANCE'
        order.orderID = localID
        order.vtOrderID = '.'.join([order.gatewayName, order.orderID])
        order.orderSysID = self.limitOrderCount
        order.symbol = symbol
        order.exchange = EXCHANGE_BINANCE
        order.vtSymbol = '.'.join([order.symbol, order.exchange])

        order.price = price
        order.totalVolume = volume
        # order.direction = direction
        # order.offset = OFFSET_NONE
        order.status = STATUS_UNKNOWN
        order.orderTime = self.dt.strftime('%H:%M:%S')

        if orderType == STR_ORDER_BUY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_OPEN

        elif orderType == STR_ORDER_SELL:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSE

        self.workingLimitOrderDict[vtOrderID] = order
        self.limitOrderDict[vtOrderID] = order

        return vtOrderIDList

    def loadHisroryDataCsv(self, fileName, symbol):
        self.dbCursor = loadBinanceCsv(fileName, symbol)
        return

