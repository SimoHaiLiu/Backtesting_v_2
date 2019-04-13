# encoding: UTF-8

from .bitmexGateway import BitmexGateway
from trader.vtConstant import GATEWAYTYPE_BTC

gatewayClass = BitmexGateway
gatewayName = 'BITMEX'
gatewayDisplayName = u'Bitmex'
gatewayType = GATEWAYTYPE_BTC
gatewayQryEnabled = False