import time

from core.models import action, conduct, webui
from core import helpers, logging, cache, settings

class _collect(action._action):
	limit = int()

	class _properties(webui._properties):
		def generate(self,classObject):
			formData = []
			formData.append({"type" : "input", "schemaitem" : "_id", "textbox" : classObject._id})
			formData.append({"type" : "input", "schemaitem" : "name", "textbox" : classObject.name})
			formData.append({"type" : "input", "schemaitem" : "limit", "textbox" : classObject.limit, "tooltip" : "Defines the number of events to collect before resuming"})
			formData.append({"type" : "checkbox", "schemaitem" : "enabled", "checked" : classObject.enabled})
			formData.append({"type" : "checkbox", "schemaitem" : "log", "checked" : classObject.log})
			formData.append({"type" : "input", "schemaitem" : "comment", "textbox" : classObject.comment})
			return formData

	def __init__(self):
		self.events = []

	def run(self,data,persistentData,actionResult):
		if "skip" in data:
			del data["skip"]
			actionResult["result"] = True
			actionResult["rc"] = 0
			return actionResult
		else:
			self.events.append(data["event"])
			if self.limit != 0 and self.limit < len(self.events):
				self.continueFlow(data,persistentData)

		# Returning false to stop flow continue
		actionResult["result"] = False
		actionResult["rc"] = 9
		return actionResult

	def continueFlow(self,data,persistentData):
		if self.events:
			tempDataCopy = conduct.copyFlowData(data)
			tempDataCopy["event"] = self.events
			tempDataCopy["skip"] = 1
			self.events = []
			tempDataCopy["eventStats"] = { "first" : True, "current" : 0, "total" : 1, "last" : True }
			persistentData["system"]["conduct"].triggerHandler(data["flowID"],tempDataCopy,flowIDType=True)

	def postRun(self,data,persistentData):
		self.continueFlow(data,persistentData)
