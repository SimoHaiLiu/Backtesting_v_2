# encoding: UTF-8
import datetime

from trader.vtCalculateGreek import calculateGreeks

greeks = calculateGreeks()
startTime = datetime.datetime.now()

delta = greeks.calculateDelta()
vega = greeks.calculateVega()
rho = greeks.calculateRho()
theta = greeks.calculateTheta()
gamma = greeks.calculateGamma()
print delta, vega, rho, theta, gamma

endTime = datetime.datetime.now()

print endTime - startTime
