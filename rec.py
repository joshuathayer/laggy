import pyaudio
from twisted.python import log
from twisted.internet.defer import Deferred
from twisted.internet import defer, stdio
from twisted.protocols import basic
from twisted.internet.protocol import Protocol
from twisted.web import server, resource
from twisted.internet import reactor

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
import socks
import socket

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

p = pyaudio.PyAudio()

class Rec():

    def __init__(self):
        self._rec_state = False
        self.stream = None
        self.screen = None
        self.frames = []

    def is_recording(self):
        return self._rec_state

    def open_stream(self, cb):
        stream = p.open(format            = FORMAT,
                        channels          = CHANNELS,
                        rate              = RATE,
                        input             = True,
                        frames_per_buffer = chunk,
                        stream_callback   = cb)
        return stream

    def get_stream(self, chunk, caller_cb):
        if self.stream is None:
            def cb(in_data, frame_count, time_info, status):
                caller_cb(in_data)
                return in_data, pyaudio.paContinue

            self.stream = self.open_stream(cb)
        else:
            log.err("stream already open")

        self.stream.start_stream()
    
    def do_rec(self):
 
        def handle_recorded(data):
            self.wf.writeframes(data)
            
        self.get_stream(1024, handle_recorded)
        
    def toggle(self):
        self._rec_state = not self._rec_state
        if self._rec_state:
            df = StringIO.StringIO()
            wf = wave.open(df, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(RATE)
            self.wf = wf
            self.df = df

            self.do_rec()
        else:
            self.stream.close() # not sure why, but stop_stream hangs
            self.wf.close()
            self.df.seek(0)

            data = self.df.read()
            # url = "http://10.52.128.131:9999/voice"
            url = "http://10.52.128.172:9999/voice"

            cli = cyclone.httpclient.fetch(url,
                                           headers={"content-type": ["application/octet-stream"]},
                                           postdata=data)

            self.wf = None
            self.df = None

            def cb(res):
                self.screen.addLine("Peer POST result {}".format(res.code))
                log.err("got a result from POST: {}".format(res.code))

            cli.addCallback(cb)

            self.stream = None
            self.frames = []
            
            
class VoiceHandler(cyclone.web.RequestHandler):

    def post(self):
        req = self.request

        self.application.screen.addLine("Received {} bytes from peer.".format(len(req.body)))
        
        df = StringIO.StringIO()
        df.write(req.body)
        df.seek(0)
        wf = wave.open(df, 'rb')
 
        def cb(in_data, frame_count, time_info, status):
            data = wf.readframes(frame_count)
            return (data, pyaudio.paContinue)
        
        stream = p.open(format            = FORMAT,
                        channels          = CHANNELS,
                        rate              = RATE,
                        output            = True,
                        frames_per_buffer = chunk,
                        stream_callback   = cb)

def main():
    try:
        log.startLogging(open('./rec.log', 'w'))

        parser = argparse.ArgumentParser()
        parser.add_argument("config")
        args = parser.parse_args()
        
        conffile = open(args.config,'r')
        cfg = yaml.load(conffile)

        # tor it up
        host, port = cfg['bind'].split(':')
        if cfg['disable_ths'] is False:
            onion_host = tor.start_hidden_service(cfg, port, log)

        # proxy
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", 9150, True)
        socket.socket = socks.socksocket

        # audio recorder
        recorder = Rec()

        # screen
        stdscr = curses.initscr() # initialize curses
        screen = display.Screen(stdscr, recorder)   # create Screen object
        stdscr.refresh()

        recorder.screen = screen

        reactor.addReader(screen) # add screen object as a reader to the reactor

        # http application
        application = cyclone.web.Application([
            (r"/voice", VoiceHandler)])

        application.screen = screen

        reactor.listenTCP(int(port), application)
        reactor.run()

    finally:
        #restore_term()
        log.err("In finally handler.")
        
if __name__ == '__main__':
    main()
