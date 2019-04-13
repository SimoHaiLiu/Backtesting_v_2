# encoding: UTF-8


########################################################################
import json
import ssl
import sys
import time
import traceback
from datetime import datetime
from threading import Lock, Thread, active_count
from vtConstant import *

from mdEngine import MData
import websocket
import zlib
import hashlib
import base64

########################################################################
class WebsocketClient(object):    
    """交易接口"""

    #----------------------------------------------------------------------
    def __init__(self, gateway):
        """Constructor"""
        self.gateway = gateway
        self.host = ''          # 服务器
        self.apiKey = ''        # 用户名
        self.secretKey = ''     # 密码
        #self.gatewayName = gateway.gatewayName
        self.active = False     # 工作状态
        self.ws = None          # websocket应用对象
        self.wsThread = None    # websocket工作线程
        
        self.heartbeatCount = 0         # 心跳计数
        self.heartbeatThread = None     # 心跳线程
        self.heartbeatReceived = None   # 心跳是否收到
        
        self.reconnecting = False       # 重新连接中
    
    #----------------------------------------------------------------------
    def passiveHeartbeat(self):
        """"""
        while self.active:

            if self.heartbeatReceived:
                
                d = {'pong': self.heartbeatReceived}
                #print d
                self.heartbeatReceived = None
                j = json.dumps(d)
                
                try:
                    self.ws.send(j) 
                except:
                    msg = traceback.format_exc()
                    self.onError(msg)
                    self.reconnect()
    
    #----------------------------------------------------------------------
    def activeHeartbeat(self):
        """"""
        while self.active:

            if self.heartbeatCount == 0:
                self.heartbeatCount = 1
           
                d = self.getHbReq()
                #print d
                j = json.dumps(d)
                
                try:
                    self.ws.send(j) 
                except:
                    msg = traceback.format_exc()
                    self.onError(msg)
                    self.reconnect()
            else:
                self.heartbeatCount += 1
                if self.heartbeatCount >= 10:
                    self.heartbeatCount = 0
                time.sleep(1)
                
    #----------------------------------------------------------------------
    def getHbReq(self):
        if EXCHANGE_DERIBIT in self.gateway.gatewayName :
            return {"action": "/api/v1/public/ping"}

        elif EXCHANGE_HUOBI in self.gateway.gatewayName:
            return {'ping': long(int(time.time() * 1000))}
        
    #----------------------------------------------------------------------
    def reconnect(self):
        """重新连接"""
        if not self.reconnecting:
            self.reconnecting = True
            
            self.close()           # 首先关闭之前的连接
            self.heartbeatReceived = None   # 将心跳状态设为正常
            self.heartbeatCount = 0
            self.initWebsocket()
        
            self.reconnecting = False
        
    #----------------------------------------------------------------------
    def connect(self, apiKey, secretKey, host, trace=False):
        """连接"""
        self.host = host
        self.apiKey = apiKey
        self.secretKey = secretKey
        
        websocket.enableTrace(trace)
        
        self.initWebsocket()
        
        
    #----------------------------------------------------------------------
    def initWebsocket(self):
        """"""
        self.ws = websocket.WebSocketApp(self.host, 
                                         on_message=self.onMessageCallback,
                                         on_error=self.onErrorCallback,
                                         on_close=self.onCloseCallback,
                                         on_open=self.onOpenCallback
                                         )        
        

        kwargs = {'sslopt': {'cert_reqs': ssl.CERT_NONE}}
        self.wsThread = Thread(target=self.ws.run_forever, kwargs=kwargs)
        self.wsThread.daemon = True
        self.wsThread.start()
        self.active = True
        print active_count()
    #----------------------------------------------------------------------
    def readData(self, evt, decType=0):
        """解码推送收到的数据"""
        # 先解压
        if decType == 0:
            decompress = zlib.decompressobj(zlib.MAX_WBITS | 16)
        else:
            decompress = zlib.decompressobj(-zlib.MAX_WBITS)
            
        inflated = decompress.decompress(evt)
        inflated += decompress.flush()

        # 再转换为json
        data = json.loads(inflated)
        return data

    #----------------------------------------------------------------------
    def closeHeartbeat(self):
        """关闭接口"""
        if self.heartbeatThread:# and self.heartbeatThread.isAlive():
            self.active = False
            try:
                self.heartbeatThread.join()
            except Exception as e:
                print(e)
            
            self.heartbeatThread = None
            
    #----------------------------------------------------------------------
    def closeWebsocket(self):
        """关闭WS"""
        if self.wsThread and self.wsThread.isAlive():
            try:
                self.ws.close()
                print ('ws closed')
                #self.wsThread.join()
            except Exception as e:
                print('close ws',e)
    
    #----------------------------------------------------------------------
    def close(self):
        """"""
        self.closeHeartbeat()
        self.closeWebsocket()
        
    #----------------------------------------------------------------------
    def onMessage(self, data):
        """信息推送""" 
        print('onMessage')
        print(data)
        
    #----------------------------------------------------------------------
    def onError(self, data):
        """错误推送"""
        #msg = data['err-msg']
        #if msg == u'invalid pong':
        #    return
        print('onError')
        print(data)
        #self.gateway.writeLog(msg['err-msg'])
        
    #----------------------------------------------------------------------
    def onClose(self):
        """接口断开"""
        print('onClose')
        self.reconnect()
        
    #----------------------------------------------------------------------
    def onOpen(self):
        """接口打开"""
        pass
    
    #----------------------------------------------------------------------
    def onMessageCallback(self, evt):
        """""" 
    
        if EXCHANGE_DERIBIT in self.gateway.gatewayName:
            evt = json.loads(evt) 
            
            if 'result' in evt and evt['result'] == 'pong':
                self.heartbeatCount = 0
                return
        elif EXCHANGE_CRYPTOFAC in self.gateway.gatewayName:
            evt = json.loads(evt)
        elif EXCHANGE_BITMEX in self.gateway.gatewayName:
            evt = json.loads(evt)
            #if 'table' in evt:
                #self.jitterCount +=1
                #if self.jitterCount == 5:
                    
                    #self.jitterCount = 0
                #else:
                    #return
        elif EXCHANGE_COINBASE in self.gateway.gatewayName :
            evt = json.loads(evt) 
        elif EXCHANGE_BINANCE in self.gateway.gatewayName:
            evt = json.loads(evt)        
        elif EXCHANGE_HUOBI in self.gateway.gatewayName or EXCHANGE_HBDM in self.gateway.gatewayName:
            evt = self.readData(evt,decType=0)
            
            if 'ping' in evt:
                #print evt ['ping']
                self.heartbeatReceived = evt['ping'] 
                return
            
        elif EXCHANGE_OKEX in self.gateway.gatewayName:
            evt = self.readData(evt,decType=1)

        #print (evt)
        data = MData(exch_=self.gateway.gatewayName)
        data.dict_['data'] = evt
        self.gateway.mdEngine.put(data)        
        #return        
        #self.onMessage(evt)      

    #----------------------------------------------------------------------
    def onErrorCallback(self, evt):
        """"""
        self.onError(evt)
        
    #----------------------------------------------------------------------
    def onCloseCallback(self):
        """"""
        self.onClose()
        
    #----------------------------------------------------------------------
    def onOpenCallback(self):
        """"""
        self.jitterCount = 0
        
        if not self.heartbeatThread:
            if EXCHANGE_DERIBIT in self.gateway.gatewayName :

                self.heartbeatThread = Thread(target=self.activeHeartbeat)
                self.heartbeatThread.daemon = True
                self.heartbeatThread.start()                
            elif EXCHANGE_HUOBI in self.gateway.gatewayName or EXCHANGE_HBDM in self.gateway.gatewayName:

                self.heartbeatThread = Thread(target=self.passiveHeartbeat)
                self.heartbeatThread.daemon = True
                self.heartbeatThread.start()                
            
            print("hb thread on!")
        
        self.onOpen()
        
    #----------------------------------------------------------------------
    def generateSign(self, params):
        """生成签名"""
        l = []
        for key in sorted(params.keys()):
            l.append('%s=%s' %(key, params[key]))
        l.append('secret_key=%s' %self.secretKey)
        sign = '&'.join(l)
        return hashlib.md5(sign.encode('utf-8')).hexdigest().upper()
    
    #----------------------------------------------------------------------
    def get_signature(self, action, arguments):
        nonce = str(int(time.time() * 1000))
    
        signature_string = '_=%s&_ackey=%s&_acsec=%s&_action=%s' % (
            nonce, self.apiKey, self.secretKey, action
        )
    
        for key, value in sorted(arguments.items()):
            if isinstance(value, list):
                value = "".join(str(v) for v in value)
            signature_string += "&%s=%s" % (key, value)

        sha256 = hashlib.sha256()
        sha256.update(signature_string.encode("utf-8"))
        signature_hash = base64.b64encode(sha256.digest()).decode()
    
        return "%s.%s.%s" % (self.apiKey, nonce, signature_hash)

    
    #----------------------------------------------------------------------
    def sendRequest(self, req, auth=False):
        """发送请求"""
        # 生成请求
        d = {}
        #d['event'] = 'addChannel'
        #d['channel'] = channel        
        
        # 如果有参数，在参数字典中加上api_key和签名字段
        if auth:
            if req.has_key('arguments'):
                #d['action'] = channel['action']
                req['sig'] = self.get_signature(req['action'], req['arguments'])
            else:
                req['sig'] = self.get_signature(req['action'])
                #d['parameters'] = channel
        
        # 使用json打包并发送
        j = json.dumps(req)
        
        # 若触发异常则重连
        try:
            self.ws.send(j)
            return True
        except websocket.WebSocketConnectionClosedException:
            self.reconnect()
            return False
    
    #----------------------------------------------------------------------
    def login(self):
        params = {}
        params['api_key'] = self.apiKey
        params['sign'] = self.generateSign(params)
        
        # 生成请求
        d = {}
        d['event'] = 'login'
        d['parameters'] = params
        j = json.dumps(d)
        
        # 若触发异常则重连
        try:
            self.ws.send(j)
            return True
        except websocket.WebSocketConnectionClosedException:
            self.reconnect()
            return False