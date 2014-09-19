from stem.control import Controller
from stem import SocketError

import socket
import socks
import stem

class NoTor(Exception):
    pass

# with thanks to onionshare
def choose_port():
    # let the OS choose a port
    return
    return port

# this is an artifact from testing... should likely go away
def get_hidden_service_dir(ths_dir, port):
    return ths_dir
    # return "/tmp/plough_hidden_service_{}".format(port)

def get_hidden_service_hostname(ths_dir, port):
    hostname_file = '{0}/hostname'.format(get_hidden_service_dir(ths_dir, port))
    return open(hostname_file, 'r').read().strip()

def start_hidden_service(cfg, port, log):
    # connect to the tor controlport
    controlports = [9051, 9151]
    controller = False
    
    ths_dir = cfg['ths_dir']

    for controlport in controlports:
        try:
            if controller:
                pass
            log.err("trying {}".format(controlport))
            controller = Controller.from_port(port=controlport)
            break
        except SocketError:
            pass

    if not controller:
        raise NoTor("No TOR!")
        sys.exit()

    try:
        controller.authenticate()
    except stem.connection.MissingPassword:
        try:
            controller.authenticate_password(cfg['tor_control_password'])
        except stem.connection.PasswordAuthFailed:
            log.err("tor control password failed")
            raise NoTor("bad password")
        
    if cfg['configure_ths'] is False:
        log.err("Avoiding hidden service configuration: already done, eh?")
        onion_host = get_hidden_service_hostname(ths_dir, port)
        log.err("Forwarding onion url {}:80 to 127.0.0.1:{}".format(onion_host, port))
        return True

    # everything below here is hosed. see https://trac.torproject.org/projects/tor/ticket/12533
    # just configure ths in your torrc for now
    try:
        print controller.get_conf('HiddenServiceDir', multiple=True)
    except Exception, e:
        print "could not get options:",e
    
    hs_dir = get_hidden_service_dir(ths_dir, port)
    hs_port = '80 127.0.0.1:{0}'.format(port)
    
    controller.set_options([
        ('HiddenServiceDir', hs_dir),
        ('HiddenServicePort', hs_port)
    ])

    onion_host = get_hidden_service_hostname(ths_dir, port)
    print "!!! forwarding onion url {}:80 to 127.0.0.1:{}".format(onion_host, port)
    return onion_host
