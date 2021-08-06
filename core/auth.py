import secrets
import base64
import urllib
import hashlib
import time
import json
import jwt
import hmac
import math
import functools
import onetimepass
from pathlib import Path
from Crypto.Cipher import AES, PKCS1_OAEP # pycryptodome
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from werkzeug.utils import redirect
from ldap3 import Server, Connection, ALL, NTLM

import jimi

# Example ACL stored with object
# "acl" : { "ids" : [ { "accessID" : "", "read" : False, "write" : False, "delete" : False } ], "fields" : [ { "field" : "passwordHash", "ids" : [ { "accessID" : "", "read" : False, "write" : False, "delete" : False } ] } ] }

class _session(jimi.db._document):
    user = str()
    sessionID = str()
    sessionStartTime = int()
    application = str()

    _dbCollection = jimi.db.db["sessions"]

    def new(self,user,sessionID,application):
        self.user = user
        self.sessionID = sessionID
        self.application = application
        self.sessionStartTime = time.time()
        return super(_session, self).new()

class _user(jimi.db._document):
    name = str()
    enabled = bool()
    username = str()
    passwordHash = str()
    passwordHashType = str()
    failedLoginCount = int()
    lastLoginAttempt = int()
    totpSecret = str()
    apiTokens = list()
    primaryGroup = str()

    _dbCollection = jimi.db.db["users"]

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
        if attr == "passwordHash" and not jimi.helpers.isBase64(value):
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

    def getAttribute(self,attr,sessionData=None):
        if attr == "passwordHash":
            return "*****"
        return super(_user, self).getAttribute(attr,sessionData=sessionData)

    def newAPIToken(self):
        apiSessionToken = secrets.token_hex(128)
        self.apiTokens.append(apiSessionToken)
        self.update(["apiTokens"])
        return apiSessionToken

class _group(jimi.db._document):
    name = str()
    enabled = bool()
    members = list()
    apiTokens = list()

    _dbCollection = jimi.db.db["groups"]

    # Override parent new to include name var, parent class new run after class var update
    def new(self,name):
        existingGroups = _group().query(query={ "name" : name })["results"]
        if len(existingGroups) == 0:
            self.name = name
            return super(_group, self).new() 
        else:
            return None

from system import install

if jimi.settings.getSetting("auth",None):
    authSettings = jimi.settings.getSetting("auth",None)
    # Loading public and private keys for session signing
    with open(str(Path(authSettings["rsa"]["cert"]))) as f:
        sessionPublicKey = f.read()
    with open(str(Path(authSettings["rsa"]["key"]))) as f:
        sessionPrivateKey = f.read()

    public_key = serialization.load_pem_public_key( sessionPublicKey.encode(), backend=default_backend() )
    private_key = serialization.load_pem_private_key( sessionPrivateKey.encode(), password=None, backend=default_backend() )

    requiredhType = "j1"

    jimi.cache.globalCache.newCache("sessions",cacheExpiry=authSettings["cacheSessionTimeout"])

def getSessionObject(sessionID,sessionData):
    session = _session().getAsClass(query={"sessionID" : sessionID})
    if len(session) == 1:
        return session[0]
    return None

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

def getPasswordFromENC(enc,customSecure=None):
    if enc[:6] == "ENC j1":
        cipher_rsa = PKCS1_OAEP.new(RSA.import_key(sessionPrivateKey))
        encSecureKey = base64.b64decode(enc[7:].split(" ")[2].encode())
        secureKey = cipher_rsa.decrypt(encSecureKey)
        if customSecure is None:
            key = install.getSecure().encode() + secureKey
        else:
            key = customSecure.encode() + secureKey
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

def getENCFromPassword(password,customSecure=None):
    if requiredhType == "j1":
        cipher_rsa = PKCS1_OAEP.new(RSA.import_key(sessionPublicKey))
        secureKey = get_random_bytes(16)
        encSecureKey = cipher_rsa.encrypt(secureKey)
        if customSecure is None:
            key = install.getSecure().encode() + secureKey
        else:
            key = customSecure.encode() + secureKey
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

def generateSharedSecret():
    return base64.b32encode(secrets.token_bytes(10)).decode("UTF-8")

def generateSession(dataDict):
    for application in dataDict:
        if dataDict[application]["api"]:
            dataDict[application]["expiry"] = time.time() + authSettings["apiSessionTimeout"]
        else:
            dataDict[application]["expiry"] = time.time() + authSettings["sessionTimeout"]
        if "CSRF" not in dataDict[application]:
            dataDict[application]["CSRF"] = secrets.token_urlsafe(16)
    return jwt.encode(dataDict, private_key, algorithm="RS256")

