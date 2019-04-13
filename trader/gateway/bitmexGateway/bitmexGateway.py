# encoding: UTF-8

'''
火币交易接口
'''

from __future__ import print_function

import base64
import hashlib
import hmac
import json
import re
import urllib
import zlib
import gzip
from copy import copy
from datetime import datetime
import time

from bitmexFutureRestApi import BitmexFutureRestApi
from bitmexFutureWsApi import BitmexFutureMarketWsApi

from trader.vtGateway import *
from trader.vtFunction import getTempPath, getJsonPath
import websocket
import ssl


########################################################################
class BitmexGateway(VtGateway):
    """Bitmex接口"""

    #----------------------------------------------------------------------
    def __init__(self, eventEngine, mdEngine, gatewayName='BITMEX'):
        """Constructor"""
        super(BitmexGateway, self).__init__(eventEngine, mdEngine, gatewayName)

        self.localID = 100
        
        self.accountDict = {}
        self.orderDict = {}
        self.localOrderDict = {}
        self.orderLocalDict = {}


        self.restApi = BitmexFutureRestApi(self)                  
        self.marketWsApi = BitmexFutureMarketWsApi(self)    
        
        self.qryEnabled = False         # 是否要启动循环查询

        self.fileName = 'c:\dxTrader\connection.json'
        self.filePath = getJsonPath(self.fileName, __file__)

    #----------------------------------------------------------------------
    def connect(self):
        """连接"""
        try:
            f = open(self.filePath)
        except IOError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'读取连接配置出错，请检查'
            self.onLog(log)
            return

        # 解析json文件
        setting = json.load(f)
        setting = setting[unicode(self.gatewayName.split('@')[-1])]
        try:
            accessKey = str(setting['accessKey'])
            secretKey = str(setting['secretKey'])
            swapSymbols = setting['swapSymbols']
            futureSymbols = setting['futureSymbols']
        except KeyError:
            log = VtLogData()
            log.gatewayName = self.gatewayName
            log.logContent = u'连接配置缺少字段，请检查'
            self.onLog(log)
            return

        # 创建行情和交易接口对象
        self.restApi.connect(futureSymbols, swapSymbols, accessKey, secretKey)
        self.marketWsApi.connect(futureSymbols, swapSymbols, accessKey, secretKey)
        
        # 初始化并启动查询
        #self.initQuery()
    
        
    #----------------------------------------------------------------------
    def subscribe(self, subscribeReq):
        """订阅行情"""
        if self.marketWsApi.subscribeTopic(type_=subscribeReq.productClass,symbol=subscribeReq.symbol):
            self.restApi.addSymbol(subscribeReq.productClass,subscribeReq.symbol)
            self.marketWsApi.addSymbol(subscribeReq.productClass,subscribeReq.symbol)

    #----------------------------------------------------------------------
    def sendOrder(self, orderReq):
        """发单"""
        return self.restApi.sendOrder(orderReq)

    #----------------------------------------------------------------------
    def cancelOrder(self, cancelOrderReq):
        """撤单"""
        self.restApi.cancelOrder(cancelOrderReq)

    #----------------------------------------------------------------------
    def close(self):
        """关闭"""
        self.spotRestApi.stop()
        self.tradeWsApi.stop()
        self.marketWsApi.stop()

    #----------------------------------------------------------------------
    def initQuery(self):
        """初始化连续查询"""
        if self.qryEnabled:
            # 需要循环的查询函数列表
            self.qryFunctionList = [self.qryInfo]

            self.qryCount = 0           # 查询触发倒计时
            self.qryTrigger = 1         # 查询触发点
            self.qryNextFunction = 0    # 上次运行的查询函数索引

            self.startQuery()

    #----------------------------------------------------------------------
    def query(self, event):
        """注册到事件处理引擎上的查询函数"""
        self.qryCount += 1

        if self.qryCount > self.qryTrigger:
            # 清空倒计时
            self.qryCount = 0

            # 执行查询函数
            function = self.qryFunctionList[self.qryNextFunction]
            function()

            # 计算下次查询函数的索引，如果超过了列表长度，则重新设为0
            self.qryNextFunction += 1
            if self.qryNextFunction == len(self.qryFunctionList):
                self.qryNextFunction = 0
    
    #----------------------------------------------------------------------
    def qryBar(self, symbol, interval='1m', limit=1000):
        self.restApi.queryBar(symbol, interval, limit)
        
    #---------------------------------------------------------------------- 
    def qryOrder(self,openOnly=False):
        self.restApi.queryOrder(openOnly)
        
    #----------------------------------------------------------------------
    def qryPosition(self):
        self.restApi.queryPos()
        
    #----------------------------------------------------------------------
    def startQuery(self):
        """启动连续查询"""
        self.eventEngine.register(EVENT_TIMER, self.query)

    #----------------------------------------------------------------------
    def setQryEnabled(self, qryEnabled):
        """设置是否要启动循环查询"""
        self.qryEnabled = qryEnabled
    
    #----------------------------------------------------------------------
    def writeLog(self, msg):
        """"""
        log = VtLogData()
        log.logContent = msg
        log.gatewayName = self.gatewayName
        
        event = Event(EVENT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)
        




#----------------------------------------------------------------------
def printDict(d):
    """"""
    print('-' * 30)
    l = d.keys()
    l.sort()
    for k in l:
        print(type(k), k, d[k])
    