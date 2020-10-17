import re
import json
import copy
import time

from core import api, helpers, model, settings
from system import variable, logic

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
    functionName = codeFunction.split("(")[0]
    args = regexCommor.split(codeFunction.strip()[(len(functionName)+1):-1])
    classObject = model._model().getAsClass(sessionData=sessionData,query={ "name" : functionName })[0].classObject()()
    classObject.enabled = True
    classObject._id= "000000000001010000000000"
    classObject.functionName = functionName
    members = [attr for attr in dir(classObject) if not callable(getattr(classObject, attr)) and not "__" in attr and attr ]
    for arg in args:
        arg=arg.replace("(\)n","\n").replace("(\)t","\t")
        key = arg.split("=")[0]
        if len(arg[len(key)+1:]) > 2:
            if ((arg[len(key)+1:][1] == "[" or arg[len(key)+1:][1] == "{") and (arg[len(key)+1:][-2] == "]" or arg[len(key)+1:][-2] == "}")):
                value = helpers.typeCast(arg[len(key)+1:][1:-1])
            else:
                value = helpers.typeCast(arg[len(key)+1:])
        else:
            value = helpers.typeCast(arg[len(key)+1:])
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

def executeCodifyFlow(sessionData,eventsData,codifyData,eventCount=0,passedFlow=[],persistentData=None):
    outputText = "Started At - {0}".format(time.time())

    if not persistentData:
        persistentData = {}

    if passedFlow == []:
        # Build Flow
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
                    flows.append({ "events": events, "classObject" : classObject, "type" : "trigger", "codeLine" : flow, "next" : [] })
                    flowLevel[flowIndentLevel] = flows[-1]
                else:
                    if len(flow.split("->")) == 2:
                        classObject = getObjectFromCode(sessionData,flow.split("->")[1])
                        flowLevel[flowIndentLevel-1]["next"].append({ "classObject" : classObject, "type" : "action", "codeLine" : flow.split("->")[1], "logic" : flow.split("->")[0], "next" : [] })
                    else:
                        classObject = getObjectFromCode(sessionData,flow)
                        flowLevel[flowIndentLevel-1]["next"].append({ "classObject" : classObject, "type" : "action", "codeLine" : flow, "logic" : "logic(True)", "next" : [] })
                    flowLevel[flowIndentLevel] = flowLevel[flowIndentLevel-1]["next"][-1]
    else:
        # Hack for forEach - need a longer term neater reusable fix for this
        passedFlow["events"] = eventsData
        flows = [passedFlow]
        
    # Execute Flow
    for flow in flows:
        eventCounter = 0
        for event in flow["events"]:
            if eventCount != 0 and eventCounter >= eventCount:
                break
            elif eventCount != 0:
                eventCounter+=1
            outputText+="\n-----------------------------------------------------------------------------------"
            outputText+="\nNow Running For Event - {0}".format(event)
            outputText+="\n-----------------------------------------------------------------------------------"
            outputText+="\n"
            data = { "event" : event, "eventStats" : { "first" : False, "current" : 0, "total" : 0, "last" : False }, "conductID" : "codify", "flowID" : "codify", "var" : {}, "plugin" : {}, "triggerID" : "000000000001010000000000" }
            processQueue = []
            currentFlow = flow
            currentObject = currentFlow["classObject"]
            loops =  0
            while True:
                if currentObject:
                    if currentFlow["type"] == "trigger":
                        if currentObject.name == "":
                            outputText+="\nTRIGGER"
                        else:
                            outputText+="\n(t) - {0}:".format(currentObject.name)
                        outputText+="\n\t[function]\n\t\t{0}".format(currentFlow["codeLine"])
                        outputText+="\n\t[pre-data]\n\t\t{0}".format(data)
                        objectContinue = True
                        if currentObject.logicString.startswith("if"):
                            outputText+="\n\t[logic]\n\t\t{0}\n\t\t".format(currentObject.logicString)
                            if logic.ifEval(currentObject.logicString,{ "data" : data}):
                                outputText+="Pass"
                                if currentObject.varDefinitions:
                                        data["var"] = variable.varEval(currentObject.varDefinitions,data["var"],{ "data" : data})
                                else:
                                    objectContinue = False
                            else:
                                outputText+="Failed"
                        else:
                            if currentObject.varDefinitions:
                                data["var"] = variable.varEval(currentObject.varDefinitions,data["var"],{ "data" : data})
                        if objectContinue:
                            passData = data
                            for nextFlow in currentFlow["next"]:
                                if not passData:
                                    passData = copy.deepcopy(data)
                                processQueue.append({ "flow" : nextFlow, "data" : passData })
                                passData = None
                        outputText+="\n\t[post-data] - \n\t\t{0}".format(data)
                        outputText+="\n"
                    elif currentFlow["type"] == "action":
                        if currentObject.name == "":
                            outputText+="\nACTION"
                        else:
                            outputText+="\n(a) - {0}:".format(currentObject.name)
                        if currentObject.enabled:
                            outputText+="\n\t[function]\n\t\t{0}".format(currentFlow["codeLine"])
                            outputText+="\n\t[pre-data]\n\t\t{0}".format(data)
                            flowLogic = currentFlow["logic"][5:]
                            outputText+="\n\t[link logic]\n\t\t{0}\n\t\t".format(flowLogic)
                            if flowLogicEval(data,helpers.typeCast(flowLogic)):
                                outputText+="Pass"
                                debugText=""
                                # Special function handler - need better long term fix whereby the object class is not being bypassed
                                if currentObject.functionName == "forEach":
                                    try:
                                        proceed = (currentObject != passedFlow["classObject"])
                                    except:
                                        proceed = True
                                    if proceed:
                                        logicResult = True
                                        if currentObject.logicString.startswith("if"):
                                            logicDebugText, logicResult = logic.ifEval(currentObject.logicString, { "data" : data }, debug=True)
                                            debugText+="\n\t[action logic]\n\t\t{0}\n\t\t{1}\n\t\t({2})".format(currentObject.logicString,logicResult,logicDebugText)
                                        if logicResult:
                                            events = []
                                            if currentObject.manual:
                                                events = currentObject.events
                                            else:
                                                events = helpers.evalString(currentObject.eventsField,{"data" : data})
                                            debugText = executeCodifyFlow(sessionData,events,codifyData,eventCount=0,passedFlow=currentFlow,persistentData=persistentData)
                                else:
                                    debugText, data["action"] = currentObject.runHandler(data,persistentData,debug=True)
                                if debugText != "":
                                    outputText+="{0}".format(debugText)
                                passData = data
                                for nextFlow in currentFlow["next"]:
                                    if not passData:
                                        passData = copy.deepcopy(data)
                                    processQueue.append({ "flow" : nextFlow, "data" : passData })
                                    passData = None
                                outputText+="\n\t[post-data]\n\t\t{0}".format(data)
                            else:
                                outputText+="Failed"
                            outputText+="\n"
                if len(processQueue) == 0:
                    break
                else:
                    currentObject = processQueue[-1]["flow"]["classObject"]
                    currentFlow = processQueue[-1]["flow"]
                    data = processQueue[-1]["data"]
                    processQueue.pop()
                # CPU saver
                loops+=1
                if cpuSaver:
                    if loops > cpuSaver["loopL"]:
                        loops = 0
                        time.sleep(cpuSaver["loopT"])
    outputText += "\nEnded At - {0}".format(time.time())
    return outputText

######### --------- API --------- #########
if api.webServer:
    if not api.webServer.got_first_request:
        @api.webServer.route(api.base+"codify/run/", methods=["POST"])
        def codifyRun():
            data = json.loads(api.request.data)
            result = executeCodifyFlow(data["sessionData"],data["events"],data["code"],eventCount=int(data["eventCount"]))
            return { "result" : result }, 200
