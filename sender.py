from twisted.internet.endpoints import TCP4ClientEndpoint
from txsocksx.http import SOCKS5Agent
import json
import base64
from twisted.web.iweb import IBodyProducer
from twisted.web.http_headers import Headers
from zope.interface import implements
from twisted.internet import reactor
from twisted.python import log

class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class Sender():
    def __init__(self, cfg):
        self.cfg    = cfg
        self.peer   = None
        self.screen = None
        self.agent  = None
        self.crypto = None

    def ensure_agent(self):
        if self.agent is None:
            torServerEndpoint = TCP4ClientEndpoint(reactor,
                                                   '127.0.0.1',
                                                   self.cfg['tor_proxy_port'])
            self.agent = SOCKS5Agent(reactor, proxyEndpoint=torServerEndpoint)

    def request(self, url, data):
        self.ensure_agent()

        sig = self.crypto.sign_data(data)
        
        json_data = json.dumps({'sig': sig,
                                'data': base64.b64encode(data)})
        
        log.err("peer url is {}".format(url))
        log.err("data is {}".format(json_data))

        d = self.agent.request('POST',
                          url,
                          Headers({"content-type": ["application/json"]}),
                          StringProducer(json_data))

        def cb(res):
            self.screen.addLine("POST to peer result {}".format(res.code))
            log.err("got a result from POST: {}".format(res.code))
        
        def ecb(res):
            self.screen.addLine("POST to peer resuled in error")
            log.err("got a error from POST: {}".format(res))

        d.addCallback(cb)
        d.addErrback(ecb)


    def alert(self, data):
        url = "http://{}/alert".format(self.peer)

        self.request(url, data)
        
    def send(self, data):
        url = "http://{}/voice".format(self.peer)

        self.request(url, data)
