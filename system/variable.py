
from core import logging, helpers, function
from system import logic

#Dict {
# "varName" : { "value" : "", "if" : "" }
# "varName2" : { "value" : "", "if" : "" }
# }
def varEval(varDict,currentVarDict,dicts={}):
    functionSafeList = function.systemFunctions
    for key, value in varDict.items():
        logicResult = True
        try:
            logicResult = logic.ifEval(value["if"],dicts)
        except KeyError:
            pass
        if logicResult:
            # Checking that supplied dictionary contains key value
            try:
                if type(value["value"]) is str:
                    currentVarDict[key] = helpers.evalString(value["value"],dicts,functionSafeList)
                elif type(value["value"]) is dict:
                    if key in currentVarDict:
                        currentVarDict[key].update(helpers.evalDict(value["value"],dicts,functionSafeList))
                    else:
                        currentVarDict[key] = helpers.evalDict(value["value"],dicts,functionSafeList)
                else:
                    currentVarDict[key] = value["value"]
            except KeyError:
                pass
    return currentVarDict

