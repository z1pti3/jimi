import time

from core.models import action, conduct, webui

class _sleep(action._action):
	sleepFor = int()

	def run(self,data,persistentData,actionResult):
		time.sleep(self.sleepFor)
		actionResult["result"] = True
		actionResult["rc"] = 0
		return actionResult
