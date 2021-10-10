from pathlib import Path
import csv
import json

import jimi

class _storageTrigger(jimi.trigger._trigger):
    storage_id = str()
    file_type = "csv"

    def doCheck(self):
        self.result = { "events" : [], "var" : {}, "plugin" : {} }
        storageFile = jimi.storage._storage().getAsClass(id=self.storage_id)
        try:
            storageFile = storageFile[0]
            with open(Path(storageFile.getLocalFilePath()),'r') as f:
                if self.file_type == "csv":
                    self.result["events"] = list(csv.DictReader(f))
                elif self.file_type == "json":
                    self.result["events"] = json.load(f)
                elif self.file_type == "txt":
                    self.result["events"] = f.readlines()
        except:
            pass
        return self.result["events"]
