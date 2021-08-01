from core import auth

def encryptString(plaintext,secureString):
    try:
        return "ENC {0}".format(auth.getENCFromPassword(plaintext,secureString))
    except:
        return ""

def decryptString(encryptedString,secureString):
    try:
        return auth.getPasswordFromENC(encryptedString,secureString)
    except:
        return ""

