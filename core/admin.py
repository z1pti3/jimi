import logging
import requests
import jimi

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"admin/clearCache/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def api_clearCache():
                jimi.cache.globalCache.clearCache("ALL")
                results = [{ "system" : jimi.cluster.getSystemId(), "status_code" : 200 }]
                apiToken = jimi.auth.generateSystemSession()
                headers = { "X-api-token" : apiToken }
                for systemIndex in jimi.cluster.systemIndexes:
                    url = systemIndex["apiAddress"]
                    apiEndpoint = "admin/clearCache/"
                    try:
                        response = requests.get("{0}{1}{2}".format(url,jimi.api.base,apiEndpoint),headers=headers, timeout=10)
                        if response.status_code == 200:
                            results.append({ "system" : jimi.cluster.getSystemId(), "index" : systemIndex["systemIndex"], "status_code" : response.status_code })
                    except:
                        logging.warning("Unable to access {0}{1}{2}".format(url,jimi.api.base,apiEndpoint))
                return { "results" : results }, 200

            @jimi.api.webServer.route(jimi.api.base+"admin/clearStartChecks/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def api_clearStartChecks():
                from system import install
                install.resetTriggers()
                return { "result" : True }, 200

        if jimi.api.webServer.name == "jimi_worker":
            @jimi.api.webServer.route(jimi.api.base+"admin/clearCache/", methods=["GET"])
            @jimi.auth.systemEndpoint
            def api_clearCache():
                jimi.cache.globalCache.clearCache("ALL")
                return { "result" : True }, 200

        if jimi.api.webServer.name == "jimi_web":
            from flask import Flask, request, render_template

            # --- User editor --- #            
            @jimi.api.webServer.route("/admin/users/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def listUsers():
                #Get groups to match against
                groups = {}
                groupsList = []
                foundGroups = jimi.auth._group().getAsClass(sessionData=jimi.api.g.sessionData,query={ })
                for group in foundGroups:
                    groups[group._id] = group
                    groupsList.append(group)
                users = []
                foundUsers =  jimi.auth._user().getAsClass(sessionData=jimi.api.g.sessionData,query={ })
                for user in foundUsers:
                    if user.primaryGroup in groups:
                        user.primaryGroupName = groups[user.primaryGroup].name
                    users.append(user)        
                return render_template("users.html",users=users,groups=groupsList,CSRF=jimi.api.g.sessionData["CSRF"])

            @jimi.api.webServer.route("/admin/users/edit/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def editUser():
                #Get group data for later
                groups = []
                foundGroups = jimi.auth._group().getAsClass(sessionData=jimi.api.g.sessionData,query={ })
                for group in foundGroups:
                    groups.append(group)

                #Get user details based on ID
                foundUser = jimi.auth._user().getAsClass(sessionData=jimi.api.g.sessionData,query={"_id":jimi.db.ObjectId(request.args.get("id"))})
                if foundUser:
                    foundUser = foundUser[0]
                    #Get friendly names for groups
                    for group in groups:
                        if group._id == foundUser.primaryGroup:
                            foundUser.primaryGroupName = group.name
                    return render_template("userDetailed.html",user=foundUser,groups=groups,CSRF=jimi.api.g.sessionData["CSRF"])
                return 404

            @jimi.api.webServer.route("/admin/users/edit/", methods=["PUT"])
            @jimi.auth.adminEndpoint
            def updateUser():
                response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Could not update the user" },403)
                userData = request.json
                if userData["enabled"] == "No":
                    userData["enabled"] = False
                else:
                    userData["enabled"] = True
                #Get user details based on username
                foundUser = jimi.auth._user().getAsClass(sessionData=jimi.api.g.sessionData,query={"username":userData["username"]})
                if foundUser:
                    foundUser = foundUser[0]
                    updateList = []
                    for item in userData:
                        if item != "CSRF" and userData[item] != foundUser.getAttribute(item,sessionData=jimi.api.g.sessionData):
                            foundUser.setAttribute(item,userData[item],sessionData=jimi.api.g.sessionData)
                            updateList.append(item)
                    if any(updateList):
                        foundUser.update(updateList,sessionData=jimi.api.g.sessionData)
                        response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "User updated successfully" },201)
                    else:
                        response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Nothing to update" },200)
                return response

            @jimi.api.webServer.route("/admin/users/create/", methods=["POST"])
            @jimi.auth.adminEndpoint
            def createUser():
                response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Please provide a username" },403)
                userData = request.json
                #Check user ID is new and valid
                if userData["username"]:
                    foundUser = jimi.auth._user().getAsClass(sessionData=jimi.api.g.sessionData,query={"username":userData["username"]})
                    if foundUser:
                        return jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Username already in use" },403)
                    #Check password provided
                    if userData["password"]:
                        if not jimi.auth.meetsPasswordPolicy(userData["password"]):
                            return jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Password does not meet minimum requirements" },403)
                        #If no name provided, use the username
                        if len(userData["name"]) == 0:
                            userData["name"] = userData["username"] 
                        #Create a new user
                        if jimi.auth._user().new(userData["name"],userData["username"],userData["password"]):
                            user = jimi.auth._user().getAsClass(sessionData=jimi.api.g.sessionData,query={"username":userData["username"]})[0]
                            #Enable the user?
                            if userData["active"] == "No":
                                user.setAttribute("enabled",False,sessionData=jimi.api.g.sessionData)
                            #Define the users primary group
                            user.setAttribute("primaryGroup",userData["group"],sessionData=jimi.api.g.sessionData)
                            group = jimi.auth._group().getAsClass(sessionData=jimi.api.g.sessionData,id=userData["group"])
                            if len(group) == 1:
                                group = group[0]
                                group.members.append(user._id)
                                group.update(["members"])
                            else:
                                return jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Could not find group!" },403)
                            #Set email if it exists
                            if userData["email"]:
                                user.setAttribute("email",userData["email"],sessionData=jimi.api.g.sessionData)
                            #Set user login type
                            user.setAttribute("loginType",userData["loginType"],sessionData=jimi.api.g.sessionData)
                            user.update(["email","primaryGroup","loginType"],sessionData=jimi.api.g.sessionData)
                            #Check for sandbox creation
                            if userData["sandbox"] == "Yes":
                                #Create a sandbox conduct using the user's name
                                sandboxConduct = jimi.conduct._conduct().new(f"{userData['name']} - Sandbox")
                                sandboxConduct = jimi.conduct._conduct().getAsClass(sessionData=jimi.api.g.sessionData,query={"name":f"{userData['name']} - Sandbox"})[0]
                                sandboxConduct.acl = {"ids":[{"accessID":group._id,"delete":True,"read":True,"write":True}]}
                                sandboxConduct.comment = f"Sandbox for {userData['name']} (auto-generated)"
                                sandboxConduct.update(["acl","comment"])
                            return jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "User created successfully" },201)
                    response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Please provide a password" },403)
                return response

            @jimi.api.webServer.route("/admin/users/edit/", methods=["DELETE"])
            @jimi.auth.adminEndpoint
            def deleteUser():
                response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Could not delete user" },403)
                #Get user details based on username
                foundUser = jimi.auth._user().getAsClass(sessionData=jimi.api.g.sessionData,id=request.args.get("id"))
                if foundUser:
                    foundUser = foundUser[0]
                    #Cannot delete the root user
                    if foundUser.username != "root":
                        if jimi.auth._user().api_delete(id=foundUser._id):
                            #Remove group membership
                            group = jimi.auth._group().getAsClass(sessionData=jimi.api.g.sessionData,id=foundUser.primaryGroup)
                            if len(group) == 1:
                                group = group[0]
                                group.members = [x for x in group.members if x != foundUser._id]
                                group.update(["members"])
                            response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "User deleted successfully" },201)
                    else:
                        response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Cannot delete root user" },403)
                return response

            # --- Group editor --- #   
            @jimi.api.webServer.route("/admin/groups/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def listGroups():
                #Get groups
                groups = []
                foundGroups = jimi.auth._group().getAsClass(sessionData=jimi.api.g.sessionData,query={ })
                for group in foundGroups:
                    group.userCount = len(group.members)
                    groups.append(group)
                
                return render_template("groups.html",groups=groups,CSRF=jimi.api.g.sessionData["CSRF"])

            @jimi.api.webServer.route("/admin/groups/edit/", methods=["GET"])
            @jimi.auth.adminEndpoint
            def editGroups():
                #Get group details based on ID
                foundGroup = jimi.auth._group().getAsClass(sessionData=jimi.api.g.sessionData,query={"_id":jimi.db.ObjectId(request.args.get("id"))})
                if foundGroup:
                    foundGroup = foundGroup[0]

                    #Get ACL info about each conduct
                    conductList = []
                    conducts = jimi.conduct._conduct().getAsClass(sessionData=jimi.api.g.sessionData,query={})
                    for conduct in conducts:
                        if "ids" in conduct.acl:
                            matches = [item for item in conduct.acl["ids"] if item["accessID"] == foundGroup._id]
                            if any(matches):
                                conductList.append({"id":conduct._id, "name":conduct.name, "acl":matches[0], "enabled":True})
                            else:
                                conductList.append({"id":conduct._id, "name":conduct.name, "acl":{"accessID":foundGroup._id,"read":False,"write":False,"delete":False}, "enabled":False})
                        else:
                            conductList.append({"id":conduct._id, "name":conduct.name, "acl":{"accessID":foundGroup._id,"read":False,"write":False,"delete":False}, "enabled":False})

                    #Get ACL info about each model
                    modelList = []
                    models = jimi.model.getModelExtra("model")[0]["results"]
                    for model in models:
                        if "ids" in model["acl"]:
                            matches = [item for item in model["acl"]["ids"] if item["accessID"] == foundGroup._id]
                            if any(matches):
                                modelList.append({"id":model["_id"], "name":model["name"], "acl":matches[0], "enabled":True})
                            else:
                                modelList.append({"id":model["_id"], "name":model["name"], "acl":{"accessID":foundGroup._id,"read":False,"write":False,"delete":False}, "enabled":False})
                        else:
                            modelList.append({"id":model["_id"], "name":model["name"], "acl":{"accessID":foundGroup._id,"read":False,"write":False,"delete":False}, "enabled":False})

                    return render_template("groupDetailed.html",group=foundGroup,conductList=conductList,modelList=modelList,CSRF=jimi.api.g.sessionData["CSRF"])
                return 404

            @jimi.api.webServer.route("/admin/groups/create/", methods=["POST"])
            @jimi.auth.adminEndpoint
            def createGroup():
                response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Please provide a name" },403)
                groupData = request.json
                #Check group name is new and valid
                if groupData["name"]:
                    foundGroup = jimi.auth._group().getAsClass(sessionData=jimi.api.g.sessionData,query={"name":groupData["name"]})
                    if foundGroup:
                        return jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Group name already in use" },403)
                    #Create a new group
                    if jimi.auth._group().new(groupData["name"]):
                        group = jimi.auth._group().getAsClass(sessionData=jimi.api.g.sessionData,query={"name":groupData["name"]})[0]
                        #Enable the group?
                        if groupData["active"] == "No":
                            group.setAttribute("enabled",False,sessionData=jimi.api.g.sessionData)
                        #Set description
                        group.setAttribute("description",groupData["description"],sessionData=jimi.api.g.sessionData)
                        group.update(["description"],sessionData=jimi.api.g.sessionData)
                        #Check for sandbox creation
                        if groupData["sandbox"] == "Yes":
                            #Create a sandbox conduct using the group's name
                            sandboxConduct = jimi.conduct._conduct().new(f"{groupData['name']} - Sandbox")
                            #TODO: Set group as owner of sandbox
                        return jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Group created successfully" },201)
                return response

            @jimi.api.webServer.route("/admin/groups/edit/", methods=["PUT"])
            @jimi.auth.adminEndpoint
            def updateGroup():
                response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Could not update the group" },403)
                groupData = request.json
                if groupData["enabled"] == "No":
                    groupData["enabled"] = False
                else:
                    groupData["enabled"] = True
                #Get group details based on group name
                foundGroup = jimi.auth._group().getAsClass(sessionData=jimi.api.g.sessionData,query={"name":groupData["name"]})
                if foundGroup:
                    foundGroup = foundGroup[0]
                    updateList = []
                    for item in groupData:
                        if item != "CSRF" and groupData[item] != foundGroup.getAttribute(item,sessionData=jimi.api.g.sessionData):
                            foundGroup.setAttribute(item,groupData[item],sessionData=jimi.api.g.sessionData)
                            updateList.append(item)
                    if any(updateList):
                        foundGroup.update(updateList,sessionData=jimi.api.g.sessionData)
                        response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Group updated successfully" },201)
                    else:
                        response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Nothing to update" },200)
                return response

            @jimi.api.webServer.route("/admin/groups/edit/", methods=["DELETE"])
            @jimi.auth.adminEndpoint
            def deleteGroup():
                response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Could not delete group" },403)
                #Get user details based on username
                foundGroup = jimi.auth._group().getAsClass(sessionData=jimi.api.g.sessionData,query={"_id":jimi.db.ObjectId(request.args.get("id"))})
                if foundGroup:
                    foundGroup = foundGroup[0]
                    #Cannot delete the root user
                    if foundGroup.name != "admin":
                        if jimi.auth._group().api_delete(query={"_id":jimi.db.ObjectId(request.args.get("id"))}):
                            response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Group deleted successfully" },201)
                    else:
                        response = jimi.api.make_response({ "CSRF" : jimi.api.g.sessionData["CSRF"], "message" : "Cannot delete admin group" },403)
                return response