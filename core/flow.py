import re
import json
import copy
import time
import uuid
import traceback

import jimi

from system import variable, logic

cpuSaver = jimi.settings.config["cpuSaver"]

regexFunction = re.compile("^([a-zA-Z0-9]*)\(.*\)")
regexCommor = re.compile(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")

def flowLogicEval(data,logicVar):
    if type(logicVar) is bool:
        try:
            if "action" in data:
                if logicVar == data["action"]["result"]:
                    return True
            #No action so must be a trigger, thus it's always true!
            else:
                return True
        except:
            pass
    elif type(logicVar) is int:
        try:
            if logicVar == data["action"]["rc"]:
                return True
        except:
            pass
    elif type(logicVar) is str:
        if logicVar.startswith("if"):
            if logic.ifEval(logicVar, { "data" : data }):
                return True
    return False

def getObjectFromCode(sessionData,codeFunction):
    functionName = codeFunction.split("{")[0]
    args = json.loads(codeFunction.strip()[(len(functionName)):])
    classObject = jimi.model._model().getAsClass(sessionData=sessionData,query={ "name" : functionName })[0].classObject()()
    members = [attr for attr in dir(classObject) if not callable(getattr(classObject, attr)) and not "__" in attr and attr ]
    for key, value in args.items():
        for member in members:
            if key == member:
                if type(getattr(classObject,member)) == type(value):
                    setattr(classObject,member,value)
                    break
                elif type(getattr(classObject,member)) == str:
                    setattr(classObject,member,str(value))
                    break
                elif type(getattr(classObject,member)) == float and type(value) == int:
                    setattr(classObject,member,float(value))
                    break
                elif type(getattr(classObject,member)) == int and type(value) == float:
                    setattr(classObject,member,int(value))
                    break
    classObject.enabled = True
    classObject.log = True
    classObject._id= "000000000001010000000000-" + str(uuid.uuid4())
    classObject.functionName = functionName
    classObject.functionArgs = args
    return classObject

def executeCodifyFlow(sessionData,eventsData,codifyData,eventCount=0,maxDuration=60):

    # Build Flow
    conductFlow = []
    flows = []
    flowLevel = {}
    for flow in codifyData.split("\n"):
        if flow:
            flowIndentLevel = len(flow.split("\t"))-1
            flow = flow.replace("\t","")
            if flowIndentLevel == 0:
                events = jimi.helpers.typeCast(eventsData)
                classObject = getObjectFromCode(sessionData,flow)
                if type(events) != list:
                    classObject.checkHandler()
                    events = classObject.result["events"]
                    if eventCount>0:
                        events = events[:eventCount]
                flows.append({ "events": events, "classObject" : classObject, "flowID" : str(uuid.uuid4()), "triggerID" : classObject._id, "type" : "trigger", "codeLine" : flow, "next" : [] })
                flowLevel[flowIndentLevel] = flows[-1]
                conductFlow.append(flowLevel[flowIndentLevel])
            else:
                if len(flow.split("->")) == 2:
                    classObject = getObjectFromCode(sessionData,flow.split("->")[1])
                    flowLevel[flowIndentLevel-1]["next"].append({ "classObject" : classObject, "flowID" : str(uuid.uuid4()), "actionID" : classObject._id, "type" : "action", "codeLine" : flow.split("->")[1], "logic" : jimi.helpers.typeCast(flow.split("->")[0][6:-1]), "next" : [] })
                else:
                    classObject = getObjectFromCode(sessionData,flow)
                    flowLevel[flowIndentLevel-1]["next"].append({ "classObject" : classObject, "flowID" : str(uuid.uuid4()), "actionID" : classObject._id, "type" : "action", "codeLine" : flow, "logic" : True, "next" : [] })
                flowLevel[flowIndentLevel] = flowLevel[flowIndentLevel-1]["next"][-1]
                conductFlow.append(flowLevel[flowIndentLevel-1]["next"][-1])

    startTime = time.time()
    output = "Started @ {0}\n\n".format(startTime)
    tempConduct = jimi.conduct._conduct()
    tempConduct._id = "000000000001010000000000-" + str(uuid.uuid4())
    tempConduct.flow = conductFlow
    tempConduct.log = True
    for flow in flows:
        tempData = jimi.conduct.dataTemplate()
        tempData["persistentData"]["system"]["conduct"] = tempConduct
        tempData["persistentData"]["system"]["trigger"] = flow["classObject"]
        for index, event in enumerate(events):
            first = True if index == 0 else False
            last = True if index == len(events) - 1 else False
            eventStat = { "first" : first, "current" : index, "total" : len(events), "last" : last }

            tempDataCopy = jimi.conduct.copyData(tempData)
            tempDataCopy["flowData"]["event"] = event
            tempDataCopy["flowData"]["eventStats"] = eventStat

            try:
                jid = jimi.workers.workers.new("testFire:{0}".format(tempConduct._id),tempConduct.triggerHandler,(flow["flowID"],tempDataCopy,False,True),maxDuration=maxDuration, raiseException=False)
                jimi.workers.workers.wait(jid)
                resultException = jimi.workers.workers.getError(jid)
                if resultException:
                    output = "\n\n***ERROR Start***\n{0}***ERROR End***\n\n".format(''.join(traceback.format_exception(etype=type(resultException), value=resultException, tb=resultException.__traceback__)))
            except Exception as e:
                output = "\n\n***ERROR Start***\n{0}***ERROR End***\n\n".format(''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__)))

    flowDict = {}
    for flow in tempConduct.flow:
        flowDict[flow["flowID"]] = flow
        if "triggerID" in flow:
            flowDict[flow["triggerID"]] = flow
        if "actionID" in flow:
            flowDict[flow["actionID"]] = flow
    # Getting Result From DB
    auditData = jimi.audit._audit().query(query={ "data.conductID" : tempConduct._id },fields=["_id","time","source","type","data","systemID"])["results"]
    for auditItem in auditData:
        if "time" in auditItem:
            auditItem["time"] = time.strftime('%d/%m/%Y %H:%M:%S', time.gmtime(auditItem["time"]))
            if auditItem["source"] == "conduct":
                if auditItem["type"] == "trigger start":
                    output+="{0} - Start\n\t{1}\n\tEvent: {2}\n\tPre-Data: {3}\n".format(flowDict[auditItem["data"]["triggerID"]]["classObject"].functionName,flowDict[auditItem["data"]["triggerID"]]["classObject"].functionArgs,auditItem["data"]["data"]["event"],auditItem["data"]["data"])
                elif auditItem["type"] == "logic":
                    output+="\tLogic String: {0}\n\tLogic Result: {1}\n".format(auditItem["data"]["logicString"],auditItem["data"]["LogicResult"])
                elif auditItem["type"] == "trigger end":
                    output+="\tPost-Data: {1}\n{0} - End\n\n".format(flowDict[auditItem["data"]["triggerID"]]["classObject"].functionName,auditItem["data"]["data"])
            if auditItem["source"] == "action":
                if auditItem["type"] == "action start":
                     output+="\t\t{0} - Start\n\t\t\t{1}\n\t\t\tPre-Data: {2}\n".format(flowDict[auditItem["data"]["actionID"]]["classObject"].functionName,flowDict[auditItem["data"]["actionID"]]["classObject"].functionArgs,auditItem["data"]["data"])
                elif auditItem["type"] == "logic":
                    output+="\t\t\tLogic String: {0}\n\t\t\tLogic Result: {1}\n".format(auditItem["data"]["logicString"],auditItem["data"]["logicResult"])
                elif auditItem["type"] == "link-logic":
                    output+="\t\t\tLink-logic String: {0}\n\t\t\tLink-logic Result: {1}\n".format(auditItem["data"]["linkLogic"],auditItem["data"]["linkLogicResult"])
                elif auditItem["type"] == "action end":
                     output+="\t\t\tPost-Data: {1}\n\t\t\tResult-Data: {2}\n\t\t{0} - End\n".format(flowDict[auditItem["data"]["actionID"]]["classObject"].functionName,auditItem["data"]["data"],auditItem["data"]["actionResult"])

    endTime = time.time()
    output += "\nEnded @ {0}\n".format(endTime)
    output += "Duration @ {0}".format(endTime-startTime)

    return output

######### --------- API --------- #########
if jimi.api.webServer:
    if not jimi.api.webServer.got_first_request:
        if jimi.api.webServer.name == "jimi_core":
            @jimi.api.webServer.route(jimi.api.base+"codify/run/", methods=["POST"])
            def codifyRun():
                data = json.loads(jimi.api.request.data)
                # Function uses token for access passed by jimi_web
                result = executeCodifyFlow(data["sessionData"],data["events"],data["code"],eventCount=int(data["eventCount"]),maxDuration=int(data["timeout"]))
                return { "result" : result }, 200
