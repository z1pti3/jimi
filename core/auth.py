import secrets
import base64
import hashlib
import time
import json
import jwt
import functools
from pathlib import Path
from Crypto.Cipher import AES, PKCS1_OAEP # pycryptodome
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

# Example ACL stored with object
# "acl" : { "ids" : [ { "accessID" : "", "read" : False, "write" : False, "delete" : False } ], "fields" : [ { "field" : "passwordHash", "ids" : [ { "accessID" : "", "read" : False, "write" : False, "delete" : False } ] } ] }

from core import db

class _user(db._document):
    name = str()
    enabled = bool()
    username = str()
    passwordHash = str()
    passwordHashType = str()
    failedLoginCount = int()
    lastLoginAttempt = int()
    apiTokens = list()
    primaryGroup = str()

    _dbCollection = db.db["users"]

    # Override parent new to include name var, parent class new run after class var update
    def new(self,name,username,password):
        existingUser = _user().query(query={ "username" : username })["results"]
        if len(existingUser) == 0:
            self.name = name
            self.username = username
            passwordHash = generatePasswordHash(password, username)
            self.passwordHashType = passwordHash[0]
            self.passwordHash = passwordHash[1]
            return super(_user, self).new()
        else:
            return None

    def setAttribute(self,attr,value,sessionData=None):
        if attr == "passwordHash" and not helpers.isBase64(value):
            if meetsPasswordPolicy(value):
                result = generatePasswordHash(value, self.username)
                self.passwordHash = result[1]
                self.passwordHashType = result[0]
                self.update(["passwordHash","passwordHashType"])
                return True
            else:
                return False
        setattr(self,attr,value)
        return True

    def newAPIToken(self):
        apiSessionToken = secrets.token_hex(128)
        self.apiTokens.append(apiSessionToken)
        self.update(["apiTokens"])
        return apiSessionToken

class _group(db._document):
    name = str()
    enabled = bool()
    members = list()
    apiTokens = list()

    _dbCollection = db.db["groups"]

    # Override parent new to include name var, parent class new run after class var update
    def new(self,name):
        existingGroups = _group().query(query={ "name" : name })["results"]
        if len(existingGroups) == 0:
            self.name = name
            return super(_group, self).new() 
        else:
            return None

from core import api, settings, helpers, audit
from system import install

authSettings = settings.config["auth"]

# Loading public and private keys for session signing
with open(Path(authSettings["rsa"]["cert"])) as f:
  sessionPublicKey = f.read()
with open(Path(authSettings["rsa"]["key"])) as f:
  sessionPrivateKey = f.read()

requiredhType = "j1"

def meetsPasswordPolicy(password):
    specialChars =  "!\"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"
    if len(password) < authSettings["policy"]["minLength"]:
        return False
    if sum(c.isdigit() for c in password) < authSettings["policy"]["minNumbers"]:
        return False
    if len([c for c in password if c.isalpha() and c.lower() == c]) < authSettings["policy"]["minLower"]:
        return False
    if len([c for c in password if c.isalpha() and c.upper() == c]) < authSettings["policy"]["minUpper"]:
        return False
    if len([c for c in password if c in specialChars]) < authSettings["policy"]["minSpecial"]:
        return False
    return True

def getPasswordFromENC(enc):
    if enc[:6] == "ENC j1":
        cipher_rsa = PKCS1_OAEP.new(RSA.import_key(sessionPrivateKey))
        encSecureKey = base64.b64decode(enc[7:].split(" ")[2].encode())
        secureKey = cipher_rsa.decrypt(encSecureKey)
        key = install.getSecure().encode() + secureKey
        key = hashlib.sha256(key).digest()
        nonce = base64.b64decode(enc[7:].split(" ")[0].encode())
        tag = base64.b64decode(enc[7:].split(" ")[1].encode())
        cipherText = base64.b64decode(enc[7:].split(" ")[3].encode())
        cipher = AES.new(key, AES.MODE_EAX, nonce = nonce)
        plaintext = cipher.decrypt(cipherText).decode()
        try:
            cipher.verify(tag)
            return plaintext
        except ValueError:
            return None
    else:
        key = hashlib.sha256(install.getSecure().encode()).digest()
        nonce = base64.b64decode(enc[4:].split(" ")[0].encode())
        tag = base64.b64decode(enc[4:].split(" ")[1].encode())
        cipherText = base64.b64decode(enc[4:].split(" ")[2].encode())
        cipher = AES.new(key, AES.MODE_EAX, nonce = nonce)
        plaintext = cipher.decrypt(cipherText).decode()
        try:
            cipher.verify(tag)
            return plaintext
        except ValueError:
            return None
    return None

