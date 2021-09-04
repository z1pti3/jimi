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
         
            @jimi.api.webServer.route("/admin/organisation/", methods=["POST"])
            @jimi.auth.adminEndpoint
            def updateOrganisation():
                try:
                    userData = request.json
                    organisation = _organisation().getAsClass(query={})
                    if len(organisation) > 0:
                        organisation = organisation[0]
                        organisation.name = userData["name"]
                        organisation.update(["name"])
                    else:
                        _organisation().new(userData["name"])
                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Organisation updated successfully" },200)
                except:
                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Could not update the organisation" },403)
                return response