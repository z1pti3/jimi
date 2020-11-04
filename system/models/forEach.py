import time

from core.models import action, conduct, webui
from core import helpers, logging, cache, settings

class _forEach(action._action):
	manual=bool()
	eventsField = str()
	events=list()
	skip=int()
	mergeEvents = bool()
	limit = int()

	class _properties(webui._properties):
		def generate(self,classObject):
			formData = []
			formData.append({"type" : "input", "schemaitem" : "_id", "textbox" : classObject._id})
			formData.append({"type" : "input", "schemaitem" : "name", "textbox" : classObject.name})
			formData.append({"type" : "input", "schemaitem" : "eventsField", "textbox" : classObject.eventsField, "tooltip" : "Data within flow to use as a list source"})
			formData.append({"type" : "checkbox", "schemaitem" : "mergeEvents", "checked" : classObject.mergeEvents, "tooltip" : "When selected existng event will be merged with defined events being looped"})
			formData.append({"type" : "checkbox", "schemaitem" : "manual", "checked" : classObject.manual, "tooltip" : "Check to enable events list to take affect"})
			formData.append({"type" : "json-input", "schemaitem" : "events", "textbox" : classObject.events, "tooltip" : "Define a set of events for looping, manual MUST be checked for this to take affect"})
			formData.append({"type" : "input", "schemaitem" : "limit", "textbox" : classObject.limit, "tooltip" : "Defines a maxium number of loops, set to 0 for unlimited"})
			formData.append({"type" : "checkbox", "schemaitem" : "enabled", "checked" : classObject.enabled})
			formData.append({"type" : "checkbox", "schemaitem" : "log", "checked" : classObject.log})
			formData.append({"type" : "input", "schemaitem" : "comment", "textbox" : classObject.comment})
			return formData

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
				if self.limit > 0:
					events = events[:self.limit]
				for index, event in enumerate(events):
					if self.limit > 0:
						if self.limit < index:
							break
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
