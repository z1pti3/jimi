from core.models import action
from core.models import trigger

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