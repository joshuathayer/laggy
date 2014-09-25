#!/usr/bin/python

from twisted.python import log
from twisted.internet.defer import Deferred
from twisted.internet import defer, stdio
from twisted.protocols import basic
from twisted.internet.protocol import Protocol
from twisted.web import server, resource
from twisted.internet import reactor

from base64 import b64encode, b64decode

import sys
import base64
import StringIO
import wave

import cyclone.httpclient

import curses, time, traceback, sys
import curses.wrapper

import display
import argparse
import yaml
import tor
import rec
import socks
import socket
import crypto
import json
import sender
import card

from twisted.internet.defer import succeed

from requests import Request

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


class AlertHandler(cyclone.web.RequestHandler):

    def post(self):
        req = self.request
        body = json.loads(req.body)
        data = base64.b64decode(body['data'])
        sig  = body['sig']

        self.application.screen.addLine("Received message from peer: {}".format(data))

            
class VoiceHandler(cyclone.web.RequestHandler):
    def initialize(self, player):
        self.player = player

    def post(self):
        req = self.request
        body = json.loads(req.body)
        data = base64.b64decode(body['data'])
        sig  = body['sig']

        self.application.screen.addLine("Received {} bytes from peer.".format(len(req.body)))

        self.player.add_message(req.body)

        
@defer.inlineCallbacks
def configure_app():
    log.startLogging(open('./rec.log', 'w'))

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", dest="config", nargs=1)
    parser.add_argument("peer")
    args = parser.parse_args()
    
    conffile = open(args.config[0],'r')
    cfg = yaml.load(conffile)
    
    ident = card.read_card(cfg['identity'])
    peer = card.read_card(args.peer)

    log.err("You are {}. You wish to communicate with {}.".format(ident['service'], peer['service']))

    d = Deferred()
    tor.bootstrap_tor(cfg, d.callback)
    [tor_config, process_proto] = yield d
    protocol = process_proto.tor_protocol

    print "Tor has launched.\nProtocol:", protocol
    info = yield protocol.get_info('traffic/read', 'traffic/written')
    print info
    
    # audio recorder
    recorder = rec.Rec()
    recorder.log = log
    
    # audio player
    player = Player()
    
    # sender, sends data to peer
    send = sender.Sender(cfg)
    
    peer_onion = peer['service']
    send.peer = peer_onion
    
    recorder.sender = send
    
    # screen
    stdscr = curses.initscr() # initialize curses
    screen = display.Screen(stdscr, recorder)   # create Screen object
    stdscr.refresh()
    
    recorder.screen = screen
    send.screen   = screen
    
    # crypto
    crypt = crypto.Crypto()
    crypt.priv_key_fn = "id_rsa"
    
    send.crypto = crypt
    
    reactor.addReader(screen) # add screen object as a reader to the reactor
    
    # http application
    application = cyclone.web.Application([
        (r"/voice", VoiceHandler, dict(player=player)),
        (r"/alert", AlertHandler)
    ])
    
    application.screen = screen
    
    reactor.listenTCP(int(cfg['local_port']), application)
    
def main():
    try:
        reactor.callWhenRunning(configure_app)
        reactor.run()

    finally:
        log.err("In finally handler.")
        
if __name__ == '__main__':
    main()
