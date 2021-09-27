import jimi

class _organisation(jimi.db._document):
    name = str()
    
    _dbCollection = jimi.db.db["organisations"]

    def new(self,name):
        self.name = name
        self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] } 
        return super(_organisation, self).new()

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_web":
            from flask import Flask, request, render_template

            @jimi.api.webServer.route("/admin/organisation/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def organisationAdminPage():
                organisation = jimi.organisation._organisation().query()["results"]
                loginTypes = jimi.settings.getSettingValue(None,jimi.api.g.sessionData,"auth","types")
                passwordPolicy = jimi.settings.getSettingValue(None,jimi.api.g.sessionData,"auth","policy")
                availableTypes = [{"name":"local","enabled":False},{"name":"ldap","enabled":False},{"name":"oauth","enabled":False}]
                for loginType in availableTypes:
                    if loginType["name"] in loginTypes:
                        loginType["enabled"] = True
                        loginTypeSettings = jimi.settings.getSetting(loginType["name"],None)
                        if loginTypeSettings is not None:
                            loginType["settings"] = loginTypeSettings	
                return render_template("organisation.html",CSRF=jimi.api.g.sessionData["CSRF"],organisation=organisation,loginTypes=availableTypes,passwordPolicy=passwordPolicy)
         
            @jimi.api.webServer.route("/admin/organisation/", methods=["POST"])
            @jimi.auth.adminEndpoint
            def updateOrganisation():
                try:
                    #Updating org details
                    userData = request.json
                    organisation = _organisation().getAsClass(query={})
                    if len(organisation) > 0:
                        organisation = organisation[0]
                        organisation.name = userData["name"]
                        organisation.update(["name"])
                    else:
                        _organisation().new(userData["name"])

                    authSettings = jimi.settings._settings().getAsClass(query={"name" : "auth"})[0]

                    #Updating auth types allowed
                    if len(userData["authTypes"]) > 0:
                        authSettings.values["types"] = userData["authTypes"]
                    else:
                        response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Please select at least one authentication type!" },403)
                        return response

                    #Updating password policy
                    authSettings.values["policy"] = {"minLength":int(userData["length"]),"minLower":int(userData["lower"]),"minNumbers":int(userData["numbers"]),"minSpecial":int(userData["special"]),"minUpper":int(userData["upper"])}

                    authSettings.update(["values"])

                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Organisation updated successfully" },200)
                except:
                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Could not update the organisation" },403)
                return response

            @jimi.api.webServer.route("/admin/organisation/ldapConnection/", methods=["PUT"])
            @jimi.auth.adminEndpoint
            def updateLdapConnection():
                try:
                    #Updating ldap connection details -- ISSUE doesn't handle cache
                    userData = request.json
                    newDomainList = []
                    ldapSettings = jimi.settings._settings().getAsClass(query={"name" : "ldap"})[0]
                    for domain in ldapSettings.values["domains"]:
                        if domain["name"] == userData["originalName"]:
                            domain = {"name":userData["name"],"ip":userData["ip"],"ssl":userData["ssl"]}
                        newDomainList.append(domain)
                    ldapSettings.values["domains"] = newDomainList
                    ldapSettings.update(["values"])
                    #Refreshing cache for settings
                    jimi.cache._cache().clearCache("settingsCache")
                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "LDAP connection updated successfully" },200)
                except Exception:
                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Could not update the LDAP connection" },403)
                return response

            @jimi.api.webServer.route("/admin/organisation/ldapConnection/", methods=["POST"])
            @jimi.auth.adminEndpoint
            def newLdapConnection():
                try:
                    userData = request.json                 
                    ldapSettings = jimi.settings._settings().getAsClass(query={"name" : "ldap"})[0]
                    for domain in ldapSettings.values["domains"]:
                        if domain["name"] == userData["name"]:
                            return jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "An LDAP connection with that name already exists!" },403)
                    ldapSettings.values["domains"].append({"name":userData["name"],"ip":userData["ip"],"ssl":userData["ssl"]})
                    ldapSettings.update(["values"])
                    #Refreshing cache for settings
                    jimi.cache._cache().clearCache("settingsCache")
                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "LDAP connection created successfully" },200)
                except Exception:
                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Could not update the LDAP connection" },403)
                return response

            @jimi.api.webServer.route("/admin/organisation/ldapConnection/", methods=["DELETE"])
            @jimi.auth.adminEndpoint
            def deleteLdapConnection():
                try:
                    userData = request.json 
                    newDomainList = []                
                    ldapSettings = jimi.settings._settings().getAsClass(query={"name" : "ldap"})[0]
                    for domain in ldapSettings.values["domains"]:
                        if domain["name"] != userData["name"]:
                            newDomainList.append(domain)
                    ldapSettings.values["domains"] = newDomainList
                    ldapSettings.update(["values"])
                    #Refreshing cache for settings
                    jimi.cache._cache().clearCache("settingsCache")
                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "LDAP connection created successfully" },200)
                except Exception:
                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Could not update the LDAP connection" },403)
                return response
