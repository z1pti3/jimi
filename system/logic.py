import re

from core import logging, helpers, function

regexLogicString = re.compile(r'((\"(.*?[^\\])\"|([a-zA-Z0-9]+(\[(.*?)\])+)|([a-zA-Z0-9]+(\((.*?)(\)\)|\)))+)|\[(.*?)\]|([a-zA-Z0-9\.]*)))\s?( not match | match | not in | in |==|!=|>=|>|<=|<)\s?((\"(.*?[^\\])\"|([a-zA-Z0-9]+(\[(.*?)\])+)|([a-zA-Z0-9]+(\((.*?)(\)\)|\))(|$))+)|\[(.*?)\]|([a-zA-Z0-9\.]*)))')
regexLogicSafeValidationString = re.compile(r'^(True|False|\(|\)| |or|and|not)*$')

def ifEval(logicString,dicts={},debug=False):
    functionSafeList = function.systemFunctions
    if "if " == logicString[:3]:
        tempLogic = logicString[3:]
        explainLogin = tempLogic
        logicMatches = regexLogicString.finditer(tempLogic)
        for index, logicMatch in enumerate(logicMatches, start=1):
            statement = [logicMatch.group(1).strip(),logicMatch.group(14).strip(),logicMatch.group(13).strip()]
            # Cast typing statement vars
            for x in range(0,2):
                statement[x] = helpers.typeCast(statement[x],dicts,functionSafeList)
            tempLogic = tempLogic.replace(logicMatch.group(0),str(logicProcess(statement)))
            explainLogin = explainLogin.replace(logicMatch.group(0),str(statement))
        # Checking that result only includes True, False, ( ), or, and,
        if regexLogicSafeValidationString.search(tempLogic):
            result = eval(tempLogic) # Can be an unsafe call be very careful with this!
            if debug:
                return result, tempLogic, explainLogin
            return result
        else:
            if logging.debugEnabled:
                logging.debug("Action logicEval tempLogic contains unsafe items, tempLogic='{0}'".format(tempLogic),3)
    else:
        return True
    return False

def logicProcess(statement):
    try:
        if statement[2] == "==":
            return (statement[0] == statement[1])
        elif statement[2] == "!=":
            return (statement[0] != statement[1])
        elif statement[2] == ">":
            return (statement[0] > statement[1])
        elif statement[2] == ">=":
            return (statement[0] >= statement[1])
        elif statement[2] == "<":
            return (statement[0] < statement[1])
        elif statement[2] == "<=":
            return (statement[0] <= statement[1])
        elif statement[2] == "in":
            return (statement[0] in statement[1])
        elif statement[2] == "not in":
            return (statement[0] not in statement[1])
        elif statement[2].startswith("match"):
            if re.search(statement[1],statement[0]):
                return True
            else:
                return False
        elif statement[2].startswith("not match"):
            if re.search(statement[1],statement[0]):
                return False
            else:
                return True
        else:
            return False
    except:
        if logging.debugEnabled:
            logging.debug("logicProcess process failed, statement='{0}'".format(statement),5)
        return False


            