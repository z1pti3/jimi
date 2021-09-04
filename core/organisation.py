import jimi

class _organisation(jimi.db._document):
	name = str()
	
	_dbCollection = jimi.db.db["organisations"]

	def new(self,name,values):
		self.name = name
		self.acl = { "ids":[ { "accessID":"0","delete": True,"read": True,"write": True } ] } 
		return super(_organisation, self).new()
