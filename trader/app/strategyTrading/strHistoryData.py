# encoding: UTF-8

"""
本模块中主要包含：
1. 将MultiCharts导出的历史数据载入到MongoDB中用的函数
2. 将通达信导出的历史数据载入到MongoDB中的函数
3. 将交易开拓者导出的历史数据载入到MongoDB中的函数
4. 将OKEX下载的历史数据载入到MongoDB中的函数
"""
from __future__ import print_function

import csv
from datetime import datetime, timedelta
from time import time
from struct import unpack

import pymongo

from trader.vtGlobal import globalSetting
from trader.vtConstant import *
from trader.vtObject import VtBarData
from .strBase import SETTING_DB_NAME, TICK_DB_NAME, MINUTE_DB_NAME, DAILY_DB_NAME


# ----------------------------------------------------------------------
def downloadEquityDailyBarts(self, symbol):
    """
    下载股票的日行情，symbol是股票代码
    """
    print(u'开始下载%s日行情' % symbol)

    # 查询数据库中已有数据的最后日期
    cl = self.dbClient[DAILY_DB_NAME][symbol]
    cx = cl.find(sort=[('datetime', pymongo.DESCENDING)])
    if cx.count():
        last = cx[0]
    else:
        last = ''
    # 开始下载数据
    import tushare as ts

    if last:
        start = last['date'][:4] + '-' + last['date'][4:6] + '-' + last['date'][6:]

    data = ts.get_k_data(symbol, start)

    if not data.empty:
        # 创建datetime索引
        self.dbClient[DAILY_DB_NAME][symbol].ensure_index([('datetime', pymongo.ASCENDING)],
                                                          unique=True)

        for index, d in data.iterrows():
            bar = VtBarData()
            bar.vtSymbol = symbol
            bar.symbol = symbol
            try:
                bar.open = d.get('open')
                bar.high = d.get('high')
                bar.low = d.get('low')
                bar.close = d.get('close')
                bar.date = d.get('date').replace('-', '')
                bar.time = ''
                bar.datetime = datetime.strptime(bar.date, '%Y%m%d')
                bar.volume = d.get('volume')
            except KeyError:
                print(d)

            flt = {'datetime': bar.datetime}
            self.dbClient[DAILY_DB_NAME][symbol].update_one(flt, {'$set': bar.__dict__}, upsert=True)

        print(u'%s下载完成' % symbol)
    else:
        print(u'找不到合约%s' % symbol)


# ----------------------------------------------------------------------
def loadMcCsv(fileName, dbName, symbol):
    """将Multicharts导出的csv格式的历史数据插入到Mongo数据库中"""
    start = time()
    print(u'开始读取CSV文件%s中的数据插入到%s的%s中' % (fileName, dbName, symbol))

    # 锁定集合，并创建索引
    client = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)

    # 读取数据和插入到数据库
    with open(fileName, 'r') as f:
        reader = csv.DictReader(f)
        for d in reader:
            bar = VtBarData()
            bar.vtSymbol = symbol
            bar.symbol = symbol
            bar.open = float(d['Open'])
            bar.high = float(d['High'])
            bar.low = float(d['Low'])
            bar.close = float(d['Close'])
            bar.date = datetime.strptime(d['Date'], '%Y-%m-%d').strftime('%Y%m%d')
            bar.time = d['Time']
            bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
            bar.volume = d['TotalVolume']
            bar.lastBar = False

            flt = {'datetime': bar.datetime}
            collection.update_one(flt, {'$set': bar.__dict__}, upsert=True)
            print(bar.date, bar.time)

    print(u'插入完毕，耗时：%s' % (time() - start))


# ----------------------------------------------------------------------
def loadOKEXCsv(fileName, dbName, symbol):
    """将OKEX导出的csv格式的历史分钟数据插入到Mongo数据库中"""
    start = time()
    print(u'开始读取CSV文件%s中的数据插入到%s的%s中' % (fileName, dbName, symbol))

    # 锁定集合，并创建索引
    client = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)

    # 读取数据和插入到数据库
    reader = csv.reader(open(fileName, "r"))
    for d in reader:
        if len(d[1]) > 10:
            bar = VtBarData()
            bar.vtSymbol = symbol
            bar.symbol = symbol

            bar.datetime = datetime.strptime(d[1], '%Y-%m-%d %H:%M:%S')
            bar.date = bar.datetime.date().strftime('%Y%m%d')
            bar.time = bar.datetime.time().strftime('%H:%M:%S')

            bar.open = float(d[2])
            bar.high = float(d[3])
            bar.low = float(d[4])
            bar.close = float(d[5])

            bar.volume = float(d[6])
            bar.tobtcvolume = float(d[7])

            flt = {'datetime': bar.datetime}
            collection.update_one(flt, {'$set': bar.__dict__}, upsert=True)
            print('%s \t %s' % (bar.date, bar.time))

    print(u'插入完毕，耗时：%s' % (time() - start))


