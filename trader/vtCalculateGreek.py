# encoding: UTF-8

'''
S: price(标的物价格)
K: strike price(行权价)
T: time to maturity(到期时间)
r: interest rate(无风险利率)
q: rate of continuous dividend paying asset(资产分红)
self.sigma: volatility of underlying asset(隐含波动率)

'''
import datetime

from scipy import stats, log, sqrt, exp, pi

# 计算希腊值和隐含波动率时用的参数
expDeribit = '2019-04-26 08:00:00 GMT'
expBitmex = '2019-06-28T12:00:00.000Z'
expBitmex1 = '2014-09-18T10:42:16.126Z'
UTC_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
GMT_FORMAT = None

currentTime = datetime.datetime.now()

tmp_datetime = datetime.datetime.strptime(expBitmex, UTC_FORMAT) - currentTime

S = 110.0
K = 100.
T = 1.0
r = 0.05
q = 0.001
sigma = 0.25
option = 'call'


# ----------------------------------------------------------------------
class calculateGreeks(object):
    def __init__(self):
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.q = q
        self.sigma = sigma
        self.option = option
        self.d1 = (log(self.S / self.K) + (self.r - self.q + 0.5 * self.sigma ** 2) * self.T) / (
                self.sigma * sqrt(self.T))
        self.d2 = (log(self.S / self.K) + (self.r - self.q - 0.5 * self.sigma ** 2) * self.T) / (
                self.sigma * sqrt(self.T))

    def calculateDelta(self):
        """计算Delta值"""
        delta = None
        if self.option == 'call':
            delta = exp(-self.q * self.T) * stats.norm.cdf(self.d1, 0.0, 1.0)
        if self.option == 'put':
            delta = -exp(-self.q * self.T) * stats.norm.cdf(-self.d1, 0.0, 1.0)
        return delta

    # ----------------------------------------------------------------------
    def calculateGamma(self):
        """计算Gamma值"""
        gamma = exp(-self.q * self.T - 0.5 * (self.d1 ** 2)) / (sqrt(2.0 * pi) * self.S * self.sigma * sqrt(self.T))
        return gamma

    # ----------------------------------------------------------------------
    def calculateTheta(self):
        """计算Theta值"""
        theta = None
        if option == 'call':
            theta = -self.S * exp(-self.q * self.T - 0.5 * (self.d1 ** 2)) * self.sigma / (
                    2 * sqrt(2.0 * pi * self.T)) - self.r * self.K * exp(
                -self.r * self.T) * stats.norm.cdf(self.d2, 0.0, 1.0) + self.q * self.S * exp(
                -self.q * self.T) * stats.norm.cdf(self.d1, 0.0, 1.0)
        if option == 'put':
            theta = -self.S * exp(-self.q * self.T - 0.5 * (self.d1 ** 2)) * self.sigma / (
                    2 * sqrt(2.0 * pi * self.T)) + self.r * self.K * exp(
                -self.r * self.T) * stats.norm.cdf(-self.d2, 0.0, 1.0) - self.q * self.S * exp(
                -self.q * self.T) * stats.norm.cdf(-self.d1, 0.0, 1.0)
        theta = theta / 365.0
        return theta

    # ----------------------------------------------------------------------
    def calculateVega(self):
        """计算Vega值"""
        vega = 1 / sqrt(2 * pi) * self.S * exp(-self.q * self.T) * exp(-self.d1 ** 2 * 0.5) * sqrt(self.T)
        vega = vega / 100.0
        return vega

    def calculateRho(self):
        """计算Rho值"""
        rho = None
        if option == 'call':
            rho = self.K * self.T * exp(-self.r * self.T) * stats.norm.cdf(self.d2, 0.0, 1.0)
        if option == 'put':
            rho = -self.K * self.T * exp(-self.r * self.T) * stats.norm.cdf(-self.d2, 0.0, 1.0)
        rho = rho / 100.0
        return rho