def getENCFromPassword(password):
    if requiredhType == "j1":
        cipher_rsa = PKCS1_OAEP.new(RSA.import_key(sessionPublicKey))
        secureKey = get_random_bytes(16)
        encSecureKey = cipher_rsa.encrypt(secureKey)
        key = install.getSecure().encode() + secureKey
        key = hashlib.sha256(key).digest()
        cipher = AES.new(key, AES.MODE_EAX)
        nonce = cipher.nonce
        cipherText, tag = cipher.encrypt_and_digest(password.encode())
        return "j1 {0} {1} {2} {3}".format(base64.b64encode(nonce).decode(),base64.b64encode(tag).decode(),base64.b64encode(encSecureKey).decode(),base64.b64encode(cipherText).decode())
    else:
        key = hashlib.sha256(install.getSecure().encode()).digest()
        cipher = AES.new(key, AES.MODE_EAX)
        nonce = cipher.nonce
        cipherText, tag = cipher.encrypt_and_digest(password.encode())
        return "{0} {1} {2}".format(base64.b64encode(nonce).decode(),base64.b64encode(tag).decode(),base64.b64encode(cipherText).decode())

def generatePasswordHash(password,salt,hType="j1"):
    hash = None
    if hType == "j1":
        hash = base64.b64encode(hashlib.pbkdf2_hmac("sha512", password.encode(), salt.encode(), 100000))
    return [hType,hash.decode()]

def generateSession(dataDict):
    dataDict["expiry"] = time.time() + authSettings["sessionTimeout"]
    if "CSRF" not in dataDict:
        dataDict["CSRF"] = secrets.token_urlsafe(16)
    return jwt.encode(dataDict, sessionPrivateKey.encode(), algorithm="RS256")

def generateSystemSession():
    data = { "expiry" : time.time() + 10, "admin" : True, "_id" : 0, "primaryGroup" : 0, "authenticated" : True, "api" : True }
    return jwt.encode(data, sessionPrivateKey.encode(), algorithm="RS256")

def validateSession(sessionToken):
    try:
        dataDict = jwt.decode(sessionToken, sessionPublicKey.encode(), algorithm="RS256")
        if dataDict["authenticated"]:
            if dataDict["expiry"] < time.time():
                return None
            elif dataDict["expiry"] < time.time() + ( authSettings["sessionTimeout"] / 4 ):
                return { "sessionData" : dataDict, "sessionToken" : sessionToken, "renew" : True }
            else:
                return { "sessionData" : dataDict, "sessionToken" : sessionToken }
    except:
        pass
    return None

def validateUser(username,password):
    user = _user().getAsClass(query={ "username" : username })
    if len(user) == 1:
        user = user[0]
        # Account lockout check
        if (user.failedLoginCount >= 5) and (user.lastLoginAttempt + 60 > time.time()):
            return None
        elif user.failedLoginCount >= 5:
            user.failedLoginCount = 0

        user.lastLoginAttempt = time.time()
        passwordHash = generatePasswordHash(password, username, user.passwordHashType)
        if passwordHash[1] == user.passwordHash:
            # If user password hash does not meet the required standard update
            if user.passwordHashType != requiredhType:
                passwordHash = generatePasswordHash(password,username)
                user.passwordHashType = passwordHash[0]
                user.passwordHash = passwordHash[1]
                user.update(["passwordHashType","passwordHash"])
            user.failedLoginCount = 0
            user.update(["lastLoginAttempt","failedLoginCount"])
            audit._audit().add("auth","login",{ "action" : "sucess", "src_ip" : api.request.remote_addr, "username" : username, "_id" : user._id, "accessIDs" : enumerateGroups(user), "primaryGroup" :user.primaryGroup, "admin" : isAdmin(user) })
            return generateSession({ "_id" : user._id, "primaryGroup" : user.primaryGroup, "admin" : isAdmin(user), "accessIDs" : enumerateGroups(user), "authenticated" : True })
        else:
            user.failedLoginCount+=1
            user.update(["lastLoginAttempt","failedLoginCount"])
    audit._audit().add("auth","login",{ "action" : "failed", "src_ip" : api.request.remote_addr, "username" : username })
    return None

# Needs to be converted into authorization roles e.g. admin
def requireAuthentication(func):
    def decorated_function(*args, **kwargs):
        if "jimiAuth" in api.request.cookies:
            validSession = validateSession(api.request.cookies["jimiAuth"])
            if not validSession:
                return api.redirect("/login", code=302)
        return func(*args, **kwargs)
    return decorated_function

def enumerateGroups(user):
    accessIDs = []
    group = _group().getAsClass(id=user.primaryGroup)
    if len(group) == 1:
        group = group[0]
        if user._id in group.members:
            accessIDs.append(group._id)
    for groupItem in _group().getAsClass(query={ "members" : { "$in" : [ user._id ] } }):
        if groupItem._id not in accessIDs:
            accessIDs.append(groupItem._id)
    return accessIDs

def isAdmin(user):
    adminGroup = _group().getAsClass(query={ "name" : "admin", "members" : { "$in" : [ user._id ] } })
    if len(adminGroup) == 1:
        return True
    return False

