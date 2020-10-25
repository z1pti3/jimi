import time

from core.models import action, conduct
from core import helpers, logging, cache, settings

class _forEach(action._action):
	manual=bool()
	eventsField = str()
	events=list()
	skip=int()
	mergeEvents = bool()

	def run(self,data,persistentData,actionResult):
		if "skip" in data:
			del data["skip"]
			actionResult["result"] = True
			actionResult["rc"] = 0
			return actionResult
		else:
			events = []
			if self.manual:
				events = self.events
			else:
				events = helpers.evalString(self.eventsField,{"data" : data})
			if self.skip == 0:
				skip = 1
			else:
				skip = self.skip
			if type(events) is list:
				cpuSaver = helpers.cpuSaver()
				tempData = conduct.flowDataTemplate(conduct=persistentData["system"]["conduct"],trigger=self,var=data["var"],plugin=data["plugin"])
				for index, event in enumerate(events):
					first = True if index == 0 else False
					last = True if index == len(events) - 1 else False
					eventStat = { "first" : first, "current" : index, "total" : len(events), "last" : last }

					tempDataCopy = conduct.copyFlowData(tempData)

					if self.mergeEvents:
						tempDataCopy["event"] = {**data["event"],**event}
						tempDataCopy["eventStats"] = eventStat
					else:
						tempDataCopy["event"] = event
						tempDataCopy["eventStats"] = eventStat

					# Adding some extra items ( need to go into plugin )
					tempDataCopy["skip"] = skip
					tempDataCopy["callingTriggerID"] = data["triggerID"]

					persistentData["system"]["conduct"].triggerHandler(data["flowID"],tempDataCopy,flowIDType=True,persistentData=persistentData)

					cpuSaver.tick()
		# Returning false to stop flow continue
		actionResult["result"] = False
		actionResult["rc"] = 200
		return actionResult
