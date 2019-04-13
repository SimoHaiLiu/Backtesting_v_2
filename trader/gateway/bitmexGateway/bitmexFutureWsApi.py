# encoding: UTF-8
'''
Deribit期货WS接口
'''

from apiBase.websocket import WebsocketClient
from bitmexConsts import *
from bitmexUtils import _split_url, createSignature
from trader.vtGateway import *
from trader.vtObject import VtTickData, VtMarketTradeData
from datetime import datetime
from copy import copy
import dateutil.parser as dp

########################################################################
class BitmexFutureTradeWsApi(WebsocketClient):
    
    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """"""
        super(BitmexFutureTradeWsApi, self).__init__(gateway)
        
        self.reqID = 10000
        
        self.accountDict = gateway.accountDict
        self.orderDict = gateway.orderDict
        self.orderLocalDict = gateway.orderLocalDict
        self.localOrderDict = gateway.localOrderDict
    
    #----------------------------------------------------------------------
    def connect(self, futureSymbols, swapSymbols, apiKey, apiSecret):
        """"""
        self.futureSymbols = futureSymbols
        self.swapSymbols = swapSymbols
        
        super(BitmexFutureTradeWsApi, self).connect(apiKey, apiSecret, WEBSOCKET_HOST)
    

    #----------------------------------------------------------------------
    def subscribeTopic(self):  # type:()->None
        host, path = _split_url(WEBSOCKET_HOST)
        
        # 订阅深度和成交
        self.reqID += 1
        req = {
            "op": "subscribe",
            "args": [

                        "order",
                        #"margin",
                        #"position",
                    ],
            
            #"id": str(self.reqID)     
        }
        req.update(
            createSignature(self.apiKey,
                            'GET',
                            host,
                            path,
                            self.secretKey)
        )        
        self.sendRequest(req)
    
    #----------------------------------------------------------------------
    def onOpen(self):
        """"""
        self.gateway.writeLog(u'Bitmex Trade WS Server connected')
        self.login()
    
    #----------------------------------------------------------------------
    def onMessage(self, data):
        if 'table' in msg:
            if 'orderBook' in msg['table']:# and 'action' in msg :
                for d in msg['data']:
                    self.onMarketDepth(d)                
                #if msg['action'] == 'partial':
                    #self.onMarketDepthPartial(msg['data'])
                #else:
                    #self.onMarketDepthInc(msg['action'], msg['data'])
            elif 'trade' in msg['table']:
                for d in msg['data']:
                    self.onMarketDetail(d)
            elif 'position' in msg['table']:
                for d in msg['data']:
                    self.onPosition(d)
        elif 'request' in msg and msg['request']['op'] == u'authKeyExpires':
            self.onLogin()
        else:
            print(msg)
            
    #----------------------------------------------------------------------
    def login(self):

        host, path = _split_url(WEBSOCKET_HOST)

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
class BitmexFutureMarketWsApi(WebsocketClient):
    
    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """"""
        super(BitmexFutureMarketWsApi, self).__init__(gateway)
        
        self.reqID = 10000
        self.tickDict = {}
        self.mtDict = {}
        self.asks = {}
        self.bids = {}
        self.accounts = {}
        self.orders = {}
        self.trades = set()
        
    #----------------------------------------------------------------------
    def connect(self, futureSymbols, swapSymbols, apiKey, apiSecret):
        """"""
        self.futureSymbols = futureSymbols
        self.swapSymbols = swapSymbols
        
        super(BitmexFutureMarketWsApi, self).connect(apiKey, apiSecret, WEBSOCKET_HOST)
    
    #----------------------------------------------------------------------
    def onOpen(self):
        """"""
        self.gateway.writeLog(u'Bitmex Market WS Server Connected')
        self.login()
    
    #----------------------------------------------------------------------
    def onLogin(self):
        """"""
        self.gateway.writeLog(u'Bitmex Market WS Server Logged In')
        self.subscribeTopic(PRODUCT_FUTURES) 
        self.subscribeTopic(PRODUCT_SWAP)  
        # subscribe trade related topics
        self.reqID += 1
        req = {
            "op": "subscribe",
            "args": [

                        "order",
                        "execution",
                        "position",
                    ],
            
            #"id": str(self.reqID)     
        }
        self.sendRequest(req, auth=False)  
        
    #----------------------------------------------------------------------
    def login(self):

        host, path = _split_url(WEBSOCKET_HOST)

        params = {
            'op': 'authKeyExpires',
        }
        sign = createSignature(self.apiKey,
                                        'GET',
                                        host,
                                        path,
                                        self.secretKey)
        
        print sign
        params["args"] = sign
        
        return self.sendRequest(params)
    
    #----------------------------------------------------------------------
    def subscribeTopic(self, type_, symbol=None):  # type:()->None
        """
        """
        if not symbol:
            if type_ == PRODUCT_FUTURES:
                symbols = self.futureSymbols
            elif type_ == PRODUCT_SWAP:
                symbols = self.swapSymbols
        else:
            if symbol in self.futureSymbols+self.swapSymbols:
                return False
            else:
                symbols = [symbol]
            
        for symbol in symbols:
            # 创建Tick对象
            tick = VtTickData()
            #tick.gatewayName = self.gatewayName
            tick.symbol = symbol
            tick.productClass = type_
            tick.exchange = EXCHANGE_BITMEX
            tick.vtSymbol = '.'.join([tick.symbol, tick.exchange])
            self.tickDict[symbol] = tick            
            
            mt = VtMarketTradeData()
            mt.symbol = symbol
            mt.productClass = type_
            mt.exchange = EXCHANGE_BITMEX
            mt.vtSymbol = '.'.join([mt.symbol, mt.exchange])
            self.mtDict[symbol] = mt
            
            # 订阅深度和成交
            self.reqID += 1
            req = {
                "op": "subscribe",
                "args": [
                            "orderBook10:%s" %symbol,
                            "trade:%s" %symbol,
                        ],
                
                #"id": str(self.reqID)     
            }
            self.sendRequest(req, auth=False)
            
            self.asks[symbol] = {}
            self.bids[symbol] = {}
        
        return True
    
    #----------------------------------------------------------------------  
    def addSymbol(self, type_, symbol):
        if type_ == PRODUCT_FUTURES:
            self.futureSymbols.append(symbol)
        elif type_ == PRODUCT_SWAP:
            self.swapSymbols.append(symbol)
            
    #----------------------------------------------------------------------
    def onMessage(self, msg):  # type: (dict)->None
        """"""
        #print(msg)
        if 'table' in msg:
            if msg['table'] == 'order' :
                for d in msg['data']:
                    self.onOrder(d)
            if 'execution' in msg['table']:
                for d in msg['data']:
                    self.onTrade(d)
                            
            elif 'orderBook' in msg['table']:# and 'action' in msg :
                for d in msg['data']:
                    self.onMarketDepth(d)                
                #if msg['action'] == 'partial':
                    #self.onMarketDepthPartial(msg['data'])
                #else:
                    #self.onMarketDepthInc(msg['action'], msg['data'])
            elif 'trade' in msg['table']:
                for d in msg['data']:
                    self.onMarketDetail(d)
            
            elif 'position' in msg['table']:
                for d in msg['data']:
                    self.onPosition(d)
        elif 'request' in msg and msg['request']['op'] == u'authKeyExpires':
            self.onLogin()
        else:
            print(msg)
            #self.gateway.writeLog(u'错误代码：%s, 信息：%s' %(data['err-code'], data['err-msg']))
        
    #----------------------------------------------------------------------
    def onOrder(self, d):
        print 'onOrder'

        sysid = d["orderID"]
        order = self.orders.get(sysid, None)
        if not order:
            order = VtOrderData()
        if d["clOrdID"] != EMPTY_STRING:
            orderid = d["clOrdID"]
        else:
            orderid = sysid

        # time = d["timestamp"][11:19]
        
    
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
        order.orderSysID = sysid
        
        if 'price' in d and d['price']: 
            order.price = float(d["price"])
        
        if 'orderQty' in d and d['orderQty']:
            order.totalVolume = float(d["orderQty"])
        if 'side' in d and d['side'] != EMPTY_STRING:
            order.direction = DIRECTION_BITMEX2VT.get(d["side"])  
        if 'ordType' in d:
            order.orderType = PRICETYPE_BITMEX2VT.get(d['ordType'])
            if order.orderType in [PRICETYPE_MARKETIFTOUCHED, PRICETYPE_STOP, PRICETYPE_MARKETPRICE]:
                order.price = 'Market'              
        
        if 'transactTime' in d:
            order.orderTime = time.mktime(time.strptime(d['transactTime'][:-1]+'000Z', "%Y-%m-%dT%H:%M:%S.%fZ"))#[:-1] # remove Z
        
        if 'ordStatus' in d:
            order.status = ORDSTATUS_BITMEX2VT.get(d.get('ordStatus', None))
            if order.status not in [STATUS_CANCELLED, STATUS_REJECTED]:
                order.tradedVolume = float(d['cumQty'])
                if order.status == STATUS_NOTTRADED and order.orderType in [PRICETYPE_LIMITIFTOUCHED,PRICETYPE_MARKETIFTOUCHED,PRICETYPE_STOPLIMIT,PRICETYPE_STOP]:
                    order.status = STATUS_UNTRIGGERED
            else:
                if 'text' in d:
                    order.statusMsg = d['text']
                if order.status == STATUS_CANCELLED:
                    order.cancelTime = d['timestamp'][:-1] # remove Z
        else:
            if 'triggered' in d:
                order.status = ORDSTATUS_BITMEX2VT.get(d.get('triggered', None))   
        
        self.orders[sysid] = order
        self.gateway.onOrder(copy(order))        

    #-----------------------------------------------------------------------
    def onTrade(self, d):
        """"""
        print 'onTrade'
        # Filter trade update with no trade volume and side (funding)
        if not d["lastQty"] or not d["side"]:
            return

        tradeid = d["execID"]
        if tradeid in self.trades:
            return
        self.trades.add(tradeid)

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
    def onPosition(self, d):
        """"""
        #print 'onPosition'
        if 'currentCost' not in d:
            return
        
        pos = VtPositionData()
        pos.gatewayName = self.gateway.gatewayName
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
    def on_account(self, d):
        """"""
        accountid = str(d["account"])
        account = self.accounts.get(accountid, None)
        if not account:
            account = AccountData(accountid=accountid,
                                  gateway_name=self.gateway_name)
            self.accounts[accountid] = account

        account.balance = d.get("marginBalance", account.balance)
        account.available = d.get("availableMargin", account.available)
        account.frozen = account.balance - account.available

        self.gateway.on_account(copy(account))
        
    #----------------------------------------------------------------------
    def onMarketDepthPartial(self, data):
        for d in data:
            tick = self.tickDict.get(d['symbol'], None)
            if not tick:
                return    
            
            if 'Sell' in d['side']:
                self.asks[d['symbol']][d['id']] = [d['price'],d['size']]
            elif 'Buy' in d['side']:
                self.bids[d['symbol']][d['id']] = [d['price'],d['size']]
                
    
    #----------------------------------------------------------------------
    def onMarketDepthInc(self, action, data):
        for d in data:
            tick = self.tickDict.get(d['symbol'], None)
            if not tick:
                return 
            
            if action == 'update':
                if 'Sell' in d['side']:
                    self.asks[d['symbol']][d['id']][1] = d['size']
                elif 'Buy' in d['side']:
                    self.bids[d['symbol']][d['id']][1] = d['size']
            elif action == 'insert':
                if 'Sell' in d['side']:
                    self.asks[d['symbol']][d['id']] = [d['price'],d['size']]
                elif 'Buy' in d['side']:
                    self.bids[d['symbol']][d['id']] = [d['price'],d['size']]               
            elif action == 'delete':
                if 'Sell' in d['side']:
                    del self.asks[d['symbol']][d['price']] 
                elif 'Buy' in d['side']:
                    del self.bids[d['symbol']][d['price']] 
            
            # sorting
            asks = sorted(self.asks[d['symbol']].items(), key=lambda item:item[1][0])
            bids = sorted(self.bids[d['symbol']].items(), key=lambda item:item[1][0], reverse=True)  
            
            for n in range(DIS_DEPTH):
                l = bids[n][1]
                #print l
                tick.__setattr__('bidPrice' + str(n+1), float(l[0]))
                tick.__setattr__('bidVolume' + str(n+1), float(l[1]))
    
            for n in range(DIS_DEPTH):
                l = asks[n][1]
                #print l
                tick.__setattr__('askPrice' + str(n+1), float(l[0]))
                tick.__setattr__('askVolume' + str(n+1), float(l[1]))
    
            self.gateway.onTick(copy(tick))        
    #----------------------------------------------------------------------
    # this function handles the orderBook10 subscriptions
    def onMarketDepth(self, data):
        """行情深度推送 """
        tick = self.tickDict.get(data['symbol'], None)
        if not tick:
            return

        #tick.date = datetime.strftime('%Y%m%d')
        #tick.time = datetime.fromtimestamp(float(data['tstamp'])/1000).strftime('%H:%M:%S.%f')[:-3]
        localTime = datetime.now()
        ts = dp.parse(str(data['timestamp']))#+dt.timedelta(hours=8)
        tss = ts.strftime('%H:%M:%S.%f')[:-3]
        #if tss[:-2] == tick.time[:-2]:
            #return        
        tick.time = tss
        lt = localTime.strftime('%H:%M:%S.%f')[:-3]
        td = (localTime-ts.replace(tzinfo = None)).total_seconds()
        if td>2:
            pass#print 'BM',data['symbol'],lt, tick.time, td  
            
        tick.datetime = datetime.strptime(data["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
        
        for n in range(MAX_HC_NUM):
            try:
                l = data['bids'][n]
                tick.bidPrice[n] = float(l[0])
                tick.bidVolume[n] = float(l[1])
            except IndexError:
                break
    
        for n in range(MAX_HC_NUM):
            try:
                l = data['asks'][n]
                tick.askPrice[n] = float(l[0])
                tick.askVolume[n] = float(l[1])
            except IndexError:
                break

        self.gateway.onTick(copy(tick))

    #----------------------------------------------------------------------
    def onMarketDetail(self, data):
        """市场细节推送"""
        symbol = data['symbol']

        tick = self.tickDict.get(symbol, None)
        if not tick:
            return

        #tick.time = datetime.fromtimestamp(float(data['tstamp'])/1000).strftime('%H:%M:%S.%f')[:-3]
        localTime = datetime.now()
        ts = dp.parse(str(data['timestamp']))#+dt.timedelta(hours=8)
        tss = ts.strftime('%H:%M:%S.%f')[:-3]
        #if tss[:-2] == tick.time[:-2]:
            #return
        tick.time = tss
        lt = localTime.strftime('%H:%M:%S.%f')[:-3]
        td = (localTime-ts.replace(tzinfo = None)).total_seconds()
        if td>2:
            pass#print 'BM',data['symbol'],lt, tick.time, td 

        #tick.openPrice = float(data['open'])
        #tick.highPrice = float(data['high'])
        #tick.lowPrice = float(data['low'])
        tick.lastPrice = float(data['price'])
        #tick.volume = float(data['vol'])
        #tick.preClosePrice = float(tick.openPrice)

        self.gateway.onTick(copy(tick))
        
        
    #----------------------------------------------------------------------
    def onMarketDetail1(self, data):
        mt = self.mtDict.get(data['symbol'], None)
        if not mt:
            return
        
        localTime = datetime.now()
        ts = dp.parse(str(data['timestamp']))#+dt.timedelta(hours=8)
        tss = ts.strftime('%H:%M:%S.%f')[:-3]
        #if tss[:-2] == tick.time[:-2]:
            #return
        mt.time = tss
        lt = localTime.strftime('%H:%M:%S.%f')[:-3]
        td = (localTime-ts.replace(tzinfo = None)).total_seconds()
        if td>2:
            pass
        
        mt.price = data['price']          
        mt.direction = DIRECTION_BITMEX2VT.get(data['side'])      
        mt.volume = float(data['size'])                 
        mt.grossValue = float(data['grossValue'])           
        mt.homeNotional = float(data['homeNotional'])
        mt.foreignNotional = float(data['homeNotional'])
       
        self.gateway.onMarketTrade(copy(mt))