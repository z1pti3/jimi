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
			self.data["persistentData"]["system"]["conduct"].triggerHandler(self.data["flowData"]["flowID"],tempDataCopy,flowIDType=True)

	def postRun(self):
		self.continueFlow()
