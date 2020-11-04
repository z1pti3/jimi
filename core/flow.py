import re
import json
import copy
import time
import uuid

from core import api, helpers, model, settings
from system import variable, logic

from core.models import conduct

cpuSaver = settings.config["cpuSaver"]

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
    classObject = model._model().getAsClass(sessionData=sessionData,query={ "name" : functionName })[0].classObject()()
    classObject.enabled = True
    classObject.log = True
    classObject._id= "000000000001010000000000"
    classObject.functionName = functionName
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
    return classObject

def executeCodifyFlow(sessionData,eventsData,codifyData,eventCount=0,persistentData=None):
    if not persistentData:
        persistentData = {}

    # Build Flow
    conductFlow = []
    flows = []
    flowLevel = {}
    for flow in codifyData.split("\n"):
        if flow:
            flowIndentLevel = len(flow.split("\t"))-1
            flow = flow.replace("\t","")
            if flowIndentLevel == 0:
                events = helpers.typeCast(eventsData)
                classObject = getObjectFromCode(sessionData,flow)
                if type(events) != list:
                    classObject.checkHeader()
                    classObject.check()
                    events = classObject.result["events"]
                flows.append({ "events": events, "classObject" : classObject, "flowID" : str(uuid.uuid4()), "triggerID" : classObject._id, "type" : "trigger", "codeLine" : flow, "next" : [] })
                flowLevel[flowIndentLevel] = flows[-1]
                conductFlow.append(flowLevel[flowIndentLevel])
            else:
                if len(flow.split("->")) == 2:
                    classObject = getObjectFromCode(sessionData,flow.split("->")[1])
                    flowLevel[flowIndentLevel-1]["next"].append({ "classObject" : classObject, "flowID" : str(uuid.uuid4()), "actionID" : classObject._id, "type" : "action", "codeLine" : flow.split("->")[1], "logic" : helpers.typeCast(flow.split("->")[0][6:-1]), "next" : [] })
                else:
                    classObject = getObjectFromCode(sessionData,flow)
                    flowLevel[flowIndentLevel-1]["next"].append({ "classObject" : classObject, "flowID" : str(uuid.uuid4()), "actionID" : classObject._id, "type" : "action", "codeLine" : flow, "logic" : True, "next" : [] })
                flowLevel[flowIndentLevel] = flowLevel[flowIndentLevel-1]["next"][-1]
                conductFlow.append(flowLevel[flowIndentLevel-1]["next"][-1])

    tempConduct = conduct._conduct()
    tempConduct._id = "000000000001010000000000"
    tempConduct.flow = conductFlow
    tempConduct.log = True
    for flow in flows:
        tempData = conduct.flowDataTemplate(conduct=tempConduct,trigger=flow["classObject"])
        for index, event in enumerate(events):
            first = True if index == 0 else False
            last = True if index == len(events) - 1 else False
            eventStat = { "first" : first, "current" : index, "total" : len(events), "last" : last }

            tempDataCopy = conduct.copyFlowData(tempData)

            tempDataCopy["event"] = event
            tempDataCopy["eventStats"] = eventStat

            tempConduct.triggerHandler(flow["flowID"],tempDataCopy,flowIDType=True)

######### --------- API --------- #########
if api.webServer:
    if not api.webServer.got_first_request:
        @api.webServer.route(api.base+"codify/run/", methods=["POST"])
        def codifyRun():
            data = json.loads(api.request.data)
            result = executeCodifyFlow(data["sessionData"],data["events"],data["code"],eventCount=int(data["eventCount"]))
            return { "result" : result }, 200
