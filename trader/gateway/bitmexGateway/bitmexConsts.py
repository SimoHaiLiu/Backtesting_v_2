# encoding: UTF-8

from trader.vtConstant import *

MODE = 'test'

if MODE =='real':
    MODE_STR = 'www'
else:
    MODE_STR = 'testnet'

REST_HOST = 'https://'+ MODE_STR +'.bitmex.com/api/v1'#
WEBSOCKET_HOST = 'wss://'+ MODE_STR +'.bitmex.com/realtime'      # 

SUB_DEPTH = 5
TICK_DEPTH = 5
DIS_DEPTH = min(SUB_DEPTH, TICK_DEPTH)

DIRECTION_VT2BITMEX = {DIRECTION_LONG: "Buy", DIRECTION_SHORT: "Sell"}
DIRECTION_BITMEX2VT = {v: k for k, v in DIRECTION_VT2BITMEX.items()}

PRICETYPE_VT2BITMEX = {PRICETYPE_LIMITPRICE: "Limit", PRICETYPE_MARKETPRICE: "Market", PRICETYPE_STOP: "Stop", PRICETYPE_STOPLIMIT: "StopLimit", PRICETYPE_MARKETIFTOUCHED: "MarketIfTouched", PRICETYPE_LIMITIFTOUCHED: "LimitIfTouched"}
PRICETYPE_BITMEX2VT = {v: k for k, v in PRICETYPE_VT2BITMEX.items()}

ORDSTATUS_VT2BITMEX = {STATUS_NOTTRADED: "New", STATUS_PARTTRADED: "Partially filled", STATUS_ALLTRADED: "Filled", STATUS_CANCELLED: "Canceled", STATUS_UNTRIGGERED: "Untriggered", STATUS_TRIGGERED: "StopOrderTriggered", STATUS_REJECTED: "Rejected"}
ORDSTATUS_BITMEX2VT = {v: k for k, v in ORDSTATUS_VT2BITMEX.items()}