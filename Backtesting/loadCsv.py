# encoding: UTF-8

"""
导入MC导出的CSV历史数据到MongoDB中
"""

from trader.app.strategyTrading.strBase import MINUTE_DB_NAME
from trader.app.strategyTrading.strHistoryData import loadMcCsv


if __name__ == '__main__':
    loadMcCsv('IF0000_1min.csv', MINUTE_DB_NAME, 'IF0000')
    loadMcCsv('rb0000_1min.csv', MINUTE_DB_NAME, 'rb0000')

