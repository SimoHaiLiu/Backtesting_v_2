# encoding: UTF-8
'''
Deribit期货WS接口
'''

from gateway.apiBase.websocket.WebsocketClient import WebsocketClient 
from deribitConsts import *
from vtGateway import *
from datetime import datetime
from copy import copy



########################################################################
class DeribitOptionWsApi(WebsocketClient):
    
    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """"""
        super(DeribitOptionWsApi, self).__init__(gateway)
        
        self.reqID = 10000
        
        self.accountDict = gateway.accountDict
        self.orderDict = gateway.orderDict
        self.orderLocalDict = gateway.orderLocalDict
        self.localOrderDict = gateway.localOrderDict
    
    #----------------------------------------------------------------------
    def connect(self, symbols, apiKey, apiSecret):
        """"""
        self.symbols = symbols
        
        super(DeribitOptionWsApi, self).connect(apiKey, 
                                                    apiSecret,
                                                    FUTURE_WEBSOCKET_HOST)
    
    #----------------------------------------------------------------------
    def subscribeTopic(self):
        """"""
        # 订阅资金变动
        self.reqID += 1
        req = {
            "op": "sub",
            "cid": str(self.reqID),
            "topic": "accounts"            
        }
        self.sendRequest(req)
        
        # 订阅委托变动
        for symbol in self.symbols:
            self.reqID += 1
            req = {
                "op": "sub",
                "cid": str(self.reqID),
                "topic": 'orders.%s' %symbol            
            }
            self.sendRequest(req)
    
    #----------------------------------------------------------------------
    def onOpen(self):
        """"""
        self.gateway.writeLog(u'Huobi Future WS Server connected')
        self.login()
    
    #----------------------------------------------------------------------
    def onMessage(self, data):
        if 'accounts' in data:
            self.onAccount()
        elif 'order.' in data:
            self.onOrder()
        elif "op" in data and data["op"] == "auth":
            self.onLogin()  
            
    #----------------------------------------------------------------------
    def login(self):

        host, path = _split_url(FUTURE_WEBSOCKET_HOST)

        params = {
            'op': 'auth',
        }
        params.update(
            createSignature(self.apiKey,
                            'GET',
                            host,
                            path,
                            self.secretKey)
        )
        return self.sendRequest(params)
    
    #----------------------------------------------------------------------
    def onLogin(self):
        """"""
        self.gateway.writeLog(u'Huobi Future WS Server Logged In')
        
        self.subscribeTopic()
        
    #----------------------------------------------------------------------
    def onMessage(self, msg):  # type: (dict)->None
        """"""
        op = msg.get('op', None)
        #if op != 'notify':
            #return
        if op == "auth":
            self.onLogin()  
            return
        
        if 'data' in msg:
            topic = msg['topic']
            if topic == 'accounts':
                self.onAccount(msg['data'])
            elif 'orders' in topic:
                self.onOrder(msg['data'])
        
    #----------------------------------------------------------------------
    def onAccount(self, data):
        """"""
        for d in data['list']:
            account = self.accountDict.get(d['currency'], None)
            if not account:
                continue
            
            if d['type'] == 'trade':
                account.available = float(d['balance'])
            elif d['type'] == 'frozen':
                account.margin = float(d['balance'])
            
            account.balance = account.margin + account.available   
            self.gateway.onAccount(account)

    #----------------------------------------------------------------------
    def onOrder(self, data):
        """"""
        orderID = data['order-id']
        strOrderID = str(orderID)
        order = self.orderDict.get(strOrderID, None)
        
        if not order:
            self.gateway.localID += 1
            localID = str(self.gateway.localID)

            self.orderLocalDict[strOrderID] = localID
            self.localOrderDict[localID] = strOrderID

            order = VtOrderData()
            order.gatewayName = self.gatewayName
    
            order.orderID = localID
            order.vtOrderID = '.'.join([order.gatewayName, order.orderID])
    
            order.symbol = data['symbol']
            order.exchange = EXCHANGE_HUOBI
            order.vtSymbol = '.'.join([order.symbol, order.exchange])
    
            order.price = float(data['order-price'])
            order.totalVolume = float(data['order-amount'])
            
            dt = datetime.fromtimestamp(data['created-at']/1000)
            order.orderTime = dt.strftime('%H:%M:%S')
            
            if 'buy' in data['order-type']:
                order.direction = DIRECTION_LONG
            else:
                order.direction = DIRECTION_SHORT
            order.offset = OFFSET_NONE          
            
            self.orderDict[strOrderID] = order
        
        order.tradedVolume += float(data['filled-amount'])
        order.status = statusMapReverse.get(data['order-state'], STATUS_UNKNOWN)        
        self.gateway.onOrder(order)
        
        if float(data['filled-amount']):
            trade = VtTradeData()
            trade.gatewayName = self.gatewayName
    
            trade.tradeID = str(data['seq-id'])
            trade.vtTradeID = '.'.join([trade.tradeID, trade.gatewayName])
    
            trade.symbol = data['symbol']
            trade.exchange = EXCHANGE_HUOBI
            trade.vtSymbol = '.'.join([trade.symbol, trade.exchange])
            trade.direction = order.direction
            trade.offset = order.offset
            trade.orderID = order.orderID
            trade.vtOrderID = order.vtOrderID
            
            trade.price = float(data['price'])
            trade.volume = float(data['filled-amount'])
    
            dt = datetime.now()
            trade.tradeTime = dt.strftime('%H:%M:%S')
    
            self.gateway.onTrade(trade)

        
