from trader.vtObject import VtOrderData
from trader.app.strategyTrading.strBase import *
from trader.app.strategyTrading.BacktestingBase import BacktestingEngine
from trader.app.strategyTrading.strHistoryData import loadBitmexCsv
from trader.vtConstant import *


class BackTestEngine(BacktestingEngine):
    def sendOrder(self, symbol, orderType, price, volume, priceType, stopLossPx, takeProfPx, strategy):
        self.limitOrderCount += 1
        orderID = str(self.limitOrderCount)

        order = VtOrderData()
        order.vtSymbol = symbol
        order.price = self.roundToPriceTick(price)
        order.totalVolume = volume
        order.orderID = orderID
        order.vtOrderID = orderID
        order.orderTime = self.dt.strftime('%H:%M:%S')

        if orderType == STR_ORDER_BUY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_OPEN
        elif orderType == STR_ORDER_SELL:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSE
        elif orderType == STR_ORDER_SHORT:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_OPEN
        elif orderType == STR_ORDER_COVER:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSE

        self.workingLimitOrderDict[orderID] = order
        self.limitOrderDict[orderID] = order

        return [orderID]

    def loadHisroryDataCsv(self, fileName, symbol):
        self.dbCursor = loadBitmexCsv(fileName, symbol)
        return


