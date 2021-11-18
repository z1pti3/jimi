import sys
import os
import json

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--reset_root',action='store_true', help='Reset root password')
parser.add_argument('--update_conduct_acl', action='store_true', help='Update conduct ACLs')
parser.add_argument('--conduct', help='Conduct ID')
parser.add_argument('--acl', help='ACL ID')
parser.add_argument('--read', action='store_true', help='Set read to true')
parser.add_argument('--write', action='store_true', help='Set write to true')
parser.add_argument('--delete', action='store_true', help='Set delete to true')
args = parser.parse_args()

if args.reset_root:
    from core import auth
    from system import install
    rootUser = auth._user().getAsClass(query={ "username" : "root" })
    if len(rootUser) == 1:
        rootUser = rootUser[0]
        rootPass = install.randomString(30)
        rootUser.setAttribute("passwordHash",rootPass)
        rootUser.update(["passwordHash"])
        print("Root password reset! Password: {0}".format(rootPass))

elif args.update_conduct_acl:
    conductID = args.conduct
    aclString = {"accessID":args.acl,"read":False,"write":False,"delete":False}
    if args.read:
        aclString["read"] = True
    if args.write:
        aclString["write"] = True
    if args.delete:
        aclString["delete"] = True
    import jimi
    counter = 0 
    conductObj = jimi.conduct._conduct().getAsClass(id=conductID)[0]
    webObjects = jimi.webui._modelUI().getAsClass(query={"conductID" : conductID})
    #Add ACL to conduct
    tempACL = []
    added = False
    for acl in conductObj.acl["ids"]:
        if acl["accessID"] == aclString["accessID"]:
            tempACL.append(aclString)
            added = True
        else:
            tempACL.append(acl)
    if added == False:
        tempACL.append(aclString)
    conductObj.acl["ids"] = tempACL
    conductObj.update(["acl"])
    for jimiObject in conductObj.flow:
        counter += 1
        if "triggerID" in jimiObject:
            #Update trigger object ACL
            triggerObject = jimi.trigger._trigger().getAsClass(id=jimiObject["triggerID"])[0]
            tempACL = []
            added = False
            for acl in triggerObject.acl["ids"]:
                if acl["accessID"] == aclString["accessID"]:
                    tempACL.append(aclString)
                    added = True
                else:
                    tempACL.append(acl)
            if added == False:
                tempACL.append(aclString)
            triggerObject.acl["ids"] = tempACL
            triggerObject.update(["acl"])
        elif "actionID" in jimiObject:
            #Update action object ACL
            actionObject = jimi.action._action().getAsClass(id=jimiObject["actionID"])[0]
            tempACL = []
            added = False
            for acl in actionObject.acl["ids"]:
                if acl["accessID"] == aclString["accessID"]:
                    tempACL.append(aclString)
                    added = True
                else:
                    tempACL.append(acl)
            if added == False:
                tempACL.append(aclString)
            actionObject.acl["ids"] = tempACL
            actionObject.update(["acl"])

        #Update UI ACL
        webObject = [x for x in webObjects if jimiObject["flowID"] == x.flowID][0]
        tempACL = []
        added = False
        for acl in webObject.acl["ids"]:
            if acl["accessID"] == aclString["accessID"]:
                tempACL.append(aclString)
                added = True
            else:
                tempACL.append(acl)
        if added == False:
            tempACL.append(aclString)
        webObject.acl["ids"] = tempACL
        webObject.update(["acl"])
        print(f"Updated {counter}/{len(conductObj.flow)} objects with new ACL",end="\r")

    print(f"Updated {counter}/{len(conductObj.flow)} objects with new ACL")

else:   
    from screens import mainScreen
    screen = mainScreen.mainScreen()
