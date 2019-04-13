# encoding: UTF-8
'''
火币现货REST交易接口
'''
from datetime import datetime
from vtGateway import *
from gateway.apiBase.rest.RestClient import Request, RestClient
from coinbaseUtils import _split_url, createSignature
from coinbaseConsts import *

########################################################################
class CoinbaseSpotRestApi(RestClient):
    
    #----------------------------------------------------------------------
    def __init__(self, gateway):  # type: (VtGateway)->CoinbaseSpotRestApi
        """"""
        super(CoinbaseSpotRestApi, self).__init__()
        
        self.gateway = gateway
        self.gatewayName = gateway.gatewayName
        
        self.symbols = []
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
        request.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36"
        }
        paramsWithSignature = createSignature(self.apiKey,
                                           request.method,
                                           self.signHost,
                                           request.path,
                                           self.apiSecret,
                                           request.params)
        request.params = paramsWithSignature
   
        if request.method == "POST":
            request.headers['Content-Type'] = 'application/json'
   
            if request.data:
                request.data = json.dumps(request.data)
   
        return request
    
    #----------------------------------------------------------------------
    def connect(self, symbols, apiKey, apiSecret, sessionCount=3):
        """连接服务器"""
        self.symbols = symbols
        self.apiKey = apiKey
        self.apiSecret = apiSecret
        
        host, path = _split_url(SPOT_REST_HOST)
        self.init(SPOT_REST_HOST)
        
        self.signHost = host
        self.start(sessionCount)
        
        self.queryContract()
    
    #----------------------------------------------------------------------
    def queryAccount(self):
        """"""
        self.addRequest('GET', '/v1/account/accounts', self.onQueryAccount)
    
    #----------------------------------------------------------------------
    def queryAccountBalance(self):
        """"""
        path = '/v1/account/accounts/%s/balance' %self.accountid
        self.addRequest('GET', path, self.onQueryAccountBalance)
    
    #----------------------------------------------------------------------
    def queryOrder(self):
        """"""
        path = '/v1/order/orders'
        
        todayDate = datetime.now().strftime('%Y-%m-%d')
        statesActive = 'submitted,partial-filled'
        
        for symbol in self.symbols:
            params = {
                'symbol': symbol,
                'states': statesActive,
                'end_date': todayDate
            }
            self.addRequest('GET', path, self.onQueryOrder, params=params)

    #----------------------------------------------------------------------
    def queryContract(self):
        """"""
        self.addRequest('GET', '/v1/common/symbols', self.onQueryContract)
    
    #----------------------------------------------------------------------
    def sendOrder(self, orderReq):
        """"""
        self.gateway.localID += 1
        localID = str(self.gateway.localID)
        vtOrderID = '.'.join([self.gatewayName, localID])

        if orderReq.direction == DIRECTION_LONG:
            type_ = 'buy-limit'
        else:
            type_ = 'sell-limit'
        
        params = {
            'account-id': self.accountid,
            'amount': str(orderReq.volume),
            'symbol': orderReq.symbol,
            'type': type_,
            'price': str(orderReq.price),
            'source': 'api'
        }
        
        path = '/v1/order/orders/place'
        self.addRequest('POST', path, self.onSendOrder, 
                        data=params, extra=localID)
        
        # 缓存委托
        order = VtOrderData()
        order.gatewayName = self.gatewayName

        order.orderID = localID
        order.vtOrderID = '.'.join([order.gatewayName, order.orderID])

        order.symbol = orderReq.symbol
        order.exchange = EXCHANGE_HUOBI
        order.vtSymbol = '.'.join([order.symbol, order.exchange])

        order.price = orderReq.price
        order.totalVolume = orderReq.volume
        order.direction = orderReq.direction
        order.offset = OFFSET_NONE
        order.status = STATUS_UNKNOWN
        
        self.orderBufDict[localID] = order

        # 返回订单号
        return vtOrderID
    
    #----------------------------------------------------------------------
    def cancelOrder(self, cancelReq):
        """"""
        localID = cancelReq.orderID
        orderID = self.localOrderDict.get(localID, None)

        if orderID:
            path = '/v1/order/orders/%s/submitcancel' %orderID
            self.addRequest('POST', path, self.onCancelOrder)
            
            if localID in self.cancelReqDict:
                del self.cancelReqDict[localID]
        else:
            self.cancelReqDict[localID] = cancelReq        
    
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
        
        self.queryOrder()
    
    #----------------------------------------------------------------------
    def onQueryOrder(self, data, request):  # type: (dict, Request)->None
        """"""
        status = data.get('status', None)
        if status == 'error':
            msg = u'错误代码：%s, 错误信息：%s' %(data['err-code'], data['err-msg'])
            self.gateway.writeLog(msg)
            return
        
        symbol = request.params['symbol']
        self.gateway.writeLog(u'%s委托信息查询成功' %symbol)
        
        data['data'].reverse()
        for d in data['data']:
            orderID = d['id']
            strOrderID = str(orderID)

            self.gateway.localID += 1
            localID = str(self.gateway.localID)

            self.orderLocalDict[strOrderID] = localID
            self.localOrderDict[localID] = strOrderID

            order = VtOrderData()
            order.gatewayName = self.gatewayName

            order.orderID = localID
            order.vtOrderID = '.'.join([order.gatewayName, order.orderID])

            order.symbol = d['symbol']
            order.exchange = EXCHANGE_HUOBI
            order.vtSymbol = '.'.join([order.symbol, order.exchange])

            order.price = float(d['price'])
            order.totalVolume = float(d['amount'])
            order.tradedVolume = float(d['field-amount'])
            order.status = statusMapReverse.get(d['state'], STATUS_UNKNOWN)

            if 'buy' in d['type']:
                order.direction = DIRECTION_LONG
            else:
                order.direction = DIRECTION_SHORT
            order.offset = OFFSET_NONE
            
            order.orderTime = datetime.fromtimestamp(d['created-at']/1000).strftime('%H:%M:%S')
            if d['canceled-at']:
                order.cancelTime = datetime.fromtimestamp(d['canceled-at']/1000).strftime('%H:%M:%S')

            self.orderDict[strOrderID] = order
            self.gateway.onOrder(order)

    #----------------------------------------------------------------------
    def onQueryContract(self, data, request):  # type: (dict, Request)->None
        """"""
        status = data.get('status', None)
        if status == 'error':
            msg = u'错误代码：%s, 错误信息：%s' %(data['err-code'], data['err-msg'])
            self.gateway.writeLog(msg)
            return
        
        self.gateway.writeLog(u'合约信息查询成功')
        
        for d in data['data']:
            contract = VtContractData()
            contract.gatewayName = self.gatewayName

            contract.symbol = d['base-currency'] + d['quote-currency']
            contract.exchange = EXCHANGE_HUOBI
            contract.vtSymbol = '.'.join([contract.symbol, contract.exchange])

            contract.name = '/'.join([d['base-currency'].upper(), d['quote-currency'].upper()])
            contract.priceTick = 1 / pow(10, d['price-precision'])
            contract.size = 1 / pow(10, d['amount-precision'])
            contract.productClass = PRODUCT_SPOT

            self.gateway.onContract(contract)
            
        self.queryAccount()        

    #----------------------------------------------------------------------
    def onSendOrder(self, data, request):  # type: (dict, Request)->None
        """"""
        localID = request.extra
        order = self.orderBufDict[localID]
        
        status = data.get('status', None)
        
        if status == 'error':
            msg = u'错误代码：%s, 错误信息：%s' %(data['err-code'], data['err-msg'])
            self.gateway.writeLog(msg)
                
            order.status = STATUS_REJECTED
            self.gateway.onOrder(order)
            return
        
        orderID = data['data']
        strOrderID = str(orderID)
        
        self.localOrderDict[localID] = strOrderID
        self.orderDict[strOrderID] = order
        
        req = self.cancelReqDict.get(localID, None)
        if req:
            self.cancelOrder(req)
    
    #----------------------------------------------------------------------
    def onCancelOrder(self, data, request):  # type: (dict, Request)->None
        """"""
        status = data.get('status', None)
        if status == 'error':
            msg = u'错误代码：%s, 错误信息：%s' %(data['err-code'], data['err-msg'])
            self.gateway.writeLog(msg)
            return
        
        self.gateway.writeLog(u'委托撤单成功：%s' %data)