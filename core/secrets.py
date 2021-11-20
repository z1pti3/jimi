import secrets

import jimi

class _secret(jimi.db._document):
    name = str()
    secretValue = str()
    token = str()
    comment = str()

    _dbCollection = jimi.db.db["secrets"]

    def new(self,acl,name,secretValue,comment=""):
        self.acl = acl
        self.name = name
        self.secretValue = secretValue
        self.comment = comment
        return super(_secret, self).new()

    def setAttribute(self,attr,value,sessionData=None):
        if attr == "secretValue" and not value.startswith("ENC "):
            if jimi.db.fieldACLAccess(sessionData,self.acl,attr,accessType="write"):
                if not self.token:
                    self.token = secrets.token_hex(128)
                    self.update(["token"])
                self.secretValue = "ENC {0}".format(jimi.auth.getENCFromPassword(value))
                return True
            return False
        return super(_secret, self).setAttribute(attr,value,sessionData=sessionData)

# API
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_web":
            from flask import Flask, request, render_template, redirect

            @jimi.api.webServer.route("/secrets/", methods=["GET"])
            def secretPage():
                secretItems = _secret().query(sessionData=jimi.api.g.sessionData,query={ })["results"]
                return render_template("secrets.html",secrets=secretItems,CSRF=jimi.api.g.sessionData["CSRF"])