########################################################################
class DeribitOptionMarketWsApi(WebsocketClient):
    
    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """"""
        super(DeribitOptionMarketWsApi, self).__init__(gateway)
        
        self.reqID = 10000
        self.tickDict = {}
    
    #----------------------------------------------------------------------
    def connect(self, symbols, apiKey, apiSecret):
        """"""
        self.symbols = symbols
        
        super(DeribitOptionMarketWsApi, self).connect(apiKey, 
                                                     apiSecret,
                                                     FUTURE_WEBSOCKET_HOST)
    
    #----------------------------------------------------------------------
    def onOpen(self):
        """"""
        self.gateway.writeLog(u'Deribit Option Market WS Server Connected')
        self.subscribeTopic()
    
    #----------------------------------------------------------------------
    def subscribeTopic(self):  # type:()->None
        """
        """
        for symbol in self.symbols:
            # 创建Tick对象
            tick = VtTickData()
            #tick.gatewayName = self.gatewayName
            tick.symbol = symbol
            tick.productClass = PRODUCT_OPTION
            tick.exchange = EXCHANGE_DERIBIT
            tick.vtSymbol = '.'.join([tick.symbol, tick.exchange, tick.productClass])
            self.tickDict[symbol] = tick            
            
            # 订阅深度和成交
            self.reqID += 1
            req = {
                "action": "/api/v1/private/subscribe",
                "arguments": {
                               "event": ["order_book"],
                               "instrument": ["options"],
                               "depth": SUB_DEPTH
                            }  
                
                #"id": str(self.reqID)     
            }
            self.sendRequest(req, auth=True)
            
            #self.reqID += 1
            #req = {
                #"sub": "market.%s.detail" %symbol,
                #"id": str(self.reqID)     
            #}
            #self.sendRequest(req)
    
    #----------------------------------------------------------------------
    def onMessage(self, msg):  # type: (dict)->None
        """"""
        if 'notifications' in msg:
            if msg['notifications'][0]['message'] == 'order_book_event':
                self.onMarketDepthAndDetail(msg['notifications'][0]['result'])
            #elif 'detail' in msg['ch']:
                #self.onMarketDetail(msg['notifications'][0]['result'])
        else:
            print(msg)
            #self.gateway.writeLog(u'错误代码：%s, 信息：%s' %(data['err-code'], data['err-msg']))
        
    #----------------------------------------------------------------------
    def onMarketDepthAndDetail(self, data):
        """行情深度推送 """
        tick = self.tickDict.get(data['instrument'], None)
        if not tick:
            return

        #tick.date = datetime.strftime('%Y%m%d')
        #tick.time = datetime.fromtimestamp(float(data['tstamp'])/1000).strftime('%H:%M:%S.%f')[:-3]
        
        localTime = datetime.now()
        ts = datetime.fromtimestamp(float(data['tstamp'])/1000)
        tick.time = ts.strftime('%H:%M:%S.%f')[:-3]
        lt = localTime.strftime('%H:%M:%S.%f')[:-3]
        td = (localTime-ts).total_seconds()
        if td>0:
            print data['instrument'],lt, tick.time, td
            
        #tick.openPrice = float(data['open'])
        tick.highPrice = float(data['high'])
        tick.lowPrice = float(data['low'])
        tick.lastPrice = float(data['last'])
        #tick.volume = float(data['vol'])
        #tick.preClosePrice = float(tick.openPrice)        
        
        try:
            for n in range(DIS_DEPTH):
                l = data['bids'][n]
                tick.__setattr__('bidPrice' + str(n+1), float(l['price']))
                tick.__setattr__('bidVolume' + str(n+1), float(l['quantity']))
    
            for n in range(DIS_DEPTH):
                l = data['asks'][n]
                tick.__setattr__('askPrice' + str(n+1), float(l['price']))
                tick.__setattr__('askVolume' + str(n+1), float(l['quantity']))
        except IndexError:
            pass
        
        self.gateway.onMtick(copy(tick))

    #----------------------------------------------------------------------
    def onMarketDetail(self, data):
        """市场细节推送"""
        symbol = data['instrument']

        tick = self.tickDict.get(symbol, None)
        if not tick:
            return

        tick.datetime = datetime.fromtimestamp(data['tstamp']/1000)
        tick.date = tick.datetime.strftime('%Y%m%d')
        tick.time = tick.datetime.strftime('%H:%M:%S.%f')

        #tick.openPrice = float(data['open'])
        tick.highPrice = float(data['high'])
        tick.lowPrice = float(data['low'])
        tick.lastPrice = float(data['last'])
        #tick.volume = float(data['vol'])
        tick.preClosePrice = float(tick.openPrice)

        if tick.bidPrice1:
            newtick = copy(tick)
            self.gateway.onMtick(newtick)