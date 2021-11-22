import html
import random
from json2html import *

class chartjs():

    def __init__(self):
        self.labels = []
        self.datasets = {}

    def addLabel(self,name):
        self.labels.append(name)

    def addLabels(self,names):
        self.labels.extend(names)

    def removeLabel(self,name):
        self.labels.remove(name)

    def addDataset(self,name,data):
        color = randomColor()
        self.datasets[name] = {
            "label" : name,
            "data" : data
        }

    def removeDataset(self,name):
        del self.datasets[name]

    def setDatasetData(self,name,data):
        self.datasets[name]["data"] = data

    def generate(self,data=None):
        result = { "labels" : [], "datasets" : [], "updates" : [], "deletes" : [] }
        if data:
            datasets = self.datasets
            if self.labels != data["labels"]:
                result["labels"] = self.labels
            for index, value in enumerate(data["datasets"]):
                if value["label"] not in datasets:
                    result["deletes"].append({ "index" : index })
                else:
                    if value["data"] != datasets[value["label"]]["data"]:
                        result["updates"].append({ "index" : index, "data" : datasets[value["label"]]["data"] })
                    del datasets[value["label"]]
            result["datasets"] = [ datasets[x] for x in datasets ]
        else:
            result["labels"] = self.lables
            result["datasets"] = [ self.datasets[x] for x in self.datasets ]
        return result

class radar(chartjs):

    def addDataset(self,name,data):
        color = randomColor()
        self.datasets[name] = {
            "label" : name,
            "data" : data,
            "fill" : True,
            "backgroundColor": color,
            "borderColor": color,
            "pointBackgroundColor": color
        }

class doughnut(chartjs):
    
    def addDataset(self,name,data):
        colors = []
        for x in range(0,len(data)):
            colors.append(randomColor())
        self.datasets[name] = {
            "label" : name,
            "data" : data,
            "backgroundColor": colors
        }

class pie(chartjs):
    
    def addDataset(self,name,data):
        colors = []
        for x in range(0,len(data)):
            colors.append(randomColor())
        self.datasets[name] = {
            "label" : name,
            "data" : data,
            "backgroundColor": colors
        }

class bar(chartjs):
    
    def addDataset(self,name,data):
        color = randomColor()
        self.datasets[name] = {
            "label" : name,
            "data" : data,
            "backgroundColor": [color]
        }

class line(chartjs):
    
    def addDataset(self,name,data):
        color = randomColor()
        self.datasets[name] = {
            "label" : name,
            "data" : data,
            "backgroundColor": [color],
            "borderColor" : color
        }

class table():

    def __init__(self,columns,pageSize=200,totalRows=0):
        self.columns = []
        for column in columns:
            self.columns.append({ "name" : column, "title" : column })
        self.totalRows = totalRows
        self.pageSize = pageSize

    def getColumns(self):
        return { "columns" : self.columns }

    def setRows(self,rows,links=[],buttons=[]):
        self.data = []
        for row in rows:
            rowData = []
            for column in self.columns:
                hyperLink = None
                buttonData = None
                for link in links:
                    if link["field"] == column["name"]:
                        hyperLink = link["url"]
                        if "fieldValue" in link:
                            hyperLinkValue = row[link["fieldValue"]]
                        else:
                            hyperLinkValue = ""
                for button in buttons:
                    if button["field"] == column["name"]:
                        buttonData = {"action": button["action"], "icon": button["icon"], "text": button["text"]}
                try:
                    value = safe(row[column["name"]])
                except KeyError:
                    value = ""
                if type(value) is dict or type(value) is list:
                    value = json2html.convert(json=value)
                if hyperLink:
                    value = "<a href=\"{0}{1}/\">{2}</a>".format(hyperLink,hyperLinkValue,value)
                if buttonData:
                    value = "<button class=\"btn btn-primary button {0}\" onClick=\"{1}\"> {2}</button>".format(buttonData["icon"],buttonData["action"],buttonData["text"])
                rowData.append(value)
            self.data.append(rowData)

    def generate(self,draw):
        return { "draw" : draw, "recordsTable" : self.pageSize, "recordsFiltered" : self.totalRows, "recordsTotal" : self.totalRows, "data" : self.data }

def randomColor():
    r = random.randint(0,255)
    g = random.randint(0,255)
    b = random.randint(0,255)
    color = f"rgba({r}, {g}, {b}, 0.5)"
    return color

def safe(value):
    if type(value) is str:
        return html.escape(value)
    elif type(value) is dict:
        result = {}
        for k, v in value.items():
            result[k] = safe(v)
        return result
    elif type(value) is list:
        result = []
        for v in value:
            result.append(safe(v))
        return result
    else:
        return html.escape(str(value))

def dictTable(dictData):
    table_attributes = "class=\"dictTable\""
    return json2html.convert(safe(dictData),table_attributes=table_attributes)
