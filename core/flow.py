import re
import json
import copy
import time
import uuid
import traceback

import jimi

from system import variable, logic

cpuSaver = jimi.settings.getSetting("cpuSaver",None)

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

    sessionID = jimi.debug.newFlowDebugSession(sessionData)
    flowDebugSession = { "sessionID" : sessionID }
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
        tempData["flowData"]["conduct_id"] = tempConduct._id
        tempData["flowData"]["conduct_name"] = tempConduct.name
        tempData["flowData"]["trigger_id"] = flow["classObject"]._id
        tempData["flowData"]["trigger_name"] = flow["classObject"].name
        for index, event in enumerate(events):
            first = True if index == 0 else False
            last = True if index == len(events) - 1 else False
            eventStat = { "first" : first, "current" : index, "total" : len(events), "last" : last }

            tempDataCopy = jimi.conduct.copyData(tempData)
            tempDataCopy["flowData"]["event"] = event
            tempDataCopy["flowData"]["eventStats"] = eventStat

            tempConduct.triggerHandler(flow["flowID"],tempDataCopy,False,True,flowDebugSession)

    output += json.dumps(jimi.helpers.dictToJson(jimi.debug.flowDebugSession[sessionID].flowList), indent=4)
    jimi.debug.deleteFlowDebugSession(sessionID)

    endTime = time.time()
    output += "\nEnded @ {0}\n".format(endTime)
    output += "Duration @ {0}".format(endTime-startTime)
    

    return output

def flowHandler(sessionData,conductID,triggerType,triggerID,events,flowDebugSession=None):
    loadedConduct = jimi.conduct._conduct().getAsClass(sessionData=sessionData,id=conductID)[0]
    if triggerType == "action":
        loadedTrigger = jimi.action._action().getAsClass(sessionData=sessionData,id=triggerID)[0]
    elif triggerType == "flow":
        flow = [ x for x in loadedConduct.flow if "flowID" in x and x["flowID"] == triggerID ]
        if flow["type"] == "action":
            loadedTrigger = jimi.action._action().getAsClass(sessionData=sessionData,id=flow["actionID"])[0]
        else:
            loadedTrigger = jimi.trigger._trigger().getAsClass(sessionData=sessionData,id=flow["triggerID"])[0]
    else:
        loadedTrigger = jimi.trigger._trigger().getAsClass(sessionData=sessionData,id=triggerID)[0]
    data = jimi.conduct.dataTemplate()
    data["persistentData"]["system"]["trigger"] = loadedTrigger
    data["flowData"]["trigger_id"] = triggerID
    data["flowData"]["trigger_name"] = loadedTrigger.name
    data["flowData"]["conduct_id"] = loadedConduct._id
    data["flowData"]["conduct_name"] = loadedConduct.name
    for index, event in enumerate(events):
        first = True if index == 0 else False
        last = True if index == len(events) - 1 else False
        eventStats = { "first" : first, "current" : index, "total" : len(events), "last" : last }

        tempData = jimi.conduct.copyData(data)
        tempData["flowData"]["event"] = event
        tempData["flowData"]["eventStats"] = eventStats

        if triggerType == "action":
            loadedConduct.triggerHandler(triggerID,data,actionIDType=True,flowDebugSession=flowDebugSession)
        elif triggerType == "flow":
            loadedConduct.triggerHandler(triggerID,data,flowIDType=True,flowDebugSession=flowDebugSession)
        else:
            loadedConduct.triggerHandler(triggerID,data,flowDebugSession=flowDebugSession)


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

            @jimi.api.webServer.route(jimi.api.base+"flow/<conductID>/<triggerType>/<triggerID>/", methods=["POST"])
            def runFlow(conductID,triggerType,triggerID):
                data = json.loads(jimi.api.request.data)
                sessionData = data["sessionData"]
                events = data["events"]
                eventCount = int(data["eventCount"])
                if eventCount > 0:
                    events = events[:eventCount]
                maxDuration = data["timeout"]
                sessionID = jimi.debug.newFlowDebugSession(sessionData)
                flowDebugSession = { "sessionID" : sessionID }
                jimi.workers.workers.new("runFlow",flowHandler,(sessionData,conductID,triggerType,triggerID,events,flowDebugSession),maxDuration=maxDuration)
                return { "sessionID" : sessionID }, 200