def generateSystemSession():
    data = {"jimi" : { "expiry" : time.time() + 10, "admin" : True, "system" : True, "_id" : 0, "user" : "system", "primaryGroup" : 0, "authenticated" : True, "api" : True }}
    return jwt.encode(data, private_key, algorithm="RS256")

def validateSession(sessionToken,application,useCache=True):
    try:
        dataDict = jwt.decode(sessionToken, public_key, algorithms=["RS256"])[application]
        if dataDict["authenticated"]:
            if dataDict["expiry"] < time.time():
                return None
            if dataDict["api"]:
                return { "sessionData" : dataDict, "sessionToken" : sessionToken }
            
            # Checking for active session skipping system sessions
            if useCache:
                session = jimi.cache.globalCache.get("sessions",dataDict["sessionID"],getSessionObject)
                if session.user != dataDict["user"]:
                    return None

            if dataDict["expiry"] < time.time() + ( authSettings["sessionTimeout"] / 2 ):
                return { "sessionData" : dataDict, "sessionToken" : sessionToken, "renew" : True }
            else:
                return { "sessionData" : dataDict, "sessionToken" : sessionToken }
    except:
        pass
    return None

def validateExternalUser(username,password,method,**kwargs):
    if method == "ldap":
        domains = jimi.settings.getSetting("ldap",None)["domains"]
        if "domain" in kwargs:
            domain = [x for x in domains if x["name"] == kwargs["domain"]][0]
            server = Server(domain["ip"], use_ssl=domain["ssl"], get_info=ALL)
            conn = Connection(server, "{}\{}".format(kwargs["domain"],username), password, authentication=NTLM)
            if conn.bind():
                # Generate new session
                if authSettings["singleUserSessions"]:
                    _session().api_delete(query={ "user" : username, "application" : kwargs["application"] })
                sessionID = secrets.token_hex(32)
                if _session().new(username,sessionID,kwargs["application"]).inserted_id:
                    jimi.audit._audit().add("auth","login",{ "action" : "success", "src_ip" : jimi.api.request.remote_addr, "username" : username, "sessionID" : sessionID, "api" : False, "application" : kwargs["application"] })
                    return generateSession({kwargs["application"] : { "_id" : kwargs["application"], "user" : username, "authenticated" : True, "sessionID" : sessionID, "api" : False}})
                else:
                    jimi.audit._audit().add("auth","session",{ "action" : "failure", "src_ip" : jimi.api.request.remote_addr, "username" : username, "sessionID" : sessionID, "api" : False, "application" : kwargs["application"] })

    jimi.audit._audit().add("auth","login",{ "action" : "failed", "src_ip" : jimi.api.request.remote_addr, "username" : username, "method" : method })
    return None

def validateUser(username,password,otp=None):
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
        validOTP = True
        if user.totpSecret:
            validOTP = onetimepass.valid_totp(otp, user.totpSecret)
        if passwordHash[1] == user.passwordHash and validOTP:
            # If user password hash does not meet the required standard update
            if user.passwordHashType != requiredhType:
                passwordHash = generatePasswordHash(password,username)
                user.passwordHashType = passwordHash[0]
                user.passwordHash = passwordHash[1]
                user.update(["passwordHashType","passwordHash"])
            user.failedLoginCount = 0
            user.update(["lastLoginAttempt","failedLoginCount"])
            # Generate new session
            if authSettings["singleUserSessions"]:
                _session().api_delete(query={ "user" : user.username, "application" : "jimi" })
            sessionID = secrets.token_hex(32)
            if _session().new(user.username,sessionID,"jimi").inserted_id:
                jimi.audit._audit().add("auth","login",{ "action" : "success", "src_ip" : jimi.api.request.remote_addr, "username" : user.username, "_id" : user._id, "accessIDs" : enumerateGroups(user), "primaryGroup" :user.primaryGroup, "admin" : isAdmin(user), "sessionID" : sessionID, "api" : False })
                return generateSession({"jimi" : { "_id" : user._id, "user" : user.username, "primaryGroup" : user.primaryGroup, "admin" : isAdmin(user), "accessIDs" : enumerateGroups(user), "authenticated" : True, "sessionID" : sessionID, "api" : False }})
            else:
                jimi.audit._audit().add("auth","session",{ "action" : "failure", "src_ip" : jimi.api.request.remote_addr, "username" : username, "_id" : user._id, "accessIDs" : enumerateGroups(user), "primaryGroup" :user.primaryGroup, "admin" : isAdmin(user), "sessionID" : sessionID, "api" : False, "application" : "jimi" })
        else:
            user.failedLoginCount+=1
            user.update(["lastLoginAttempt","failedLoginCount"])

    jimi.audit._audit().add("auth","login",{ "action" : "failed", "src_ip" : jimi.api.request.remote_addr, "username" : username, "method" : "local" })
    return None