def loadBinanceCsv(fileName, symbol, dbName=None):
    barlist = []

    reader = csv.reader(open(fileName, "r"))
    for d in reader:
        if 'open' not in d[1]:
            bar = VtBarData()
            bar.symbol = symbol
            bar.interval = '1m'  # K线周期.
            bar.exchange = EXCHANGE_BINANCE
            bar.vtSymbol = '.'.join([bar.symbol, bar.exchange])
            bar.datetime = datetime.strptime(d[0], '%Y-%m-%d %H:%M:%S')
            bar.date = bar.datetime.date().strftime('%Y-%m-%d')
            bar.time = bar.datetime.time().strftime('%H:%M:%S')
            bar.open = float(d[1])
            bar.high = float(d[2])
            bar.low = float(d[3])
            bar.close = float(d[4])
            bar.volume = float(d[5])
            barlist.append(bar)

    return barlist


def loadBitmexCsv(fileName, symbol, dbName=None):
    barlist = []

    reader = csv.reader(open(fileName, "r"))
    for d in reader:
        if 'open' not in d[1]:
            bar = VtBarData()
            bar.symbol = symbol
            bar.interval = '1m'  # K线周期.
            bar.exchange = EXCHANGE_BITMEX
            bar.vtSymbol = '.'.join([bar.symbol, bar.exchange])
            bar.datetime = datetime.strptime(d[0], '%Y-%m-%d %H:%M:%S')
            bar.date = bar.datetime.date().strftime('%Y-%m-%d')
            bar.time = bar.datetime.time().strftime('%H:%M:%S')
            bar.open = float(d[1])
            bar.high = float(d[2])
            bar.low = float(d[3])
            bar.close = float(d[4])
            bar.volume = float(d[5])
            barlist.append(bar)

    return barlist


def loadDeribitCsv(fileName, symbol, dbName=None):
    barlist = []
    start = time()

    reader = csv.reader(open(fileName, "r"))
    for d in reader:
        if 'open' not in d[1]:
            bar = VtBarData()
            bar.symbol = symbol
            bar.interval = '1m'  # K线周期.
            bar.exchange = EXCHANGE_DERIBIT
            bar.vtSymbol = '.'.join([bar.symbol, bar.exchange])
            bar.datetime = datetime.strptime(d[0], '%Y-%m-%d %H:%M:%S')
            bar.date = bar.datetime.date().strftime('%Y-%m-%d')
            bar.time = bar.datetime.time().strftime('%H:%M:%S')
            bar.open = float(d[1])
            bar.high = float(d[2])
            bar.low = float(d[3])
            bar.close = float(d[4])
            bar.volume = float(d[5])
            barlist.append(bar)

    return barlist

def loadMcCsvDB(fileName, dbName, symbol):
    """csv格式的历史数据插入到Mongo数据库中"""
    start = time()
    print(u'开始读取CSV文件%s中的数据插入到%s的%s中' % (fileName, dbName, symbol))

    # 锁定集合，并创建索引
    client = pymongo.MongoClient(globalSetting['mongoHost'], globalSetting['mongoPort'])
    collection = client[dbName][symbol]
    collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)

    # 读取数据和插入到数据库
    with open(fileName, 'r') as f:
        reader = csv.DictReader(f)
        for d in reader:
            bar = VtBarData()
            bar.vtSymbol = symbol
            bar.symbol = symbol
            bar.open = float(d['Open'])
            bar.high = float(d['High'])
            bar.low = float(d['Low'])
            bar.close = float(d['Close'])
            bar.date = datetime.strptime(d['Date'], '%Y-%m-%d').strftime('%Y%m%d')
            bar.time = d['Time']
            bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
            bar.volume = d['TotalVolume']
            bar.lastBar = False

            flt = {'datetime': bar.datetime}
            collection.update_one(flt, {'$set': bar.__dict__}, upsert=True)
            print(bar.date, bar.time)

    print(u'插入完毕，耗时：%s' % (time() - start))