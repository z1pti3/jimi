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

def getObjectFromCode(codeFunction):
    functionName = codeFunction.split("(")[0]
    args = regexCommor.split(codeFunction[(len(functionName)+1):-1])
    classObject = model._model().getAsClass(query={ "name" : functionName })[0].classObject()
    members = [attr for attr in dir(classObject) if not callable(getattr(classObject, attr)) and not "__" in attr and attr ]
    for arg in args:
        key = arg.split("=")[0]
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
    return classObject()

def executeCodifyFlow(eventsData,codifyData):
    outputText = ""

    flows = []
    flowLevel = {}
    for flow in codifyData.split("\n"):
        flowIndentLevel = len(flow.split("\t"))-1
        if flowIndentLevel == 0:
            events = helpers.evalString(eventsData)
            if type(events) != list:
                classObject = getObjectFromCode(flow)
                classObject.checkHeader()
                classObject.check()
                events = classObject.result["events"]
            flows.append({ "events": events, "classObject" : classObject, "type" : "trigger", "codeLine" : flow, "next" : [] })
            if flowIndentLevel not in flowLevel:
                flowLevel[flowIndentLevel] = flows[-1]
        else:
            classObject = getObjectFromCode(flow.split("->")[1])
            flowLevel[flowIndentLevel-1]["next"].append({ "classObject" : classObject, "type" : "action", "codeLine" : flow.split("->")[1], "logic" : flow.split("->")[0], "next" : [] })
            if flowIndentLevel not in flowLevel:
                flowLevel[flowIndentLevel] = flowLevel[flowIndentLevel-1]["next"][-1]
        
    for flow in flows:
        persistentData = {}
        for event in flow["events"]:
            data = { "event" : event, "var" : {}, "plugin" : {} }
            processQueue = []
            currentFlow = flow
            currentObject = currentFlow["classObject"]
            loops =  0
            while True:
                if currentObject:
                    if currentFlow["type"] == "trigger":
                        outputText+="\nExecuted {0}".format(currentFlow["codeLine"])
                        outputText+="\ndata={0}".format(data)
                        objectContinue = True
                        if currentObject.logicString.startswith("if"):
                            if logic.ifEval(currentObject.logicString,{ "data" : data}):
                                outputText+="\nLogic Pass"
                                if currentObject.varDefinitions:
                                        data["var"] = variable.varEval(currentObject.varDefinitions,data["var"],{ "data" : data})
                                else:
                                    objectContinue = False
                            else:
                                outputText+="\nLogic Failed"
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
                        outputText+="\ndata={0}".format(data)
                        outputText+="\n"
                    elif currentFlow["type"] == "action":
                        if currentObject.enabled:
                            outputText+="\nExecuted {0}".format(currentFlow["codeLine"])
                            outputText+="\ndata={0}".format(data)
                            if flowLogicEval(data,helpers.typeCast(re.sub('\W','',currentFlow["logic"][7:-1]))):
                                outputText+="\nFlow Logic Pass"
                                data["action"] = currentObject.runHandler(data,persistentData)
                                passData = data
                                for nextFlow in currentFlow["next"]:
                                    if not passData:
                                        passData = copy.deepcopy(data)
                                    processQueue.append({ "flow" : nextFlow, "data" : passData })
                                    passData = None
                                outputText+="\ndata={0}".format(data)
                            else:
                                outputText+="\nFlow Logic Failed"
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
    return outputText

######### --------- API --------- #########
if api.webServer:
    if not api.webServer.got_first_request:
        @api.webServer.route(api.base+"codify/run/", methods=["POST"])
        def codifyRun():
            data = json.loads(api.request.data)
            result = executeCodifyFlow(data["events"],data["code"])
            return { "result" : result }, 200

