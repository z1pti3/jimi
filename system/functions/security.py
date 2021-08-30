import secrets

import jimi

def encryptString(plaintext,secureString=""):
    try:
        secureString = secureRandom(32)
        return "ENC {0} {1}".format(jimi.auth.getENCFromPassword(plaintext,secureString),secureString)
    except:
        return ""

def decryptString(encryptedString,secureString=""):
    try:
        secureString = encryptedString.split(" ")[6]
        return jimi.auth.getPasswordFromENC(encryptedString,secureString)
    except:
        return ""

def secureRandom(bytes=128):
    return secrets.token_hex(bytes)
