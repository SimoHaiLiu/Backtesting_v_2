# encoding: UTF-8

# 默认空值
EMPTY_STRING = ''
EMPTY_UNICODE = u''
EMPTY_INT = 0
EMPTY_FLOAT = 0.0
EMPTY_LIST = []
# 方向常量
DIRECTION_NONE = u'none'
DIRECTION_LONG = u'long'
DIRECTION_SHORT = u'short'
DIRECTION_UNKNOWN = u'unknown'
DIRECTION_NET = u'net'
DIRECTION_SELL = u'sell'      # IB接口
DIRECTION_COVEREDSHORT = u'covered short'    # 证券期权

# 开平常量
OFFSET_NONE = u'none'
OFFSET_OPEN = u'open'
OFFSET_CLOSE = u'close'
OFFSET_CLOSETODAY = u'close today'
OFFSET_CLOSEYESTERDAY = u'close yesterday'
OFFSET_UNKNOWN = u'unknown'

# 状态常量
STATUS_NOTTRADED = u'pending'
STATUS_PARTTRADED = u'partial filled'
STATUS_ALLTRADED = u'filled'
STATUS_CANCELLED = u'cancelled'
STATUS_REJECTED = u'rejected'
STATUS_UNKNOWN = u'unknown'

# 合约类型常量
PRODUCT_EQUITY = u'equity'
PRODUCT_FUTURES = u'futures'
PRODUCT_OPTION = u'option'
PRODUCT_INDEX = u'index'
PRODUCT_COMBINATION = u'combination'
PRODUCT_FOREX = u'forex'
PRODUCT_UNKNOWN = u'unknown'
PRODUCT_SPOT = u'spot'
PRODUCT_DEFER = u'defer'
PRODUCT_NONE = 'none'

# 价格类型常量
PRICETYPE_LIMITPRICE = u'limit order'
PRICETYPE_MARKETPRICE = u'market order'
PRICETYPE_FAK = u'FAK'
PRICETYPE_FOK = u'FOK'

# 期权类型
OPTION_CALL = u'call'
OPTION_PUT = u'put'

# 交易所类型

EXCHANGE_OKCOIN = 'OKCOIN'       # OKCOIN比特币交易所
EXCHANGE_HUOBI = 'HUOBI'         # 火币比特币交易所
EXCHANGE_LBANK = 'LBANK'         # LBANK比特币交易所
EXCHANGE_ZB = 'ZB'		 # 比特币中国比特币交易所
EXCHANGE_OKEX = 'OKEX'		 # OKEX比特币交易所
EXCHANGE_OKEXFUTURE = 'OKEXFUTURE'		 # OKEX比特币交易所-期货
EXCHANGE_BINANCE = "BINANCE"     # 币安比特币交易所
EXCHANGE_BITFINEX = "BITFINEX"   # Bitfinex比特币交易所
EXCHANGE_BITMEX = 'BITMEX'       # BitMEX比特币交易所
EXCHANGE_FCOIN = 'FCOIN'         # FCoin比特币交易所
EXCHANGE_BIGONE = 'BIGONE'       # BigOne比特币交易所
EXCHANGE_COINBASE = 'COINBASE'   # Coinbase交易所
EXCHANGE_BITHUMB = 'BITHUMB'   # Bithumb比特币交易所

# 货币类型
CURRENCY_USD = 'USD'            # 美元
CURRENCY_CNY = 'CNY'            # 人民币
CURRENCY_HKD = 'HKD'            # 港币
CURRENCY_UNKNOWN = 'UNKNOWN'    # 未知货币
CURRENCY_NONE = ''              # 空货币

# 数据库
LOG_DB_NAME = 'VnTrader_Log_Db'

# 接口类型

GATEWAYTYPE_BTC = 'btc'                         # 比特币



# K线周期类型
INTERVAL_1M = u'1-Minute'
INTERVAL_5M = u'5-Minute'
INTERVAL_15M = u'15-Minute'
INTERVAL_30M = u'30-Minute'
INTERVAL_1H = u'1-Hour'
INTERVAL_4H = u'4-Hour'
INTERVAL_DAILY = u'Daily'
INTERVAL_WEEKLY = u'Weekly'