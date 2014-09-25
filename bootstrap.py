#!/usr/bin/python

# bootstrap a laggy user:
# * create an RSA keypair
# * create a tor hidden service key
# * accept a username
# * create a "card" file which contains public key and ths service, and
#   can be exchanged with peers for identiy.

import argparse
import yaml
import tor
from twisted.internet import reactor
import json
import crypto

from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from base64 import b64encode, b64decode
from Crypto.PublicKey import RSA

from twisted.internet.defer import Deferred
from twisted.internet import defer, stdio

from twisted.python import log

parser = argparse.ArgumentParser()
parser.add_argument("config")
parser.add_argument("username")
args = parser.parse_args()

conffile = open(args.config,'r')
cfg = yaml.load(conffile)

def make_cards(ths):
    c = crypto.Crypto()
    key, pub, prv = c.generate_key()

    signer = PKCS1_v1_5.new(key)
    digest = SHA256.new()
    digest.update(args.username)
    digest.update(ths)
    sign = signer.sign(digest)
    sig = b64encode(sign)

    # public
    card = { 'name': args.username,
             'RSA': pub,
             'service': ths,
             'sig': sig }

    fn = "".join([c for c in args.username if c.isalpha() or c.isdigit()]).rstrip()

    f = open("{}.laggy".format(fn),'w')
    f.write(b64encode(json.dumps(card)))
    f.close()

    # private
    priv = { 'name': args.username,
             'RSA': key.exportKey('PEM'),
             'service': ths }

    f = open("{}-private.laggy".format(fn),'w')
    f.write(b64encode(json.dumps(priv)))
    f.close()
    reactor.stop()
    
@defer.inlineCallbacks
def do_bootstrap():

    d = Deferred()
    tor.bootstrap_tor(cfg, d.callback)
    [config, process_proto] = yield d
    log.err("ok i am here, i have config and process_proto")
    
    onion_address = config.HiddenServices[0].hostname
    make_cards(onion_address)
        
def main():
    try:
        reactor.callWhenRunning(do_bootstrap)
        reactor.run()

    finally:
        log.err("In finally handler.")
        
if __name__ == '__main__':
    main()
    log.startLogging(open('./bootstrap.log', 'w'))
