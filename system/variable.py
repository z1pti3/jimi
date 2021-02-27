
from core import logging, helpers, function
from system import logic

#Dict {
# "varName" : { "value" : "", "if" : "", "scope" : 0 }
# "varName2" : { "value" : "", "if" : "", "scope" : 1 }
# }
def varEval(varDict,currentVarDict,dicts={},scope=0):
    functionSafeList = function.systemFunctions
    for key, value in varDict.items():
        if "scope" in value:
            varScope = value["scope"]
        else:
            varScope = 0
        if varScope == scope: 
            logicResult = True
            if "if" in value:
                logicResult = logic.ifEval(value["if"],dicts)
            if logicResult:
                # Checking that supplied dictionary contains key value
                if "value" in value:
                    if type(value["value"]) is str:
                        currentVarDict[key] = helpers.evalString(value["value"],dicts,functionSafeList)
                    elif type(value["value"]) is dict:
                        if key in currentVarDict:
                            currentVarDict[key].update(helpers.evalDict(value["value"],dicts,functionSafeList))
                        else:
                            currentVarDict[key] = helpers.evalDict(value["value"],dicts,functionSafeList)
                    else:
                        currentVarDict[key] = value["value"]
    return currentVarDict

