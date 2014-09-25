import json
from base64 import b64encode, b64decode


def read_card(fn):
    f = open(fn, 'r')
    user = json.loads(b64decode(f.read()))
    f.close()
    return user

class Card():
    def __init__(self):
        self.name    = ''
        self.RSA     = ''
        self.service = ''
        self.sig     = ''
