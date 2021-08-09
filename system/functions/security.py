from core import auth

def encryptString(plaintext,secureString):
    try:
        if len(secureString) < 4:
            return ""
        return "ENC {0}".format(auth.getENCFromPassword(plaintext,secureString))
    except:
        return ""

def decryptString(encryptedString,secureString):
    try:
        if len(secureString) < 4:
            return ""
        return auth.getPasswordFromENC(encryptedString,secureString)
    except:
        return ""

