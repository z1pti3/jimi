import time

from core.models import action, conduct, webui

class _sleep(action._action):
	sleepFor = int()

	# class _properties(webui._properties):
	# 	def generate(self,classObject):
	# 		formData = []
	# 		formData.append({"type" : "input", "schemaitem" : "_id", "textbox" : classObject._id})
	# 		formData.append({"type" : "input", "schemaitem" : "name", "textbox" : classObject.name})
	# 		formData.append({"type" : "input", "schemaitem" : "sleepFor", "textbox" : classObject.sleepFor, "tooltip" : "Defines in seconds how long to sleep"})
	# 		formData.append({"type" : "checkbox", "schemaitem" : "enabled", "checked" : classObject.enabled})
	# 		formData.append({"type" : "checkbox", "schemaitem" : "log", "checked" : classObject.log})
	# 		formData.append({"type" : "input", "schemaitem" : "comment", "textbox" : classObject.comment})
	# 		return formData

	def run(self,data,persistentData,actionResult):
		time.sleep(self.sleepFor)
		actionResult["result"] = True
		actionResult["rc"] = 0
		return actionResult
