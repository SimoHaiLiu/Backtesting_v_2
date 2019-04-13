import json
from ws4py.client.threadedclient import WebSocketClient
from datetime import datetime
import datetime as dt
import dateutil.parser as dp

class CG_Client(WebSocketClient):
    counter = long(0)
    ttlJitter = float(0)
    avgJitter = float(0)
    tick = '00:00:00.000'
    def opened(self):
        req = '{"op": "subscribe","args": ["orderBook10:XBTUSD"]}'
       
        self.send(req)

    def closed(self, code, reason=None):
        print("Closed down:", code, reason)

    def received_message(self, msg):
        #print msg
        msg = json.loads(str(msg))
        
        
        if 'table' in msg and 'orderBook' in msg['table']:# and 'action' in msg :
            for d in msg['data']:
                localTime = datetime.now()
                ts = dp.parse(str(d['timestamp']))#+dt.timedelta(hours=8)
                tss = ts.strftime('%H:%M:%S.%f')[:-3]
                
        #if tss[:-2] == tick.time[:-2]:
            #return        
        #tick.time = tss
                lt = localTime.strftime('%H:%M:%S.%f')[:-3]
                td = (localTime-ts.replace(tzinfo = None)).total_seconds()
        #if td>2:
                self.counter += 1
                self.ttlJitter += td
                self.avgJitter = self.ttlJitter/self.counter
                if self.tick[4] != tss[4]:
                    
                    print 'BM',d['symbol'],lt, tss, td, self.counter, self.avgJitter
                self.tick = tss
                        


if __name__ == '__main__':
    ws = None
    try:
        ws = CG_Client('wss://www.bitmex.com/realtime')
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()
