# encoding: UTF-8
'''
BITMEX期货REST交易接口
'''
from datetime import timedelta
from trader.vtGateway import *
from trader.vtObject import VtBarData
from apiBase.rest.RestClient import Request, RestClient
from bitmexUtils import _split_url, createSignatureRest
from bitmexConsts import *


########################################################################
class BitmexFutureRestApi(RestClient):
    
    #----------------------------------------------------------------------
    def __init__(self, gateway):  # type: (VtGateway)->BitmexFutureRestApi
        """"""
        super(BitmexFutureRestApi, self).__init__()
        
        self.gateway = gateway
        self.gatewayName = gateway.gatewayName
        
        self.apiKey = ""
        self.apiSecret = ""
        self.signHost = ""
        
        self.accountDict = gateway.accountDict
        self.orderDict = gateway.orderDict
        self.orderLocalDict = gateway.orderLocalDict
        self.localOrderDict = gateway.localOrderDict
        
        self.accountid = ''     # 
        self.cancelReqDict = {}
        self.orderBufDict = {}
        
    #----------------------------------------------------------------------
    def sign(self, request):
        #request.headers = {
            #"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36"
        #}
        print request.data
        expires, signature = createSignatureRest(self.apiSecret, request)
        print request.data
        
        #if request.method == "POST":

        request.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "api-key": self.apiKey,
            "api-expires": str(expires),
            "api-signature": signature,
        }            

            #if request.data:
                #request.data = json.dumps(request.data)
   
        return request
    
    #----------------------------------------------------------------------
    def connect(self, futureSymbols, swapSymbols, apiKey, apiSecret, sessionCount=3):
        """连接服务器"""
        self.futureSymbols = futureSymbols
        self.swapSymbols = swapSymbols
        self.apiKey = apiKey
        self.apiSecret = apiSecret
        
        host, path = _split_url(REST_HOST)
        self.init(REST_HOST)
        
        self.signHost = host
        self.start(sessionCount)
        
        self.queryContract()
        # test
        #self.queryAccount()
    
    #----------------------------------------------------------------------  
    def addSymbol(self, type_, symbol):
        if type_ == PRODUCT_FUTURES:
            self.futureSymbols.append(symbol)
        elif type_ == PRODUCT_SWAP:
            self.swapSymbols.append(symbol)
            
    #----------------------------------------------------------------------
    def queryBar(self, symbol=None, interval='1m', count=1000):
        """"""    
        params = {'symbol': symbol, 'binSize': interval, 'count': count, 'reverse': True, 'partial': True}
        self.addRequest('GET', '/trade/bucketed', self.onQueryBar, data=params, extra=symbol+'_'+interval) 
        
    #----------------------------------------------------------------------
    def queryAccount(self):
        """"""
        self.addRequest('GET', '/user/wallet', self.onQueryAccount)
    
    #----------------------------------------------------------------------
    def queryAccountBalance(self):
        """"""
        path = '/v1/account/accounts/%s/balance' %self.accountid
        self.addRequest('GET', path, self.onQueryAccountBalance)
    
    #----------------------------------------------------------------------
    def queryOrder(self, openOnly=False):
        """"""
        params = {'reverse': True}
        if openOnly:
            params['open'] = True
        self.addRequest('GET', '/order', self.onQueryOrder, data=params)
        
    #----------------------------------------------------------------------
    def queryTrade(self):
        """"""    
        params = {'reverse': True}
        self.addRequest('GET', '/execution/TradeHistory', self.onQueryTrade, data=params)    
        
    #----------------------------------------------------------------------
    def queryPos(self):
        """"""

        self.addRequest('GET', '/position', self.onQueryPos)
        
    #----------------------------------------------------------------------
    def queryContract(self):
        """"""
        self.addRequest('GET', '/instrument/active', self.onQueryContract, sign=False)
    
    #----------------------------------------------------------------------
    def sendOrder(self, orderReq):
        """"""
        vtOrderIDList = []
        self.gateway.localID += 1
        ts = str(int(time.time()*1000000)+self.gateway.localID)
        localID = '_'.join([ts,orderReq.priceType])
        vtOrderID = '_'.join([self.gatewayName, localID])
        vtOrderIDList.append(vtOrderID)
        
        params = {
            "symbol": str(orderReq.symbol),
            "side": DIRECTION_VT2BITMEX[orderReq.direction],
            "ordType": PRICETYPE_VT2BITMEX[orderReq.priceType],
            #"price": orderReq.price,
            "orderQty": int(orderReq.volume),
            "clOrdID": str(vtOrderID),
        }

        # Only add price for limit order.
        if orderReq.priceType in [PRICETYPE_LIMITPRICE]:
            params["price"] = orderReq.price
             
        order = VtOrderData()
    
        order.gatewayName = self.gatewayName
        order.orderID = localID
        order.vtOrderID = vtOrderID
        order.exchange = EXCHANGE_BITMEX
        order.symbol = orderReq.symbol
        order.vtSymbol = '.'.join([order.symbol, order.exchange])
        order.orderType = orderReq.priceType
        order.price = orderReq.price
        order.totalVolume = orderReq.volume
        order.direction = orderReq.direction
        order.offset = OFFSET_NONE
        order.status = STATUS_UNKNOWN
    
        self.orderBufDict[localID] = order
            
        # When the req has either a take profit px or a stop loss px, then we have to post a bulk order 
        if orderReq.stopLossPx or orderReq.takeProfPx:
            bulkOrderParams = {"orders":[params,]}
            
            if orderReq.takeProfPx:
                #self.gateway.localID += 1
            
                localID = '_'.join([ts,PRICETYPE_MARKETIFTOUCHED])
                vtOrderID = '_'.join([self.gatewayName, localID])
                vtOrderIDList.append(vtOrderID)
                
                paramsTp = {
                    "symbol": str(orderReq.symbol),
                    "side": DIRECTION_VT2BITMEX[directionRevMap.get(orderReq.direction)],
                    "ordType": PRICETYPE_VT2BITMEX[PRICETYPE_MARKETIFTOUCHED],
                    #"price": orderReq.takeProfPx,
                    "stopPx": orderReq.takeProfPx,
                    "execInst": "LastPrice",
                    "orderQty": int(orderReq.takeProfVol),
                    "clOrdID": str(vtOrderID),
                }            
    
                bulkOrderParams["orders"].append(paramsTp)

            if orderReq.stopLossPx:
                self.gateway.localID += 1
            
                localID = '_'.join([ts,PRICETYPE_STOP])
                vtOrderID = '_'.join([self.gatewayName, localID])
                vtOrderIDList.append(vtOrderID)
                
                paramsSl = {
                    "symbol": str(orderReq.symbol),
                    "side": DIRECTION_VT2BITMEX[directionRevMap.get(orderReq.direction)],
                    "ordType": PRICETYPE_VT2BITMEX[PRICETYPE_STOP],
                    #"price": orderReq.stopLossPx,
                    "stopPx": orderReq.stopLossPx,
                    "execInst": "LastPrice",
                    "orderQty": int(orderReq.stopLossVol),
                    "clOrdID": str(vtOrderID),
                }     
                
                bulkOrderParams["orders"].append(paramsSl)   
            
        
            path = '/order/bulk'
            self.addRequest('POST', path, self.onSendOrder, 
                                    data=bulkOrderParams, 
                                            onFailed=self.on_send_order_failed,
                                            onError=self.on_send_order_error,
                                )    
                     
        else:
            
            path = '/order'
            self.addRequest('POST', path, self.onSendOrder, 
                            data=params, 
                onFailed=self.on_send_order_failed,
                onError=self.on_send_order_error,
            )        

        self.gateway.onOrder(order)
        
        # 返回订单号
        return vtOrderIDList
        
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelReq):
        """"""
        #localID = cancelReq.orderID
        #orderID = self.localOrderDict.get(localID, None)

        if cancelReq.orderID:
            params = {"orderID": str(cancelReq.orderID)}
            path = '/order' 
            self.addRequest('DELETE', path, self.onCancelOrder, data=params, onError=self.on_cancel_order_error)
            
            #if localID in self.cancelReqDict:
                #del self.cancelReqDict[localID]
        #else:
            #self.cancelReqDict[localID] = cancelReq        
    
    #----------------------------------------------------------------------
    def onQueryAccount(self, data, request):  # type: (dict, Request)->None
        """"""
        for d in data['data']:
            if str(d['type']) == 'spot':
                self.accountid = str(d['id'])
                self.gateway.writeLog(u'账户代码%s查询成功' %self.accountid)        
        
        self.queryAccountBalance()
    
    #----------------------------------------------------------------------
    def onQueryAccountBalance(self, data, request):  # type: (dict, Request)->None
        """"""
        status = data.get('status', None)
        if status == 'error':
            msg = u'错误代码：%s, 错误信息：%s' %(data['err-code'], data['err-msg'])
            self.gateway.writeLog(msg)
            return
        
        self.gateway.writeLog(u'资金信息查询成功')
        
        for d in data['data']['list']:
            currency = d['currency']
            account = self.accountDict.get(currency, None)

            if not account:
                account = VtAccountData()
                account.gatewayName = self.gatewayName
                account.accountID = d['currency']
                account.vtAccountID = '.'.join([account.gatewayName, account.accountID])
                
                self.accountDict[currency] = account
            
            if d['type'] == 'trade':
                account.available = float(d['balance'])
            elif d['type'] == 'frozen':
                account.margin = float(d['balance'])
            
            account.balance = account.margin + account.available

        for account in self.accountDict.values():
            self.gateway.onAccount(account)   
        
        self.queryTrade()
    
    #----------------------------------------------------------------------
    def onQueryPos(self, data, request):  # type: (dict, Request)->None
        for d in data:
            if 'currentCost' not in d:
                return
            
            pos = VtPositionData()
            pos.gatewayName = self.gatewayName
            pos.symbol = d["symbol"]
            pos.exchange = EXCHANGE_BITMEX
            pos.vtSymbol = '.'.join([pos.symbol,pos.exchange])
            pos.vtPositionName = '.'.join([pos.vtSymbol, pos.gatewayName])
            if 'avgEntryPrice' in d and d['avgEntryPrice']:
                pos.openPrice = float(d['avgEntryPrice'])
            pos.position = abs(float(d["currentQty"]))
            if d['currentQty'] > 0:
                pos.direction = DIRECTION_LONG
            else:
                pos.direction = DIRECTION_SHORT#pos.position  - float(data[position]['free'])
    
            self.gateway.onPosition(pos)            
    
    #----------------------------------------------------------------------
    def onQueryTrade(self, data, request):
        for d in reversed(data):
                
            # Filter trade update with no trade volume and side (funding)
            if not d["lastQty"] or not d["side"]:
                continue
    
            tradeid = d["execID"]

            trade = VtTradeData()
            trade.gatewayName = self.gateway.gatewayName
            trade.exchange = EXCHANGE_BITMEX
            trade.symbol = d['symbol']
            trade.vtSymbol = '.'.join([trade.symbol, trade.exchange])
        
            #self.tradeID += 1
            trade.orderID = d['clOrdID'] # to record the client ID
            trade.tradeID = tradeid
            trade.vtTradeID = '.'.join([trade.tradeID, trade.gatewayName])
            trade.orderSysID = d["orderID"]
            trade.vtOrderID =  d['clOrdID']
            trade.commission = d['commission']
            trade.volume = d["lastQty"]
            trade.price = d["lastPx"]
            trade.direction = DIRECTION_BITMEX2VT[d["side"]]
            #trade.offset = order.offset
            
            trade.tradeTime = d["timestamp"][:-1] # remove Z
        
            self.gateway.onTrade(trade)   
    
    #----------------------------------------------------------------------
    def onQueryOrder(self, data, request):  # type: (dict, Request)->None
        """"""
        for d in reversed(data):
            sysid = d["orderID"]
            
            if '08b' in sysid or 'a17' in sysid:
                print("")
                
            if d["clOrdID"] != EMPTY_STRING:
                orderid = d["clOrdID"]
            else:
                orderid = sysid

            # time = d["timestamp"][11:19]
            order = VtOrderData()
        
            order.gatewayName = self.gateway.gatewayName
            
            if d['clOrdID'] != EMPTY_STRING:
                order.orderID = orderid.split('.')[-1]
                order.vtOrderID = orderid
            else:
                #order.orderID = orderid
                order.vtOrderID = '.'.join([order.gatewayName, orderid])
        
            order.exchange = EXCHANGE_BITMEX
            order.symbol = d['symbol']
            order.vtSymbol = '.'.join([order.symbol, order.exchange])
            order.orderType = PRICETYPE_BITMEX2VT.get(d['ordType'])
            if order.orderType in [PRICETYPE_MARKETIFTOUCHED, PRICETYPE_STOP, PRICETYPE_MARKETPRICE]:
                order.price = 'Market'
            elif 'price' in d and d['price']:
                order.price = float(d["price"])
            order.totalVolume = float(d["orderQty"])
            order.direction = DIRECTION_BITMEX2VT[d["side"]]           
            order.orderSysID = sysid
            order.orderTime = time.mktime(time.strptime(d['transactTime'][:-1]+'000Z', "%Y-%m-%dT%H:%M:%S.%fZ"))#[:-1] # remove Z
            #self.orders[sysid] = order
           
            order.status = ORDSTATUS_BITMEX2VT.get(d.get('ordStatus', None))
 
            order.tradedVolume = float(d['cumQty'])
            if order.status == STATUS_CANCELLED:
                order.cancelTime = d['timestamp'][:-1] # remove Z
            if 'text' in d:
                order.statusMsg = d['text']            
            self.gateway.onOrder(order)            

    #----------------------------------------------------------------------
    def onQueryBar(self, data, request):
        """"""
        e = request.extra.split('_')
        l = len(data)
        index = 0
        for d in reversed(data):
            bar = VtBarData()
            
            bar.symbol = d['symbol']        # 代码
            bar.interval = e[1]       # K线周期.
            bar.exchange = EXCHANGE_BITMEX
            bar.vtSymbol = '.'.join([bar.symbol, bar.exchange])
        
            bar.open = float(d['open'])             # OHLCV
            bar.high = float(d['high'])
            bar.low = float(d['low'])
            bar.close = float(d['close'])
            bar.volume = float(d['volume']) 
            
            dt = datetime.strptime(d['timestamp'][:-1]+'000Z', '%Y-%m-%dT%H:%M:%S.%fZ')
            if 'm' in bar.interval:
                bar.datetime = dt - timedelta(minutes=int(bar.interval[:-1]))
            elif 'd' in bar.interval:
                bar.datetime = dt - timedelta(days=int(bar.interval[:-1]))
            elif 'h' in bar.interval:
                bar.datetime = dt - timedelta(hours=int(bar.interval[:-1]))
                
            bar.date = bar.datetime.strftime('%Y-%m-%d')
            bar.time = bar.datetime.strftime('%H:%M:%S.%f')[:-3]                
            
            index += 1
            if index == l:
                bar.lastBar = True
                
            self.gateway.onBar(bar)
            
    #----------------------------------------------------------------------
    def onQueryContract(self, data, request):  # type: (dict, Request)->None
        """"""
        if len(data):
            self.gateway.writeLog(' '.join([EXCHANGE_BITMEX, 'instruments query completed']))
        
        for d in data:
            contract = VtContractData()
            contract.gatewayName = self.gatewayName

            contract.symbol = d['symbol']
            contract.exchange = EXCHANGE_BITMEX
            if d['typ'] == 'FFCCSX':
                contract.productClass = PRODUCT_FUTURES
            elif d ['typ'] == 'FFWCSX':
                contract.productClass = PRODUCT_SWAP
            elif d ['typ'] == 'OPECCS':
                contract.productClass = PRODUCT_UNKNOWN
                
            contract.vtSymbol = '.'.join([contract.symbol, contract.exchange])

            contract.name = contract.vtSymbol
            contract.priceTick = d['tickSize']
            contract.size = d['lotSize']
            
            self.gateway.onContract(contract)
            
        #self.queryAccount()   
        self.queryOrder()
        self.queryTrade()
        self.queryPos()
        

    
    #----------------------------------------------------------------------
    def onSendOrder(self, data, request):  # type: (dict, Request)->None
        """"""
        pass
    
    #----------------------------------------------------------------------
    def onCancelOrder(self, data, request):  # type: (dict, Request)->None
        """"""
        pass
            
    #----------------------------------------------------------------------        
    def on_send_order_failed(self, status_code, request):
        """
        Callback when sending order failed on server.
        """
        #order = request.extra
        #order.status = STATUS_REJECTED
        #self.gateway.onOrder(order)

        msg = request.response.text
        self.gateway.writeLog(msg)

    #----------------------------------------------------------------------
    def on_send_order_error(self, exception_type, exception_value, tb, request):
        """
        Callback when sending order caused exception.
        """
        return
        order = request.extra
        order.status = STATUS_REJECTED
        self.gateway.on_order(order)

        # Record exception if not ConnectionError
        #if not issubclass(exception_type, ConnectionError):
            #self.on_error(exception_type, exception_value, tb, request)

    def on_cancel_order_error(self, exception_type, exception_value, tb, request):
        """
        Callback when cancelling order failed on server.
        """
        # Record exception if not ConnectionError
        if not issubclass(exception_type, ConnectionError):
            self.on_error(exception_type, exception_value, tb, request)

