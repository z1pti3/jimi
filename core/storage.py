from core import db

class _storage(db._document):
    fileData = str()

    _dbCollection = db.db["storage"]

    def new(self,acl,fileData):
        self.fileData = fileData
        self.acl = acl
        return super(_storage, self).new()
