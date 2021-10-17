from core.models import action
from core.models import trigger
import string, secrets
import jimi

class _resetTrigger(action._action):
    enabled = True
    scope = 3

    def run(self,data,persistentData,actionResult):
        try:
            if "event" in data:
                if "triggerID" in data["event"]:
                    failedTrigger = trigger._trigger().getAsClass(id=data["event"]["triggerID"])
                    if len(failedTrigger) == 1:
                        failedTrigger = failedTrigger[0]
                        failedTrigger.startCheck = 0
                        failedTrigger.update(["startCheck"])
                        actionResult["result"] = True
                        actionResult["rc"] = 0
                        return actionResult
        except:
            pass
        actionResult["result"] = False
        actionResult["rc"] = 42
        return actionResult

class _getTrigger(action._action):
    triggerID = str()

    def run(self,data,persistentData,actionResult):
        triggerID = jimi.helpers.evalString(self.triggerID,{"data" : data})
        foundTrigger = trigger._trigger().getAsClass(id=triggerID)
        if len(foundTrigger) == 1:
            foundTrigger = foundTrigger[0]
            actionResult["result"] = True
            actionResult["rc"] = 0
            actionResult["trigger"] = jimi.helpers.classToJson(foundTrigger,hidden=True)
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _setTrigger(action._action):
    triggerID = str()
    field = str()
    value = str()

    def run(self,data,persistentData,actionResult):
        triggerID = jimi.helpers.evalString(self.triggerID,{"data" : data})
        field = jimi.helpers.evalString(self.field,{"data" : data})
        value = jimi.helpers.evalString(self.value,{"data" : data})
        foundTrigger = trigger._trigger().getAsClass(id=triggerID)
        if len(foundTrigger) == 1:
            foundTrigger = foundTrigger[0]
            foundTrigger.setAttribute(field,value)
            foundTrigger.update([field])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _enableTrigger(action._action):
    triggerID = str()

    def run(self,data,persistentData,actionResult):
        triggerID = jimi.helpers.evalString(self.triggerID,{"data" : data})
        foundTrigger = trigger._trigger().getAsClass(id=triggerID)
        if len(foundTrigger) == 1:
            foundTrigger = foundTrigger[0]
            foundTrigger.enabled = True
            foundTrigger.update(["enabled"])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _disableTrigger(action._action):
    triggerID = str()

    def run(self,data,persistentData,actionResult):
        triggerID = jimi.helpers.evalString(self.triggerID,{"data" : data})
        foundTrigger = trigger._trigger().getAsClass(id=triggerID)
        if len(foundTrigger) == 1:
            foundTrigger = foundTrigger[0]
            foundTrigger.enabled = False
            foundTrigger.update(["enabled"])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _getAction(action._action):
    actionID = str()

    def run(self,data,persistentData,actionResult):
        actionID = jimi.helpers.evalString(self.actionID,{"data" : data})
        foundAction = action._action().getAsClass(id=actionID)
        if len(foundAction) == 1:
            foundAction = foundAction[0]
            actionResult["result"] = True
            actionResult["rc"] = 0
            actionResult["action"] = jimi.helpers.classToJson(foundAction,hidden=True)
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _setAction(action._action):
    actionID = str()
    field = str()
    value = str()

    def run(self,data,persistentData,actionResult):
        actionID = jimi.helpers.evalString(self.actionID,{"data" : data})
        field = jimi.helpers.evalString(self.field,{"data" : data})
        value = jimi.helpers.evalString(self.value,{"data" : data})
        foundAction = action._action().getAsClass(id=actionID)
        if len(foundAction) == 1:
            foundAction = foundAction[0]
            foundAction.setAttribute(field,value)
            foundAction.update([field])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _enableAction(action._action):
    actionID = str()

    def run(self,data,persistentData,actionResult):
        actionID = jimi.helpers.evalString(self.actionID,{"data" : data})
        foundAction = action._action().getAsClass(id=actionID)
        if len(foundAction) == 1:
            foundAction = foundAction[0]
            foundAction.enabled = True
            foundAction.update(["enabled"])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _disableAction(action._action):
    actionID = str()

    def run(self,data,persistentData,actionResult):
        actionID = jimi.helpers.evalString(self.actionID,{"data" : data})
        foundAction = action._action().getAsClass(id=actionID)
        if len(foundAction) == 1:
            foundAction = foundAction[0]
            foundAction.enabled = False
            foundAction.update(["enabled"])
            actionResult["result"] = True
            actionResult["rc"] = 0
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 404
        return actionResult

class _generatePassword(action._action):
    length = 16
    lowercase = bool()
    uppercase = bool()
    digits = bool()
    symbols = bool()
    blacklist = str()

    def run(self,data,persistentData,actionResult):
        alphabet = ""
        if self.lowercase:
            alphabet += string.ascii_lowercase
        if self.uppercase:
            alphabet += string.ascii_uppercase
        if self.digits:
            alphabet += string.digits
        if self.symbols:
            alphabet += string.punctuation
        
        for character in self.blacklist:
            alphabet = alphabet.replace(character,"")

        if len(alphabet) > 0:
            while True:
                failedRequirements = False
                generatedPassword = ''.join(secrets.choice(alphabet) for i in range(self.length))
                if self.lowercase and not any(c.islower() for c in generatedPassword):
                    failedRequirements = True
                elif self.uppercase and not any(c.isupper() for c in generatedPassword):
                    failedRequirements = True
                elif self.digits and not any(c.isdigit() for c in generatedPassword):
                    failedRequirements = True
                elif self.symbols and not any(c in string.punctuation for c in generatedPassword):
                    failedRequirements = True
                
                if not failedRequirements:
                    break
        
            actionResult["result"] = True
            actionResult["rc"] = 0
            actionResult["password"] = generatedPassword
            return actionResult
        actionResult["result"] = False
        actionResult["rc"] = 100
        actionResult["msg"] = "Could not generate password"
        return actionResult

class _break(action._action):

    def doAction(self,data):
        raise jimi.exceptions.endFlow

class _exit(action._action):

    def doAction(self,data):
        raise jimi.exceptions.endWorker