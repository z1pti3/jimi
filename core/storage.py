import jimi

class _storage(jimi.db._document):
    fileData = str()
    source = str()

    _dbCollection = jimi.db.db["storage"]

    def new(self,acl,source,fileData):
        self.source = source
        self.fileData = fileData
        self.acl = acl
        return super(_storage, self).new()
