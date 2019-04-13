# encoding: UTF-8

"""
展示如何执行策略回测。
"""

from __future__ import division

from Exchange.BinanceTrade import BackTestEngine , MINUTE_DB_NAME
# from Exchange.BitmexTrade import BackTestEngine, MINUTE_DB_NAME
import os

path = 'BtDate/'
dirs = os.listdir(path)
for dir in dirs:
    fileName = dir  # CSV格式回测数据文件名

if __name__ == '__main__':
    from trader.app.strategyTrading.strategy.strategyRsi import RsiStrategy

    # 创建回测引擎
    engine = BackTestEngine()

    # 设置引擎的回测模式为K线
    engine.setBacktestingMode(engine.BAR_MODE)

    # 设置回测用的数据起始日期
    engine.setStartDate('20120101')

    # 设置产品相关参数
    engine.setSlippage(0.2)  # 滑点
    engine.setRate(0.2 / 10000)  # 手续费万0.2
    engine.setSize(10)  # 合约大小
    engine.setPriceTick(0.00001)  # 最小价格变动

    # 设置使用的历史数据库
    engine.setDatabase(MINUTE_DB_NAME, 'IF0000')

    # engine.loadHisroryDataCsv(fileName=fileName, symbol=None)  # 设置使用的历史数据Csv(symbol=None 请填写symbol值)

    # 在引擎中创建策略对象
    d = {}
    engine.initStrategy(RsiStrategy, d)

    # 开始跑回测
    engine.runBacktesting()

    engine.showBacktestingResult()  # 显示回测结果

    # engine.showDailyResult() # 显示每日回测结果