######### --------- API --------- #########
if api.webServer:
    if not api.webServer.got_first_request:
        # Ensures that all requests require basic level of authentication ( athorization handled by dectirators )
        @api.webServer.before_request
        def api_alwaysAuthBefore():
            api.g = { "sessionData" : {}, "sessionToken": "", "type" : "" }
            if authSettings["enabled"]:
                noAuthEndPoints = ["static","loginPage","api_validateUser","api_validateAPIKey"]
                if api.request.endpoint not in noAuthEndPoints:
                    validSession = None
                    if "jimiAuth" in api.request.cookies:
                        validSession = validateSession(api.request.cookies["jimiAuth"])
                        if not validSession:
                            return api.redirect("/login?return={0}".format(api.request.full_path), code=302)
                        api.g["type"] = "cookie"
                        # Confirm CSRF
                        if api.request.method in ["POST","PUI","DELETE"]:
                            try:
                                data = json.loads(api.request.data)
                                if "CSRF" not in data:
                                    raise KeyError
                            except:
                                try:
                                    data = json.loads(list(api.request.form.to_dict().keys())[0])
                                    if "CSRF" not in data:
                                        raise KeyError
                                except:
                                    data = api.request.form["CSRF"]
                            if validSession["sessionData"]["CSRF"] != data["CSRF"]:
                                return {}, 403
                    elif "x-api-token" in api.request.headers:
                        validSession = validateSession(api.request.headers.get("x-api-token"))
                        if not validSession:
                            return {}, 403
                        #if validSession["sessionData"]["api"] != True:
                        #    return {}, 403
                        api.g["type"] = "x-api-token"
                    else: 
                        return api.redirect("/login?return={0}".format(api.request.full_path), code=302)
                    # Data that is returned to the Flask request handler function
                    api.g["sessionData"] = validSession["sessionData"]
                    api.g["sessionToken"] = validSession["sessionToken"]
                    if "renew" in validSession:
                        api.g["renew"] = validSession["renew"]
                else:
                    api.g["type"] = "bypass"
            
        # Ensures that all requests return an up to date sessionToken to prevent session timeout for valid sessions
        @api.webServer.after_request
        def api_alwaysAuthAfter(response):
            if authSettings["enabled"]:
                    if api.g["type"] != "bypass":
                        if api.g["type"] == "cookie":
                            if "renew" in api.g:
                                response.set_cookie("jimiAuth", value=generateSession(api.g["sessionData"]), max_age=600) # Need to add secure=True before production, httponly=False cant be used due to auth polling
            # Cache Weakness
            if api.request.endpoint != "static": 
                response.headers['Cache-Control'] = 'no-cache, no-store'
                response.headers['Pragma'] = 'no-cache'
            # ClickJacking
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            return response

        # Checks that username and password are a match
        @api.webServer.route(api.base+"auth/", methods=["POST"])
        def api_validateUser():
            response = api.make_response()
            data = json.loads(api.request.data)
            userSession = validateUser(data["username"],data["password"])
            if userSession:
                response.set_cookie("jimiAuth", value=userSession, max_age=600) # Need to add secure=True before production
                return response, 200
            return response, 403

        # Called by API systems to request an x-api-token string from x-api-key provided
        @api.webServer.route(api.base+"auth/", methods=["GET"])
        def api_validateAPIKey():
            if "x-api-key" in api.request.headers:
                user = _user().getAsClass(query={ "apiTokens" : { "$in" : [ api.request.headers.get("x-api-key") ] } } )
                if len(user) == 1:
                    user = user[0]  
                    return { "x-api-token" : generateSession({ "_id" : user._id, "primaryGroup" : user.primaryGroup, "admin" : isAdmin(user), "accessIDs" : enumerateGroups(user), "authenticated" : True })}
            return {}, 404

        @api.webServer.route(api.base+"auth/poll/", methods=["GET"])
        def api_sessionPolling():
            return { "data" : True }, 200     

        @api.webServer.route(api.base+"auth/logout/", methods=["GET"])
        def api_logout():
            response = api.make_response(api.redirect("/login?return=/?"))
            response.set_cookie("jimiAuth", value="")
            audit._audit().add("auth","logout",{ "action" : "sucess", "_id" : api.g["sessionData"]["_id"] })
            return response, 302

        # Checks that username and password are a match
        @api.webServer.route(api.base+"auth/myAccount/", methods=["POST"])
        def api_updateMyAccount():
            user = _user().getAsClass(id=api.g["sessionData"]["_id"])
            if len(user) == 1:
                user = user[0]
                data = json.loads(api.request.data)
                user.setAttribute("passwordHash",data["data"]["passwordHash"],sessionData=api.g["sessionData"])
                user.setAttribute("name",data["data"]["name"],sessionData=api.g["sessionData"])
                user.update(["name","passwordHash","apiTokens"])
                return {}, 200
            return {}, 403

        # Called by API systems to request an x-api-token string from x-api-key provided
        @api.webServer.route(api.base+"auth/myAccount/", methods=["GET"])
        def api_getMyAccount():
            user = _user().getAsClass(id=api.g["sessionData"]["_id"])
            if len(user) == 1:
                user = user[0]
                userProps = {}
                userProps["name"] = user.name
                userProps["passwordHash"] = user.passwordHash
                return { "results" : [ userProps ] }, 200
            return { }, 404