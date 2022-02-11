import jimi
import time

class _subFlow(jimi.action._action):
	triggerID = str()
	customEventsValue = False
	eventsValue = str()
	customEventsList = False
	eventsList = list()
	mergeFinalDataValue = False 
	mergeFinalEventValue = False
	mergeFinalConductValue = False
	useNewDataTemplate = False
	maxRetries = int()
	retryDelay = int()

	def doAction(self,data):
		triggerID = jimi.helpers.evalString(self.triggerID,{"data" : data["flowData"]})

		events = [data["flowData"]["event"]]

		if self.useNewDataTemplate:
			tempData = jimi.conduct.dataTemplate(data=data)
		else:
			tempData = jimi.conduct.copyData(jimi.conduct.dataTemplate(data,keepEvent=True))
		tempData["flowData"]["callingTriggerID"] = data["flowData"]["trigger_id"]
		currentConduct = data["persistentData"]["system"]["conduct"]

		if self.customEventsValue:
			events = jimi.helpers.evalString(self.eventsValue,{"data" : data["flowData"]})
			if type(events) is not list:
				events = [events]
		if self.customEventsList:
			events = jimi.helpers.evalList(self.eventsList,{"data" : data["flowData"]})

		maxRetries = self.maxRetries
		while True:
			trigger = jimi.trigger._trigger().getAsClass(id=triggerID)
			if len(trigger) == 1:
				subflowResult = True
				trigger = trigger[0]
				try:
					finalData = trigger.notify(events,tempData)
				except jimi.exceptions.endWorker as e:
					finalData = e.data
				if "subflowResult" in finalData["flowData"]["var"]:
					subflowResult = finalData["flowData"]["var"]["subflowResult"]
				if subflowResult:
					if self.mergeFinalDataValue:
						data["flowData"]["action"] = finalData["flowData"]["action"]
						data["flowData"]["var"] = finalData["flowData"]["var"]
						data["flowData"]["plugin"] = finalData["flowData"]["plugin"]
					if self.mergeFinalEventValue:
						data["eventData"]["var"] = finalData["eventData"]["var"]
						data["eventData"]["plugin"] = finalData["eventData"]["plugin"]
					if self.mergeFinalConductValue:
						data["conductData"]["var"] = finalData["conductData"]["var"]
						data["conductData"]["plugin"] = finalData["conductData"]["plugin"]
					break
				elif maxRetries > 0:
					maxRetries -= 1
					time.sleep(self.retryDelay)
				else:
					break
			else:
				data["persistentData"]["system"]["conduct"] = currentConduct
				return { "result" : False, "rc" : 5, "msg" : "Unable to find the specified triggerID={0}".format(triggerID) }

		data["persistentData"]["system"]["conduct"] = currentConduct
		return { "result" : subflowResult, "rc" : 0 }

class _subFlowReturn(jimi.action._action):
	subFlowResult = True

	def doAction(self,data):
		data["flowData"]["var"]["subflowResult"] = self.subFlowResult
		raise jimi.exceptions.endWorker(data)
