import txtorcon
from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.python import log
import functools

# config tor via txtorcon.
# thanks https://github.com/meejah/txtorcon/blob/master/examples/launch_tor_with_hiddenservice.py
def updates(prog, tag, summary):
    log.err("{}%: {}".format(prog, summary))

def setup_failed(arg):
    log.err("tor setup failure: {}".format(arg))
    reactor.stop()

def bootstrap_tor(cfg, cb):
    hs_port               = cfg['local_port']
    hs_public_port        = 80
    hs_temp               = cfg['ths_dir']
    
    config                = txtorcon.TorConfig()
    config.SOCKSPort      = cfg['tor_proxy_port']
    config.HiddenServices = [txtorcon.HiddenService(config, hs_temp, [str(80) + " 127.0.0.1:" + str(hs_port)])]
    config.save()

    d = txtorcon.launch_tor(config, reactor, progress_updates=updates)

    def inner_cb(proto):
        log.err("in inner cb")
        cb([config, proto])

    d.addCallback(inner_cb)
    d.addErrback(setup_failed)
