import time

from core.models import action, conduct, webui
from core import helpers, logging, cache, settings

class _collect(action._action):
	limit = int()

	def __init__(self):
		self.events = []

	def doAction(self,data):
		try:
			if "skip" in data["flowData"]:
				del data["flowData"]["skip"]
				return { "result" : True, "rc" : 0 }
		except KeyError:
			pass
		
		self.events.append(data["flowData"]["event"])
		self.data = data
		if self.limit != 0 and self.limit < len(self.events):
			self.continueFlow()

		# Returning false to stop flow continue
		return { "result" : False, "rc" : 9 }

	def continueFlow(self):
		if self.events:
			tempDataCopy = conduct.copyData(self.data)
			tempDataCopy["flowData"]["event"] = self.events
			tempDataCopy["flowData"]["skip"] = 1
			self.events = []
			tempDataCopy["flowData"]["eventStats"] = { "first" : True, "current" : 0, "total" : 1, "last" : True }
			self.data["persistentData"]["system"]["conduct"].triggerHandler(self.data["flowData"]["flow_id"],tempDataCopy,flowIDType=True)

	def postRun(self):
		self.continueFlow()
