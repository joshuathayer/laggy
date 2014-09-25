from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from base64 import b64encode, b64decode



class Crypto():
    def __init__(self):
        self.pub_key_fn  = None
        self.priv_key_fn = None
        self.key         = None

    def generate_key(self):
        new_key = RSA.generate(2048)
        # new_key = RSA.importKey(f.read())
        public_key = new_key.publickey().exportKey("PEM")
        private_key = new_key.exportKey("PEM")

        self.key = new_key
        return new_key, private_key, public_key
        # f = open('mykey.pem','w')
        # f.write(RSA.exportKey('PEM'))
        # f.close()
        # f = open('mykey.pem','r')
        
        # tor.bootstrap_tor(cfg, setup_complete)
        # reactor.run()


    def sign_data(self, data):
        """
        param: private_key_loc Path to your private key
        param: package Data to be signed
        return: base64 encoded signature
        """
        key = open(self.priv_key_fn, "r").read()
        rsakey = RSA.importKey(key)
        signer = PKCS1_v1_5.new(rsakey)
        digest = SHA256.new()
        digest.update(data)
        sign = signer.sign(digest)
        return b64encode(sign)

    def verify_sign(self, public_key_loc, signature, data):
        '''
        Verifies with a public key from whom the data came that it was indeed
        signed by their private key
        param: public_key_loc Path to public key
        param: signature String signature to be verified
        return: Boolean. True if the signature is valid; False otherwise.
        '''
        from Crypto.PublicKey import RSA
        from Crypto.Signature import PKCS1_v1_5
        from Crypto.Hash import SHA256
        from base64 import b64decode
        pub_key = open(public_key_loc, "r").read()
        rsakey = RSA.importKey(pub_key)
        signer = PKCS1_v1_5.new(rsakey)
        digest = SHA256.new()
        # Assumes the data is base64 encoded to begin with
        digest.update(b64decode(data))
        if signer.verify(digest, b64decode(signature)):
            return True
        return False
