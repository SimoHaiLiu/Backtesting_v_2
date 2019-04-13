# encoding: UTF-8

'''
This file implements the strategy trading engine
'''

from __future__ import division

import json
import os
import traceback
from collections import OrderedDict
from datetime import datetime, timedelta
from copy import copy, deepcopy

from trader.vtConstant import *
from trader.vtGateway import *
from trader.vtFunction import todayDate, getJsonPath
from .strBase import *
from .strategy import STRATEGY_CLASS


########################################################################
class StrEngine(object):
    """Str trading engine"""
    settingFileName = 'str_setting.json'
    settingFilePath = getJsonPath(settingFileName, __file__)
    
    STATUS_FINISHED = set([STATUS_REJECTED, STATUS_CANCELLED, STATUS_ALLTRADED])

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 当前日期
        self.today = todayDate()
        
        # 保存策略实例的字典
        # key为策略名称，value为策略实例，注意策略名称不允许重复
        self.strategyDict = {}
        
        # 保存vtSymbol和策略实例映射的字典（用于推送tick数据）
        # 由于可能多个strategy交易同一个vtSymbol，因此key为vtSymbol
        # value为包含所有相关strategy对象的list
        self.tickStrategyDict = {}
        
        # 保存vtOrderID和strategy对象映射的字典（用于推送order和trade数据）
        # key为vtOrderID，value为strategy对象
        self.orderStrategyDict = {}     
        
        # 本地停止单编号计数
        self.stopOrderCount = 0
        # stopOrderID = STOPORDERPREFIX + str(stopOrderCount)
        
        # 本地停止单字典
        # key为stopOrderID，value为stopOrder对象
        self.stopOrderDict = {}             # 停止单撤销后不会从本字典中删除
        self.workingStopOrderDict = {}      # 停止单撤销后会从本字典中删除
        
        # 保存策略名称和委托号列表的字典
        # key为name，value为保存orderID（限价+本地停止）的集合
        self.strategyOrderDict = {}
        
        # 成交号集合，用来过滤已经收到过的成交推送
        self.tradeSet = set()
        
        # 引擎类型为实盘
        self.engineType = ENGINETYPE_TRADING
        
        # RQData数据服务
        self.rq = None
        
        # RQData能获取的合约代码列表
        self.rqSymbolSet = set()
        
        # 初始化RQData服务
        #self.initRqData()
        
        # 注册日式事件类型
        self.mainEngine.registerLogEvent(EVENT_STR_LOG)
        
        # 注册事件监听
        self.registerEvent()
 
    #----------------------------------------------------------------------
    def sendOrder(self, symbol, orderType, price, volume, priceType, stopLossPx=None, takeProfPx=None, strategy=None):
        """发单"""
        contract = self.mainEngine.getContract(symbol)
        
        req = VtOrderReq()
        req.symbol = contract.symbol
        req.exchange = contract.exchange
        req.vtSymbol = contract.vtSymbol
        req.price = self.roundToPriceTick(contract.priceTick, price)
        req.volume = volume
        
        req.productClass = contract.productClass
        #req.currency = contract.currency        
        
        # 设计为CTA引擎发出的委托只允许使用限价单
        req.priceType = priceType
        
        # CTA委托类型映射
        if orderType == STR_ORDER_BUY:
            req.direction = DIRECTION_LONG
            #req.offset = OFFSET_OPEN
            
        elif orderType == STR_ORDER_SELL:
            req.direction = DIRECTION_SHORT
            #req.offset = OFFSET_CLOSE
                
        #elif order['type'] == CTAORDER_SHORT:
            #req.direction = DIRECTION_SHORT
            ##req.offset = OFFSET_OPEN
            
        #elif order['type'] == CTAORDER_COVER:
            #req.direction = DIRECTION_LONG
            #req.offset = OFFSET_CLOSE
            
        # order converter
        if stopLossPx:
            req.stopLossPx = stopLossPx
            #req.priceType = PRICETYPE_STOPLIMIT
            
        if takeProfPx:
            req.takeProfPx = takeProfPx
            
        #reqList = self.convertOrderReq(req, stopLossPx, takeProfPx)
        #vtOrderIDList = []
        
        #if not reqList:
            #return vtOrderIDList
        
        #for convertedReq in reqList:
        vtOrderIDList = self.mainEngine.sendOrder(req, contract.gatewayName)    # 发单
        for vtOrderID in vtOrderIDList:
            self.orderStrategyDict[vtOrderID] = strategy                                 # 保存vtOrderID和策略的映射关系
            self.strategyOrderDict[strategy.name].add(vtOrderID)                         # 添加到策略委托号集合中
        #vtOrderIDList.append(vtOrderID)
            
        #self.writeStrLog(u'策略%s发送委托，%s，%s，%s@%s' 
                         #%(strategy.name, vtSymbol, req.direction, volume, price))
        
        return vtOrderIDList
    
    #----------------------------------------------------------------------
    def convertOrderReq(req, stopLossPx, takeProfPx):
        if req.exchange == EXCHANGE_BITMEX:
            pass
        elif req.exchange in [EXCHANGE_DERIBIT,]: # exchanges do not support bulk orders.
            pass
            #slReq = deepcopy(req)
            #slReq.price = stopLossPx
            #slReq.direction = directionRevMap.get(req.direction)
            
            #spReq = deepcopy(req)
            #spReq.price = takeProfPx
            #spReq.direction = directionRevMap.get(req.direction)  
            
            #return [req, slReq, spReq]
 
    #----------------------------------------------------------------------
    def qryBar(self, strategy, interval='1m', limit=1000):
        gwList = []
        for vtSymbol in strategy.vtSymbols:
            contract = self.mainEngine.getContract(vtSymbol)
            self.mainEngine.qryBar(contract.gatewayName, contract.symbol, interval, limit)
     
    #----------------------------------------------------------------------
    def qryOrder(self, strategy, openOnly=False):
        gwList = []
        for vtSymbol in strategy.vtSymbols:
            gatewayName = self.mainEngine.getContract(vtSymbol).gatewayName
            
            if gatewayName not in gwList:
                self.mainEngine.qryOrder(gatewayName, openOnly)
                gwList.append(gatewayName)
                
    #----------------------------------------------------------------------
    def qryPosition(self, strategy):
        gwList = []
        for vtSymbol in strategy.vtSymbols:
            gatewayName = self.mainEngine.getContract(vtSymbol).gatewayName
            
            if gatewayName not in gwList:
                self.mainEngine.qryPosition(gatewayName)
                gwList.append(gatewayName)        
        
    #----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 查询报单对象
        order = self.mainEngine.getOrder(vtOrderID)
        
        # 如果查询成功
        if order:
            # 检查是否报单还有效，只有有效时才发出撤单指令
            orderFinished = (order.status==STATUS_ALLTRADED or order.status==STATUS_CANCELLED)
            if not orderFinished:
                req = VtCancelOrderReq()
                req.symbol = order.symbol
                req.exchange = order.exchange
                req.frontID = order.frontID
                req.sessionID = order.sessionID
                req.orderID = order.orderSysID # use the sys id 
                self.mainEngine.cancelOrder(req, order.gatewayName)    

    #----------------------------------------------------------------------
    def sendStopOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发停止单（本地实现）"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)
        
        so = StopOrder()
        so.vtSymbol = vtSymbol
        so.orderType = orderType
        so.price = price
        so.volume = volume
        so.strategy = strategy
        so.stopOrderID = stopOrderID
        so.status = STOPORDER_WAITING
        
        if orderType == STR_ORDER_BUY:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_OPEN
        elif orderType == STR_ORDER_SELL:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_CLOSE
        elif orderType == STR_ORDER_SHORT:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_OPEN
        elif orderType == STR_ORDER_COVER:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_CLOSE           
        
        # 保存stopOrder对象到字典中
        self.stopOrderDict[stopOrderID] = so
        self.workingStopOrderDict[stopOrderID] = so
        
        # 保存stopOrderID到策略委托号集合中
        self.strategyOrderDict[strategy.name].add(stopOrderID)
        
        # 推送停止单状态
        strategy.onStopOrder(so)
        
        return [stopOrderID]
    
    #----------------------------------------------------------------------
    def cancelStopOrder(self, stopOrderID):
        """撤销停止单"""
        # 检查停止单是否存在
        if stopOrderID in self.workingStopOrderDict:
            so = self.workingStopOrderDict[stopOrderID]
            strategy = so.strategy
            
            # 更改停止单状态为已撤销
            so.status = STOPORDER_CANCELLED
            
            # 从活动停止单字典中移除
            del self.workingStopOrderDict[stopOrderID]
            
            # 从策略委托号集合中移除
            s = self.strategyOrderDict[strategy.name]
            if stopOrderID in s:
                s.remove(stopOrderID)
            
            # 通知策略
            strategy.onStopOrder(so)

    #----------------------------------------------------------------------
    def processStopOrder(self, tick):
        """收到行情后处理本地停止单（检查是否要立即发出）"""
        vtSymbol = tick.vtSymbol
        
        # 首先检查是否有策略交易该合约
        if vtSymbol in self.tickStrategyDict:
            # 遍历等待中的停止单，检查是否会被触发
            for so in self.workingStopOrderDict.values():
                if so.vtSymbol == vtSymbol:
                    longTriggered = so.direction==DIRECTION_LONG and tick.lastPrice>=so.price        # 多头停止单被触发
                    shortTriggered = so.direction==DIRECTION_SHORT and tick.lastPrice<=so.price     # 空头停止单被触发
                    
                    if longTriggered or shortTriggered:
                        # 买入和卖出分别以涨停跌停价发单（模拟市价单）
                        # 对于没有涨跌停价格的市场则使用5档报价
                        if so.direction==DIRECTION_LONG:
                            if tick.upperLimit:
                                price = tick.upperLimit
                            else:
                                price = tick.askPrice5
                        else:
                            if tick.lowerLimit:
                                price = tick.lowerLimit
                            else:
                                price = tick.bidPrice5
                        
                        # 发出市价委托
                        vtOrderID = self.sendOrder(so.vtSymbol, so.orderType, 
                                                   price, so.volume, so.strategy)
                        
                        # 检查因为风控流控等原因导致的委托失败（无委托号）
                        if vtOrderID:
                            # 从活动停止单字典中移除该停止单
                            del self.workingStopOrderDict[so.stopOrderID]
                            
                            # 从策略委托号集合中移除
                            s = self.strategyOrderDict[so.strategy.name]
                            if so.stopOrderID in s:
                                s.remove(so.stopOrderID)
                            
                            # 更新停止单状态，并通知策略
                            so.status = STOPORDER_TRIGGERED
                            so.strategy.onStopOrder(so)

    #----------------------------------------------------------------------
    def processTickEvent(self, event):
        """处理行情推送"""
        tick = event.dict_['data']
        tick = copy(tick)
        
        # 收到tick行情后，先处理本地停止单（检查是否要立即发出）
        self.processStopOrder(tick)
        
        # 推送tick到对应的策略实例进行处理
        if tick.vtSymbol in self.tickStrategyDict:
   
            # 逐个推送到策略实例中
            l = self.tickStrategyDict[tick.vtSymbol]
            for strategy in l:
                if strategy.inited:
                    self.callStrategyFunc(strategy, strategy.onTick, tick)
    
        #----------------------------------------------------------------------
    def processBarEvent(self, event):
        """处理行情推送"""
        bar = event.dict_['data']
        bar = copy(bar)
        
        # 推送bar到对应的策略实例进行处理
        if bar.vtSymbol in self.tickStrategyDict:
   
            # 逐个推送到策略实例中
            l = self.tickStrategyDict[bar.vtSymbol]
            for strategy in l:
                self.callStrategyFunc(strategy, strategy.onBar, bar)
    
    #----------------------------------------------------------------------
    def processMarketTradeEvent(self, event):
        mt = event.dict_['data']
        mt = copy(mt)

        
        # 推送tick到对应的策略实例进行处理
        if mt.vtSymbol in self.tickStrategyDict:

            l = self.tickStrategyDict[mt.vtSymbol]
            for strategy in l:
                if strategy.inited:
                    self.callStrategyFunc(strategy, strategy.onMarketTrade, mt)        
    #----------------------------------------------------------------------
    def processOrderEvent(self, event):
        """处理委托推送"""
        order = event.dict_['data']
        
        vtOrderID = order.vtOrderID
        
        if vtOrderID in self.orderStrategyDict:
            strategy = self.orderStrategyDict[vtOrderID]            
            
            # 如果委托已经完成（拒单、撤销、全成），则从活动委托集合中移除
            if order.status in self.STATUS_FINISHED:
                s = self.strategyOrderDict[strategy.name]
                if vtOrderID in s:
                    s.remove(vtOrderID)
            
            self.callStrategyFunc(strategy, strategy.onOrder, order)
        else:
            
            for strategy in self.strategyDict.values():
                if order.vtSymbol in strategy.vtSymbols:
                    self.callStrategyFunc(strategy, strategy.onOrder, order)
                    
    #----------------------------------------------------------------------
    def processTradeEvent(self, event):
        """处理成交推送"""
        trade = event.dict_['data']
        
        # 过滤已经收到过的成交回报
        if trade.vtTradeID in self.tradeSet:
            return
        self.tradeSet.add(trade.vtTradeID)
        
        # 将成交推送到策略对象中
        if trade.vtOrderID in self.orderStrategyDict:
            strategy = self.orderStrategyDict[trade.vtOrderID]
            
            # 计算策略持仓
            #if trade.direction == DIRECTION_LONG:
                #strategy.pos += trade.volume
            #else:
                #strategy.pos -= trade.volume
            
            self.callStrategyFunc(strategy, strategy.onTrade, trade)
            
            # 保存策略持仓到数据库
            #self.saveSyncData(strategy)              
    
    #----------------------------------------------------------------------
    def processPosEvent(self, event):
        position = event.dict_['data']
        
        for strategy in self.strategyDict.values():
            if position.vtSymbol in strategy.vtSymbols:
                self.callStrategyFunc(strategy, strategy.onPosition, position)        
    
    #----------------------------------------------------------------------
    def processTimerEvent(self, event):
        """"""
        for strategy in self.strategyDict.values():
            self.callStrategyFunc(strategy, strategy.onTimer)
            
    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.processTickEvent)
        self.eventEngine.register(EVENT_BAR, self.processBarEvent)
        self.eventEngine.register(EVENT_MARKETTRADE, self.processMarketTradeEvent)
        self.eventEngine.register(EVENT_ORDER, self.processOrderEvent)
        self.eventEngine.register(EVENT_TRADE, self.processTradeEvent)
        self.eventEngine.register(EVENT_POSITION, self.processPosEvent)
        self.eventEngine.register(EVENT_TIMER, self.processTimerEvent)
        
    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """插入数据到数据库（这里的data可以是VtTickData或者VtBarData）"""
        self.mainEngine.dbInsert(dbName, collectionName, data.__dict__)
    
    #----------------------------------------------------------------------
    def loadBar(self, dbName, collectionName, days):
        """从数据库中读取Bar数据，startDate是datetime对象"""
        # 优先尝试从RQData获取数据
        if dbName == MINUTE_DB_NAME and collectionName.upper() in self.rqSymbolSet:
            l = self.loadRqBar(collectionName, days)
            return l
        
        # 如果没有则从数据库中读取数据
        startDate = self.today - timedelta(days)
        
        d = {'datetime':{'$gte':startDate}}
        barData = self.mainEngine.dbQuery(dbName, collectionName, d, 'datetime')
        
        l = []
        for d in barData:
            bar = VtBarData()
            bar.__dict__ = d
            l.append(bar)
        return l
    
    #----------------------------------------------------------------------
    def loadTick(self, dbName, collectionName, days):
        """从数据库中读取Tick数据，startDate是datetime对象"""
        startDate = self.today - timedelta(days)
        
        d = {'datetime':{'$gte':startDate}}
        tickData = self.mainEngine.dbQuery(dbName, collectionName, d, 'datetime')
        
        l = []
        for d in tickData:
            tick = VtTickData()
            tick.__dict__ = d
            l.append(tick)
        return l    
    
    #----------------------------------------------------------------------
    def writeStrLog(self, content):
        """快速发出模块日志事件"""
        log = VtLogData()
        log.logContent = content
        log.gatewayName = 'STR_TRADING'
        event = Event(type_=EVENT_STR_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)   
    
    #----------------------------------------------------------------------
    def loadStrategy(self, setting):
        """载入策略"""
        try:
            name = setting['name']
            className = setting['className']
        except Exception:
            msg = traceback.format_exc()
            self.writeStrLog(u'Load Strategy Error：%s' %msg)
            return
        
        # 获取策略类
        strategyClass = STRATEGY_CLASS.get(className, None)
        if not strategyClass:
            self.writeStrLog(u'Cannot Find Strategy Class：%s' %className)
            return
        
        # 防止策略重名
        if name in self.strategyDict:
            self.writeStrLog(u'Duplicated Strategy Name：%s' %name)
        else:
            # 创建策略实例
            strategy = strategyClass(self, setting)  
            self.strategyDict[name] = strategy
            
            # 创建委托号列表
            self.strategyOrderDict[name] = set()
            
            # 保存Tick映射关系
            for vtSymbol in strategy.vtSymbols:
                if vtSymbol in self.tickStrategyDict:
                    self.tickStrategyDict[vtSymbol]
                else:
                    self.tickStrategyDict[vtSymbol] = []
                self.tickStrategyDict[vtSymbol].append(strategy)
            
    #----------------------------------------------------------------------
    def subscribeMarketData(self, strategy):
        """订阅行情"""
        # 订阅合约
        for vtSymbol in strategy.vtSymbols:
            contract = self.mainEngine.getContract(vtSymbol)
            if contract:
                req = VtSubscribeReq()
                req.symbol = contract.symbol
                req.exchange = contract.exchange
                req.productClass = contract.productClass
                
                self.mainEngine.subscribe(req, contract.gatewayName)
            else:
                self.writeStrLog(u'%s Instrument Info %s Not Found' %(strategy.name, vtSymbol))

    #----------------------------------------------------------------------
    def initStrategy(self, name):
        """初始化策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if not strategy.inited:
                #strategy.inited = True
                self.callStrategyFunc(strategy, strategy.onInit)

                self.loadSyncData(strategy)                             # 初始化完成后加载同步数据
                self.subscribeMarketData(strategy)                      # 加载同步数据后再订阅行情
            else:
                self.writeStrLog(u'Strategy Has Already Been Initilized：%s' %name)
        else:
            self.writeStrLog(u'Strategy Instance Does Not Exist：%s' %name)        

    #---------------------------------------------------------------------
    def startStrategy(self, name):
        """启动策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if strategy.inited and not strategy.trading:
                strategy.trading = True
                self.callStrategyFunc(strategy, strategy.onStart)
        else:
            self.writeStrLog(u'Strategy Instance Does Not Exist：%s' %name)
    
    #----------------------------------------------------------------------
    def stopStrategy(self, name):
        """停止策略"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            
            if strategy.trading:
                strategy.trading = False
                self.callStrategyFunc(strategy, strategy.onStop)
                
                # 对该策略发出的所有限价单进行撤单
                for vtOrderID, s in self.orderStrategyDict.items():
                    if s is strategy:
                        self.cancelOrder(vtOrderID)
                
                # 对该策略发出的所有本地停止单撤单
                #for stopOrderID, so in self.workingStopOrderDict.items():
                    #if so.strategy is strategy:
                        #self.cancelStopOrder(stopOrderID)   
        else:
            self.writeStrLog(u'Strategy Instance Does Not Exist：%s' %name)    
            
    #----------------------------------------------------------------------
    def initAll(self):
        """全部初始化"""
        for name in self.strategyDict.keys():
            self.initStrategy(name)    
            
    #----------------------------------------------------------------------
    def startAll(self):
        """全部启动"""
        for name in self.strategyDict.keys():
            self.startStrategy(name)
            
    #----------------------------------------------------------------------
    def stopAll(self):
        """全部停止"""
        for name in self.strategyDict.keys():
            self.stopStrategy(name)    
    
    #----------------------------------------------------------------------
    def saveSetting(self):
        """保存策略配置"""
        with open(self.settingFilePath, 'w') as f:
            l = []
            
            for strategy in self.strategyDict.values():
                setting = {}
                for param in strategy.paramList:
                    setting[param] = strategy.__getattribute__(param)
                l.append(setting)
            
            jsonL = json.dumps(l, indent=4)
            f.write(jsonL)
    
    #----------------------------------------------------------------------
    def loadSetting(self):
        """读取策略配置"""
        with open(self.settingFilePath) as f:
            l = json.load(f)
            
            for setting in l:
                self.loadStrategy(setting)
    
    #----------------------------------------------------------------------
    def getStrategyVar(self, name):
        """获取策略当前的变量字典"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            varDict = OrderedDict()
            
            for key in strategy.varList:
                varDict[key] = strategy.__getattribute__(key)
            
            return varDict
        else:
            self.writeStrLog(u'Strategy Instance Does Not Exist：' + name)    
            return None
    
    #----------------------------------------------------------------------
    def getStrategyParam(self, name):
        """获取策略的参数字典"""
        if name in self.strategyDict:
            strategy = self.strategyDict[name]
            paramDict = OrderedDict()
            
            for key in strategy.paramList:  
                paramDict[key] = strategy.__getattribute__(key)
            
            return paramDict
        else:
            self.writeStrLog(u'Strategy Instance Does Not Exist：' + name)    
            return None
    
    #----------------------------------------------------------------------
    def getStrategyNames(self):
        """查询所有策略名称"""
        return self.strategyDict.keys()        
        
    #----------------------------------------------------------------------
    def putStrategyEvent(self, name):
        """触发策略状态变化事件（通常用于通知GUI更新）"""
        strategy = self.strategyDict[name]
        d = {k:strategy.__getattribute__(k) for k in strategy.varList}
        
        event = Event(EVENT_STRATEGY+name)
        event.dict_['data'] = d
        self.eventEngine.put(event)
        
        d2 = {k:str(v) for k,v in d.items()}
        d2['name'] = name
        event2 = Event(EVENT_STRATEGY)
        event2.dict_['data'] = d2
        self.eventEngine.put(event2)        
        
    #----------------------------------------------------------------------
    def callStrategyFunc(self, strategy, func, params=None):
        """调用策略的函数，若触发异常则捕捉"""
        try:
            if params:
                func(params)
            else:
                func()
        except Exception:
            # 停止策略，修改状态为未初始化
            strategy.trading = False
            strategy.inited = False
            
            # 发出日志
            content = '\n'.join([u'策略%s触发异常已停止' %strategy.name,
                                traceback.format_exc()])
            self.writeStrLog(content)
            
    #----------------------------------------------------------------------
    def saveSyncData(self, strategy):
        """保存策略的持仓情况到数据库"""
        flt = {'name': strategy.name,
               'vtSymbol': strategy.vtSymbol}
        
        d = copy(flt)
        for key in strategy.syncList:
            d[key] = strategy.__getattribute__(key)
        
        self.mainEngine.dbUpdate(POSITION_DB_NAME, strategy.className,
                                 d, flt, True)
        
        content = u'策略%s同步数据保存成功，当前持仓%s' %(strategy.name, strategy.pos)
        self.writeStrLog(content)
    
    #----------------------------------------------------------------------
    def loadSyncData(self, strategy):
        """从数据库载入策略的持仓情况"""
        flt = {'name': strategy.name,
               'vtSymbol': strategy.vtSymbols}
        syncData = self.mainEngine.dbQuery(POSITION_DB_NAME, strategy.className, flt)
        
        if not syncData:
            return
        
        d = syncData[0]
        
        for key in strategy.syncList:
            if key in d:
                strategy.__setattr__(key, d[key])
                
    #----------------------------------------------------------------------
    def roundToPriceTick(self, priceTick, price):
        """取整价格到合约最小价格变动"""
        if not priceTick:
            return price
        
        newPrice = round(price/priceTick, 0) * priceTick
        return newPrice    
    
    #----------------------------------------------------------------------
    def stop(self):
        """停止"""
        pass
    
    #----------------------------------------------------------------------
    def cancelAll(self, name):
        """全部撤单"""
        s = self.strategyOrderDict[name]
        
        # 遍历列表，全部撤单
        # 这里不能直接遍历集合s，因为撤单时会修改s中的内容，导致出错
        for orderID in list(s):
            if STOPORDERPREFIX in orderID:
                self.cancelStopOrder(orderID)
            else:
                self.cancelOrder(orderID)

    #----------------------------------------------------------------------
    def getPriceTick(self, vtSymbol):
        """获取最小价格变动"""
        contract = self.mainEngine.getContract(vtSymbol)
        if contract:
            return contract.priceTick
        return 0
        
    #----------------------------------------------------------------------
    def initRqData(self):
        """初始化RQData客户端"""
        # 检查是否填写了RQData配置
        username = globalSetting.get('rqUsername', None)
        password = globalSetting.get('rqPassword', None)
        if not username or not password:
            return
        
        # 加载RQData
        try:
            import rqdatac as rq
        except ImportError:
            return
        
        # 登录RQData
        self.rq = rq
        self.rq.init(username, password)
        
        # 获取本日可交易合约代码
        try:
            df = self.rq.all_instruments(type='Future', date=datetime.now())
            for ix, row in df.iterrows():
                self.rqSymbolSet.add(row['order_book_id'])
        except RuntimeError:
            pass
    
    #----------------------------------------------------------------------
    def loadRqBar(self, symbol, days):
        """从RQData加载K线数据"""
        endDate = datetime.now()
        startDate = endDate - timedelta(days)
        
        df = self.rq.get_price(symbol.upper(), 
                               frequency='1m', 
                               fields=['open', 'high', 'low', 'close', 'volume'],
                               start_date=startDate,
                               end_date=endDate)
        
        l = []
        
        for ix, row in df.iterrows():
            bar = VtBarData()
            bar.symbol = symbol
            bar.vtSymbol = symbol
            bar.open = row['open']
            bar.high = row['high']
            bar.low = row['low']
            bar.close = row['close']
            bar.volume = row['volume']
            bar.datetime = row.name
            bar.date = bar.datetime.strftime("%Y%m%d")
            bar.time = bar.datetime.strftime("%H:%M:%S")
            
            l.append(bar)
        
        return l