import time

import jimi

class _collect(jimi.action._action):
	useCustomData = bool()
	customData = dict()
	limit = int()

	def __init__(self,restrictClass=True):
		self.events = []
		return super(_collect, self).__init__(restrictClass)

	def doAction(self,data):
		try:
			if "skip" in data["flowData"]:
				del data["flowData"]["skip"]
				return { "result" : True, "rc" : 0 }
		except KeyError:
			pass

		if self.useCustomData:
			customData = jimi.helpers.evalDict(self.customData,{"data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" :  data["persistentData"] }) 
			self.events.append(customData)
		else:
			self.events.append(data["flowData"]["event"])

		self.data = data
		if self.limit != 0 and self.limit < len(self.events):
			self.continueFlow()

		# Returning false to stop flow continue
		return { "result" : False, "rc" : 9 }

	def continueFlow(self):
		if self.events:
			tempDataCopy = jimi.conduct.copyData(self.data)
			tempDataCopy["flowData"]["event"] = self.events
			tempDataCopy["flowData"]["skip"] = 1
			self.events = []
			tempDataCopy["flowData"]["eventStats"] = { "first" : True, "current" : 0, "total" : 1, "last" : True }
			self.data["persistentData"]["system"]["conduct"].triggerHandler(self.data["flowData"]["flow_id"],tempDataCopy,flowIDType=True)

	def postRun(self):
		self.continueFlow()
