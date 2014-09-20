#!/usr/bin/python

from twisted.python import log
from twisted.internet.defer import Deferred
from twisted.internet import defer, stdio
from twisted.protocols import basic
from twisted.internet.protocol import Protocol
from twisted.web import server, resource
from twisted.web.http_headers import Headers
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from txsocksx.http import SOCKS5Agent

import sys, tty, termios
import base64
import StringIO
import wave

import cyclone.httpclient
import cyclone.jsonrpc

import curses, time, traceback, sys
import curses.wrapper

import display
import argparse
import yaml
import tor
import rec
import socks
import socket

from zope.interface import implements
from twisted.internet.defer import succeed
from twisted.web.iweb import IBodyProducer

import pyaudio
p = pyaudio.PyAudio()

SHORT_NORMALIZE = (1.0/32768.0)
chunk           = 1024
FORMAT          = pyaudio.paInt16
CHANNELS        = 1
RATE            = 16000
swidth          = 2
Max_Seconds     = 10
TimeoutSignal   = ((RATE / chunk * Max_Seconds) + 2)
silence         = True
FileNameTmp     = '/tmp/hello.wav'
Time            = 0

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
        self.cfg = cfg
        self.peer = None
        self.screen = None
        self.agent = None

    def ensure_agent(self):
        if self.agent is None:
            torServerEndpoint = TCP4ClientEndpoint(reactor, '127.0.0.1', self.cfg['tor_proxy_port'])
            self.agent = SOCKS5Agent(reactor, proxyEndpoint=torServerEndpoint)

    def alert(self, data):
        self.ensure_agent()
        
        self.screen.addLine("Alerting peer.")

        url = "http://{}/alert".format(self.peer)
        log.err("peer url is {}".format(url))

        d = self.agent.request('POST',
                          url,
                          Headers({"content-type": ["application/octet-stream"]}),
                          StringProducer(data))

        def cb(res):
            self.screen.addLine("Peer alert POST result {}".format(res.code))
            log.err("got a result from POST: {}".format(res.code))
        
        def ecb(res):
            self.screen.addLine("Peer alert POST resuled in error {}".format(res))
            log.err("got a error from POST: {}".format(res))

        d.addCallback(cb)
        d.addErrback(ecb)
        
    def send(self, data):
        self.ensure_agent()
        
        url = "http://{}/voice".format(self.peer)
        
        self.screen.addLine("Going to attempt to send recording to {}".format(url))
        d = self.agent.request('POST',
                        url,
                          Headers({"content-type": ["application/octet-stream"]}),
                          StringProducer(data))
        
        self.wf = None
        self.df = None
        
        def cb(res):
            self.screen.addLine("Peer POST result {}".format(res.code))
            log.err("got a result from POST: {}".format(res.code))
        
        def ecb(res):
            self.screen.addLine("Peer POST resuled in error {}".format(res))
            log.err("got a error from POST: {}".format(res))

        d.addCallback(cb)
        d.addErrback(ecb)

class AlertHandler(cyclone.web.RequestHandler):

    def post(self):
        req = self.request
        data = req.body

        self.application.screen.addLine("Received message from peer: {}".format(data))


class Player():
    def __init__(self):
        self.messages = []
        self.am_playing = False

    def add_message(self, data):
        self.messages.append(data)

        if not self.am_playing:
            self.play()

    def play(self):
        if len(self.messages):
            data = self.messages.pop()
        else:
            return

        df = StringIO.StringIO()
        df.write(data)
        df.seek(0)
        wf = wave.open(df, 'rb')
 
        def cb(in_data, frame_count, time_info, status):
            data = wf.readframes(frame_count)

            if not data:
                self.am_playing = False
                self.play()

            return (data, pyaudio.paContinue)

        self.am_playing = True
        stream = p.open(format            = FORMAT,
                        channels          = CHANNELS,
                        rate              = RATE,
                        output            = True,
                        frames_per_buffer = chunk,
                        stream_callback   = cb)
            
class VoiceHandler(cyclone.web.RequestHandler):
    def initialize(self, player):
        self.player = player

    def post(self):
        req = self.request

        self.application.screen.addLine("Received {} bytes from peer.".format(len(req.body)))

        self.player.add_message(req.body)
        
        
def main():
    try:
        log.startLogging(open('./rec.log', 'w'))

        parser = argparse.ArgumentParser()
        parser.add_argument("--config", dest="config", nargs=1)
        parser.add_argument("peer")
        args = parser.parse_args()
        
        conffile = open(args.config[0],'r')
        cfg = yaml.load(conffile)

        roster_raw = yaml.load(open("roster.yml"))
        roster = { r['name']: {'onion': r['onion']} for r in roster_raw['peers'] }

        if args.peer not in roster:
            msg = "Could not find peer {}, cannot start".format(args.peer)
            print msg
            log.err(msg)
            sys.exit()

        # tor it up
        host, port = cfg['bind'].split(':')
        if cfg['disable_ths'] is False:
            onion_host = tor.start_hidden_service(cfg, port, log)

        # proxy
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9150, True)
        socket.socket = socks.socksocket

        # audio recorder
        recorder = rec.Rec()
        recorder.log = log

        # audio player
        player = Player()

        # sender, sends data to peer
        sender = Sender(cfg)

        peer_onion = roster[args.peer]['onion']
        sender.peer = peer_onion

        recorder.sender = sender

        # screen
        stdscr = curses.initscr() # initialize curses
        screen = display.Screen(stdscr, recorder)   # create Screen object
        stdscr.refresh()

        recorder.screen = screen
        sender.screen   = screen

        reactor.addReader(screen) # add screen object as a reader to the reactor

        # http application
        application = cyclone.web.Application([
            (r"/voice", VoiceHandler, dict(player=player)),
            (r"/alert", AlertHandler)
        ])

        application.screen = screen

        reactor.listenTCP(int(port), application)
        reactor.run()

    finally:
        #restore_term()
        log.err("In finally handler.")
        
if __name__ == '__main__':
    main()
