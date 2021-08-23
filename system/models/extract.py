import re

import jimi

class _extract(jimi.action._action):
	regex_pattern = str()
	string = str()

	def doAction(self,data):
		regex_pattern = jimi.helpers.evalString(self.regex_pattern,{"data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"] })
		string = jimi.helpers.evalString(self.string,{"data" : data["flowData"], "eventData" : data["eventData"], "conductData" : data["conductData"], "persistentData" : data["persistentData"] })
		matches = re.finditer(regex_pattern,string, re.MULTILINE)
		results = []
		for matchNum, match in enumerate(matches, start=1):
			results.append(match.groupdict())
		return { "result" : True, "rc" : 0, "extracts" : results }