# Needs to be converted into authorization roles e.g. admin
def requireAuthentication(func):
    def decorated_function(*args, **kwargs):
        if "jimiAuth" in jimi.api.request.cookies:
            validSession = validateSession(jimi.api.request.cookies["jimiAuth"])
            if not validSession:
                return {}, 403
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

def adminEndpoint(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            if authSettings["enabled"]:
                if jimi.api.g.sessionData["admin"]:
                    return f(*args, **kwargs)
            else:
                return f(*args, **kwargs)
        except Exception as e:
            jimi.logging.debug("Error during webservice function. Exception={0}".format(e),-1)
        return {}, 403
    return wrap

def systemEndpoint(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            if authSettings["enabled"]:
                if jimi.api.g.sessionData["system"]:
                    return f(*args, **kwargs)
            else:
                return f(*args, **kwargs)
        except Exception as e:
            jimi.logging.debug("Error during webservice function. Exception={0}".format(e),-1)
        return {}, 403
    return wrap

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        # Ensures that all requests require basic level of authentication ( authorisation handled by decorators )
        @jimi.api.webServer.before_request
        def api_alwaysAuthBefore():
            jimi.api.g.sessionData = {}
            jimi.api.g.sessionToken = ""
            jimi.api.g.type = ""
            #api.g = { "sessionData" : {}, "sessionToken": "", "type" : "" }
            if authSettings["enabled"]:
                noAuthEndPoints = ["static","staticFile","loginPage","api_validateUser","api_validateAPIKey"]
                if jimi.api.request.endpoint != None and jimi.api.request.endpoint not in noAuthEndPoints and "__PUBLIC__" not in jimi.api.request.endpoint:
                    validSession = None
                    if "jimiAuth" in jimi.api.request.cookies:
                        validSession = validateSession(jimi.api.request.cookies["jimiAuth"],"jimi")
                        if not validSession:
                                return jimi.api.redirect("/login?return={0}".format(urllib.parse.quote(jimi.api.request.full_path)), code=302)
                        jimi.api.g.type = "cookie"
                        # Confirm CSRF
                        if jimi.api.request.method in ["POST","PUT","DELETE"]:
                            try:
                                try:
                                    data = json.loads(jimi.api.request.data)
                                    if "CSRF" not in data:
                                        raise KeyError
                                except:
                                    try:
                                        data = json.loads(list(jimi.api.request.form.to_dict().keys())[0])
                                        if "CSRF" not in data:
                                            raise KeyError
                                    except:
                                        data = jimi.api.request.form
                                if validSession["sessionData"]["CSRF"] != data["CSRF"]:
                                    return jimi.api.redirect("/login?return={0}".format(urllib.parse.quote(jimi.api.request.full_path)), code=302)
                            except:
                                return jimi.api.redirect("/login?return={0}".format(urllib.parse.quote(jimi.api.request.full_path)), code=302)
                    elif "x-api-token" in jimi.api.request.headers:
                        validSession = validateSession(jimi.api.request.headers.get("x-api-token"),"jimi")
                        if not validSession:
                            return {}, 403
                        #if validSession["sessionData"]["api"] != True:
                        #    return {}, 403
                        jimi.api.g.type = "x-api-token"
                    else: 
                        return jimi.api.redirect("/login?return={0}".format(urllib.parse.quote(jimi.api.request.full_path)), code=302)
                    # Data that is returned to the Flask request handler function
                    jimi.api.g.sessionData = validSession["sessionData"]
                    jimi.api.g.sessionToken = validSession["sessionToken"]
                    if "renew" in validSession:
                        jimi.api.g.renew = validSession["renew"]
                else:
                    jimi.api.g.type = "bypass"
            else:
                jimi.api.g.sessionData = { "_id" : "0", "user" : "noAuth", "CSRF" : "" }
                jimi.api.g.sessionToken = ""
                jimi.api.g.type = "noAuth"
            
        # Ensures that all requests return an up to date sessionToken to prevent session timeout for valid sessions
        @jimi.api.webServer.after_request
        def api_alwaysAuthAfter(response):
            if authSettings["enabled"]:
                if jimi.api.g.type != "bypass":
                    if jimi.api.g.type == "cookie":
                        if "renew" in jimi.api.g:
                            response.set_cookie("jimiAuth", value=generateSession({"jimi":jimi.api.g.sessionData}), max_age=authSettings["sessionTimeout"], httponly=True) # Need to add secure=True before production, httponly=False cant be used due to auth polling
            # Cache Weakness
            if jimi.api.request.endpoint and jimi.api.request.endpoint != "static" and "__STATIC__" not in jimi.api.request.endpoint:
                response.headers['Cache-Control'] = 'no-cache, no-store'
                response.headers['Pragma'] = 'no-cache'
            # Permit CORS when web and web API ( Flask ) are seperated
            response.headers['Access-Control-Allow-Origin'] = "http://localhost:3000"
            response.headers['Access-Control-Allow-Methods'] = "GET, POST, PUT, DELETE"
            # ClickJacking
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            return response

        if jimi.api.webServer.name == "jimi_web":
            from flask import Flask, request, render_template

            @jimi.api.webServer.route("/myAccount/")
            def myAccountPage():
                return render_template("myAccount.html",CSRF=jimi.api.g.sessionData["CSRF"])

            # Checks that username and password are a match
            @jimi.api.webServer.route(jimi.api.base+"auth/", methods=["POST"])
            def api_validateUser():
                if authSettings["enabled"]:
                    data = json.loads(jimi.api.request.data)
                    #check if OTP has been passed
                    #if invalid user or user requires OTP, return 200 but request OTP
                    if "otp" not in data:
                        user = _user().getAsClass(query={ "username" : data["username"] })
                        if len(user) == 1:
                            user = user[0]
                            if user.totpSecret != "":
                                return {}, 403
                            else:
                                userSession = validateUser(data["username"],data["password"])
                        else:
                            return {}, 403
                    else:
                        userSession = validateUser(data["username"],data["password"],data["otp"])
                    if userSession:
                        sessionData = validateSession(userSession,"jimi")["sessionData"]
                        redirect = jimi.api.request.args.get("return")
                        if redirect:
                            if "." in redirect or ".." in redirect:
                                redirect = "/conducts/"
                            if not redirect.startswith("/"):
                                redirect = "/" + redirect
                        else:
                            redirect = "/conducts/"
                        # Default redirect forced update to /conducts/
                        if redirect == "/?":
                            redirect = "/conducts/"
                        response = jimi.api.make_response({ "CSRF" : sessionData["CSRF"], "redirect" : redirect },200)
                        response.set_cookie("jimiAuth", value=userSession, max_age=authSettings["sessionTimeout"], httponly=True, secure=True)
                        return response, 200
                else:
                    return { "CSRF" : "" }, 200
                return {}, 403

            # Called by API systems to request an x-api-token string from x-api-key provided
            @jimi.api.webServer.route(jimi.api.base+"auth/", methods=["GET"])
            def api_validateAPIKey():
                if "x-api-key" in jimi.api.request.headers:
                    user = _user().getAsClass(query={ "apiTokens" : { "$in" : [ jimi.api.request.headers.get("x-api-key") ] } } )
                    if len(user) == 1:
                        user = user[0]  
                        # Generate new session
                        sessionID = secrets.token_hex(32)
                        if _session().new(user.username,sessionID,"jimi").inserted_id:
                            jimi.audit._audit().add("auth","login",{ "action" : "success", "src_ip" : jimi.api.request.remote_addr, "username" : user.username, "_id" : user._id, "accessIDs" : enumerateGroups(user), "primaryGroup" : user.primaryGroup, "admin" : isAdmin(user), "sessionID" : sessionID, "api" : True, "application" : "jimi" })
                            return { "x-api-token" : generateSession({"jimi": { "_id" : user._id, "user" : user.username, "primaryGroup" : user.primaryGroup, "admin" : isAdmin(user), "accessIDs" : enumerateGroups(user), "authenticated" : True, "sessionID" : sessionID, "api" : True }}).decode()}, 200
                        else:
                            jimi.audit._audit().add("auth","session",{ "action" : "failure", "src_ip" : jimi.api.request.remote_addr, "username" : user.username, "_id" : user._id, "accessIDs" : enumerateGroups(user), "primaryGroup" :user.primaryGroup, "admin" : isAdmin(user), "sessionID" : sessionID, "api" : True, "application" : "jimi" })
                            return {}, 403
                return {}, 404

            @jimi.api.webServer.route(jimi.api.base+"auth/poll/", methods=["GET"])
            def api_sessionPolling():
                result = { "CSRF" : "" }
                if authSettings["enabled"]:
                    result = { "CSRF" : jimi.api.g.sessionData["CSRF"] }
                return result, 200

            @jimi.api.webServer.route("/logout/", methods=["GET"])
            def logout():
                # Deleting active session
                session = jimi.cache.globalCache.delete("sessions",jimi.api.g.sessionData["sessionID"])
                if authSettings["singleUserSessions"]:
                    _session().api_delete(query={ "user" : jimi.api.g.sessionData["user"] })
                else:
                    session = _session().getAsClass(query={"sessionID" : jimi.api.g.sessionData["sessionID"]})
                    if len(session) == 1:
                        session = session[0]
                        session.delete()

                jimi.audit._audit().add("auth","logout",{ "action" : "success", "_id" : jimi.api.g.sessionData["_id"] })
                return jimi.api.make_response(redirect("/login/"))

            @jimi.api.webServer.route(jimi.api.base+"auth/logout/", methods=["GET"])
            def api_logout():
                response = jimi.api.make_response()

                # Deleting active session
                session = jimi.cache.globalCache.delete("sessions",jimi.api.g.sessionData["sessionID"])
                if authSettings["singleUserSessions"]:
                    _session().api_delete(query={ "user" : jimi.api.g.sessionData["user"] })
                else:
                    session = _session().getAsClass(query={"sessionID" : jimi.api.g.sessionData["sessionID"]})
                    if len(session) == 1:
                        session = session[0]
                        session.delete()

                jimi.audit._audit().add("auth","logout",{ "action" : "success", "_id" : jimi.api.g.sessionData["_id"] })
                response.set_cookie("jimiAuth", value="")
                return response, 200

            # Checks that username and password are a match
            @jimi.api.webServer.route(jimi.api.base+"auth/myAccount/", methods=["POST"])
            def api_updateMyAccount():
                if authSettings["enabled"]:
                    user = _user().getAsClass(id=jimi.api.g.sessionData["_id"])
                    if len(user) == 1:
                        user = user[0]
                        data = json.loads(jimi.api.request.data)
                        if "password" in data:
                            if generatePasswordHash(data["password"],user.username)[1] == user.passwordHash:
                                if not user.setAttribute("passwordHash",data["password1"],sessionData=jimi.api.g.sessionData):
                                    return { "msg" : "New password does not meet complexity requirements" }, 400
                            else:
                                return { "msg" : "Current password does not match" }, 400
                        user.update(["passwordHash","apiTokens"])
                        return {}, 200
                else:
                    return {}, 200
                return {}, 403

            # Called by API systems to request an x-api-token string from x-api-key provided
            @jimi.api.webServer.route(jimi.api.base+"auth/myAccount/", methods=["GET"])
            def api_getMyAccount():
                if authSettings["enabled"]:
                    user = _user().getAsClass(id=jimi.api.g.sessionData["_id"])
                    if len(user) == 1:
                        user = user[0]
                        userProps = {}
                        userProps["username"] = user.getAttribute("username",sessionData=jimi.api.g.sessionData)
                        userProps["name"] = user.getAttribute("name",sessionData=jimi.api.g.sessionData)
                        return userProps, 200
                else:
                    userProps = {}
                    userProps["username"] = "username"
                    userProps["name"] = "name"
                    return userProps, 200
                return { }, 404

            @jimi.api.webServer.route(jimi.api.base+"auth/regenerateOTP/", methods=["GET"])
            def api_regenerateOTP():
                user = _user().getAsClass(id=jimi.api.g.sessionData["_id"])
                if len(user) == 1:
                    user = user[0]
                    user.setAttribute("totpSecret",generateSharedSecret(),sessionData=jimi.api.g.sessionData)
                    user.update(["totpSecret"])
                    return { }, 200
                return { }, 404

            @jimi.api.webServer.route(jimi.api.base+"auth/viewOTP/", methods=["GET"])
            def api_viewOTP():
                user = _user().getAsClass(id=jimi.api.g.sessionData["_id"])
                if len(user) == 1:
                    user = user[0]
                    totpSecret = user.getAttribute("totpSecret",sessionData=jimi.api.g.sessionData)
                    if totpSecret != "":
                        return "otpauth://totp/JIMI:{}?secret={}&issuer=JIMI".format(user.username,totpSecret), 200
                return { }, 404
