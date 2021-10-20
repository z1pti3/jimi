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

	def runHandler(self,data=None,debug=False):
		try:
			if "skip" in data["flowData"]:
				actionResult = self.doAction(data)
				return actionResult
		except KeyError:
			pass
		return super(_forEach, self).runHandler(data=data,debug=debug)

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
			events = jimi.helpers.evalString(self.eventsField,{"data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"]})
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
				concurrentEvents = []
			try:
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
							try:
								event = { "value" : event }
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
						concurrentEvents.append(tempDataCopy)	
					else:
						data["persistentData"]["system"]["conduct"].triggerHandler(data["flowData"]["flow_id"],tempDataCopy,flowIDType=True,flowDebugSession=flowDebugSession)

					cpuSaver.tick()
				# Waiting for all jobs to complete
				if eventHandler:
					eventBatches = jimi.helpers.splitList(concurrentEvents,int(len(concurrentEvents)/self.concurrency))
					for events in eventBatches:
						durationRemaining = ( data["persistentData"]["system"]["trigger"].startTime + data["persistentData"]["system"]["trigger"].maxDuration ) - time.time()
						eventHandler.new("forEachTrigger:{0}".format(data["flowData"]["flow_id"]),data["persistentData"]["system"]["conduct"].triggerBatchHandler,(data["flowData"]["flow_id"],events,False,True,flowDebugSession),maxDuration=durationRemaining)

					eventHandler.waitAll()
					if eventHandler.failures or eventHandler.failureCount() > 0:
						if jimi.logging.debugEnabled:
							jimi.logging.debug("forEachTrigger concurrent crash: forEachID={0}".format(self._id),5)
						eventHandler.stop()
						raise jimi.exceptions.concurrentCrash(self._id,self.name,eventHandler.failures)
					eventHandler.stop()
			except jimi.exceptions.endFlow:
				pass
		# Returning false to stop flow continue
		return { "result" : False, "rc" : 200 }
