import time

from core.models import action, conduct, webui
from core import helpers, logging, cache, settings

import jimi

class _forEach(jimi.action._action):
	manual=bool()
	eventsField = str()
	events=list()
	skip=int()
	mergeEvents = bool()
	limit = int()
	concurrency = int()

	class _properties(jimi.webui._properties):
		def generate(self,classObject):
			formData = []
			formData.append({"type" : "input", "schemaitem" : "_id", "textbox" : classObject._id})
			formData.append({"type" : "input", "schemaitem" : "name", "textbox" : classObject.name})
			formData.append({"type" : "input", "schemaitem" : "eventsField", "textbox" : classObject.eventsField, "tooltip" : "Data within flow to use as a list source"})
			formData.append({"type" : "checkbox", "schemaitem" : "mergeEvents", "checked" : classObject.mergeEvents, "tooltip" : "When selected existng event will be merged with defined events being looped"})
			formData.append({"type" : "checkbox", "schemaitem" : "manual", "checked" : classObject.manual, "tooltip" : "Check to enable events list to take affect"})
			formData.append({"type" : "json-input", "schemaitem" : "events", "textbox" : classObject.events, "tooltip" : "Define a set of events for looping, manual MUST be checked for this to take affect"})
			formData.append({"type" : "input", "schemaitem" : "limit", "textbox" : classObject.limit, "tooltip" : "Defines a maxium number of loops, set to 0 for unlimited"})
			formData.append({"type" : "input", "schemaitem" : "concurrency", "textbox" : classObject.concurrency, "tooltip" : "Defines the number of concurrent threads, set to 0 for non-threaded mode ( default )"})
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
				events = jimi.helpers.evalString(self.eventsField,{"data" : data})
			if self.skip == 0:
				skip = 1
			else:
				skip = self.skip
			if type(events) is list:
				cpuSaver = helpers.cpuSaver()
				tempData = conduct.flowDataTemplate(conduct=persistentData["system"]["conduct"],trigger=self,var=data["var"],plugin=data["plugin"])
				if self.limit > 0:
					events = events[:self.limit]
				eventHandler = None
				if self.concurrency > 0:
					eventHandler = jimi.workers.workerHandler(self.concurrency)
				for index, event in enumerate(events):
					if self.limit > 0:
						if self.limit < index:
							break
					first = True if index == 0 else False
					last = True if index == len(events) - 1 else False
					eventStat = { "first" : first, "current" : index + 1, "total" : len(events), "last" : last }

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

					if eventHandler:
						while eventHandler.countIncomplete() >= self.concurrency:
							cpuSaver.tick()
						if eventHandler.failures:
							if jimi.logging.debugEnabled:
								jimi.logging.debug("forEachTrigger concurrent crash: forEachID={0}".format(self._id),5)
							jimi.audit._audit().add("forEachTrigger","conccurent crash",{ "forEachID" : self._id, "name" : self.name })
							eventHandler.stop()
							raise jimi.exceptions.concurrentCrash
							
						durationRemaining = ( persistentData["system"]["trigger"].startTime + persistentData["system"]["trigger"].maxDuration ) - time.time()
						eventHandler.new("forEachTrigger:{0}".format(data["flowID"]),persistentData["system"]["conduct"].triggerHandler,(data["flowID"],tempDataCopy,False,True,persistentData),maxDuration=durationRemaining)
					else:
						persistentData["system"]["conduct"].triggerHandler(data["flowID"],tempDataCopy,flowIDType=True,persistentData=persistentData)

					cpuSaver.tick()
				# Waiting for all jobs to complete
				if eventHandler:
					eventHandler.waitAll()
					if eventHandler.failures:
						if jimi.logging.debugEnabled:
							jimi.logging.debug("forEachTrigger concurrent crash: forEachID={0}".format(self._id),5)
						jimi.audit._audit().add("forEachTrigger","conccurent crash",{ "forEachID" : self._id, "name" : self.name })
						eventHandler.stop()
						raise jimi.exceptions.concurrentCrash
					eventHandler.stop()
		# Returning false to stop flow continue
		actionResult["result"] = False
		actionResult["rc"] = 200
		return actionResult
