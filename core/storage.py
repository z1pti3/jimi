from core import db

class _storage(db._document):
    fileData = str()
    source = str()

    _dbCollection = db.db["storage"]

    def new(self,acl,source,fileData):
        self.source = source
        self.fileData = fileData
        self.acl = acl
        return super(_storage, self).new()
