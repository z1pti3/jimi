import jimi
from core import logging, helpers, function
from system import logic

#Dict {
# "varName" : { "value" : "varValue", "if" : "if 1==1", "scope" : 0 }
# "varName2" : { "value" : "varValue", "if" : "if 1==1", "scope" : 1 }
# "varName3" : [{ "value" : "varValue", "if" : "if 1==2", "scope" : 1 },{ "value" : "varValue", "if" : "if 1==1", "scope" : 1 }]
# }
def varEval(varDict,currentVarDict,dicts={},scope=0):
    try:
        functionSafeList = function.systemFunctions
        for key, value in varDict.items():
            if type(value) is dict:
                doVarEval(key,value,currentVarDict,functionSafeList,dicts,scope)
            else:
                for valueItem in value:
                    if doVarEval(key,valueItem,currentVarDict,functionSafeList,dicts,scope):
                        break
    except Exception as e:
        raise jimi.exceptions.variableDefineFailure(varDict,e)
    return currentVarDict

def doVarEval(key,value,currentVarDict,functionSafeList,dicts,scope):
    if "scope" in value:
        varScope = value["scope"]
    else:
        varScope = 0
    if varScope == scope: 
        logicResult = True
        if "if" in value:
            logicResult = logic.ifEval(value["if"],dicts)
        if logicResult:
            if type(value["value"]) is str:
                currentVarDict[key] = helpers.evalString(value["value"],dicts,functionSafeList)
            elif type(value["value"]) is dict:
                if key in currentVarDict:
                    currentVarDict[key].update(helpers.evalDict(value["value"],dicts,functionSafeList))
                else:
                    currentVarDict[key] = helpers.evalDict(value["value"],dicts,functionSafeList)
            elif type(value["value"]) is list:
                currentVarDict[key] = helpers.evalList(value["value"],dicts,functionSafeList)
            else:
                currentVarDict[key] = value["value"]
            return True
    return False

