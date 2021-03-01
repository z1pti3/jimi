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

	# class _properties(jimi.webui._properties):
	# 	def generate(self,classObject):
	# 		formData = []
	# 		formData.append({"type" : "input", "schemaitem" : "_id", "textbox" : classObject._id})
	# 		formData.append({"type" : "input", "schemaitem" : "name", "textbox" : classObject.name})
	# 		formData.append({"type" : "input", "schemaitem" : "eventsField", "textbox" : classObject.eventsField, "tooltip" : "Data within flow to use as a list source"})
	# 		formData.append({"type" : "checkbox", "schemaitem" : "mergeEvents", "checked" : classObject.mergeEvents, "tooltip" : "When selected existng event will be merged with defined events being looped"})
	# 		formData.append({"type" : "checkbox", "schemaitem" : "manual", "checked" : classObject.manual, "tooltip" : "Check to enable events list to take affect"})
	# 		formData.append({"type" : "json-input", "schemaitem" : "events", "textbox" : classObject.events, "tooltip" : "Define a set of events for looping, manual MUST be checked for this to take affect"})
	# 		formData.append({"type" : "input", "schemaitem" : "limit", "textbox" : classObject.limit, "tooltip" : "Defines a maxium number of loops, set to 0 for unlimited"})
	# 		formData.append({"type" : "input", "schemaitem" : "concurrency", "textbox" : classObject.concurrency, "tooltip" : "Defines the number of concurrent threads, set to 0 for non-threaded mode ( default )"})
	# 		formData.append({"type" : "checkbox", "schemaitem" : "enabled", "checked" : classObject.enabled})
	# 		formData.append({"type" : "checkbox", "schemaitem" : "log", "checked" : classObject.log})
	# 		formData.append({"type" : "input", "schemaitem" : "comment", "textbox" : classObject.comment})
	# 		return formData

	def doAction(self,data):
		try:
			if "skip" in data["flowData"]:
				del data["flowData"]["skip"]
				return { "result" : True, "rc" : 0 }
		except KeyError:
			pass
		
		events = []
		if self.manual:
			events = self.events
		else:
			events = jimi.helpers.evalString(self.eventsField,{"data" : data["flowData"]})
		if self.skip == 0:
			skip = 1
		else:
			skip = self.skip
		# NOTE - try or if faster? It is most likely to be false than true
		if "flowDebugSession" in data["persistentData"]["system"]:
			flowDebugSession = data["persistentData"]["system"]["flowDebugSession"]
		else:
			flowDebugSession = None
		if type(events) is list:
			cpuSaver = helpers.cpuSaver()
			tempData = conduct.dataTemplate(data,keepEvent=True)
			
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

				tempDataCopy = conduct.copyData(tempData)

				if self.mergeEvents:
					try:
						tempDataCopy["flowData"]["event"] = {**data["flowData"]["event"],**event}
						tempDataCopy["flowData"]["eventStats"] = eventStat
					except:
						tempDataCopy["flowData"]["event"] = event
						tempDataCopy["flowData"]["eventStats"] = eventStat
				else:
					tempDataCopy["flowData"]["event"] = event
					tempDataCopy["flowData"]["eventStats"] = eventStat

				# Adding some extra items ( need to go into plugin )
				tempDataCopy["flowData"]["skip"] = skip
				tempDataCopy["flowData"]["callingTriggerID"] = data["flowData"]["trigger_id"]

				if eventHandler:
					while eventHandler.countIncomplete() >= self.concurrency:
						cpuSaver.tick()
					if eventHandler.failures:
						if jimi.logging.debugEnabled:
							jimi.logging.debug("forEachTrigger concurrent crash: forEachID={0}".format(self._id),5)
						jimi.audit._audit().add("forEachTrigger","conccurent crash",{ "forEachID" : self._id, "name" : self.name })
						eventHandler.stop()
						raise jimi.exceptions.concurrentCrash
						
					durationRemaining = ( data["persistentData"]["system"]["trigger"].startTime + data["persistentData"]["system"]["trigger"].maxDuration ) - time.time()
					eventHandler.new("forEachTrigger:{0}".format(data["flowData"]["flow_id"]),data["persistentData"]["system"]["conduct"].triggerHandler,(data["flowData"]["flow_id"],tempDataCopy,False,True,flowDebugSession),maxDuration=durationRemaining)
				else:
					data["persistentData"]["system"]["conduct"].triggerHandler(data["flowData"]["flow_id"],tempDataCopy,flowIDType=True,flowDebugSession=flowDebugSession)

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
		return { "result" : False, "rc" : 200 }
