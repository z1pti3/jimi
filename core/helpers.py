import os
import requests
from pathlib import Path
import re
import functools
import types
import traceback
import base64
import sys
import importlib
from types import ModuleType, FunctionType
from gc import get_referents
import json
import ast
import time
import datetime
from bson.objectid import ObjectId 
import hashlib
import inspect
import subprocess
from dateutil import relativedelta

import jimi

functionSafeList = jimi.function.systemFunctions

regexEvalString = re.compile("(\%\%([^%]*)\%\%)")
regexDict = re.compile("^([a-zA-Z]+)\[.*\]")
regexDictKeys = re.compile("(\[\"?([^\]\"]*)\"?\])")
regexFunction = re.compile("^([a-zA-Z0-9]*)\(.*\)")
regexFunctionOpen = re.compile("^([a-zA-Z0-9]*)\(.*")
regexCommor = re.compile(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")
regexInt = re.compile("^(-|)[0-9]+$")
regexFloat = re.compile("^(-|)[0-9]+\.[0-9]+$")
regexString = re.compile("^\".*\"$")

baseDir = os.getcwd()

systemProperties = ["classID","workerID","acl","scope","lastUpdateTime","creationTime","createdBy","attemptCount","autoRestartCount","clusterSet","systemID","startCheck","scope"]

class cpuSaver:
    loops = 0

    def __init__(self):
        self.cpuSaver = jimi.settings.cpuSaver 

    def tick(self,runAfter=0,sleepFor=0,ignoreEnabledState=False):
        if self.cpuSaver and ( self.cpuSaver["enabled"] or ignoreEnabledState ):
            sleep = False
            if runAfter > 0:
                if self.loops > runAfter:
                    sleep = True
            elif self.loops > self.cpuSaver["loopL"]:
                sleep = True
            if sleep:
                if sleepFor > 0:
                    time.sleep(sleepFor)
                else:
                    time.sleep(self.cpuSaver["loopT"])
                self.loops = 0
                return True
            self.loops+=1
        return False

# Return evaluated dictionary of list seperated varibles ['test','this is a test %data["event"]["tick"]%']
def defineVars(varDefinitions,dicts={},functionSafeList=functionSafeList):
    result = {}
    for varDefinition in varDefinitions:
        result[varDefinition[0]] = evalString(str(varDefinition[1]),dicts,functionSafeList)
    return result

def evalString(varString,dicts={},functionSafeList=functionSafeList):
    results = varString
    evalMatches = regexEvalString.findall(varString)
    if len(evalMatches) == 0:
        results = typeCast(varString)
    for evalMatch in evalMatches:
        if results is not None:
            results = typeCast(results.replace(evalMatch[0],str(typeCast(evalMatch[1],dicts,functionSafeList))))
    return results

def evalDict(varDict,dicts={},functionSafeList=functionSafeList):
    result = {}
    for key, value in varDict.items():
        newKey = evalString(key,dicts,functionSafeList)
        if type(value) is str:
            result[newKey] = evalString(varDict[key],dicts,functionSafeList)
        elif type(value) is dict:
            if newKey not in result:
                result[newKey] = evalDict(value,dicts,functionSafeList)
            else:
                result[newKey].update(evalDict(value,dicts,functionSafeList))
        elif type(value) is list:
            result[newKey] = evalList(value,dicts,functionSafeList)
        else:
            result[newKey] = varDict[key]
    return result

def evalList(varList,dicts={},functionSafeList=functionSafeList):
    result = []
    for item in varList:
        if type(item) is str:
            result.append(evalString(item,dicts,functionSafeList))
        elif type(item) is dict:
            result.append(evalDict(item,dicts,functionSafeList))
        else:
            result.append(item)
    return result

# Get dict values from string dict
def getDictValue(varString,dicts={}):
    def nested_dict_get(dictionary, keys):
        return functools.reduce(lambda d, key: d.get(key) if d else None, keys, dictionary)

    if regexDict.search(varString):
        dictName = varString.split("[")[0]
        if dictName in dicts:
            dictKeys = []
            for key in regexDictKeys.findall(varString):
                dictKeys.append(key[1])
            try:
                return typeCast(nested_dict_get(dicts[dictName],dictKeys))
            except AttributeError:
                try:
                    currentValue = dicts[dictName]
                    for key in dictKeys:
                        if type(currentValue) is dict:
                            currentValue = currentValue[key]
                        elif type(currentValue) is list:
                            currentValue = currentValue[int(key)]
                        else:
                            return None
                except:
                    return None
                return currentValue
    return None

# Type cast string into varible types, includes dict and function calls
def typeCast(varString,dicts={},functionSafeList=functionSafeList):
    if type(varString) == str and varString:
        # String defined
        if varString[0] == "\"" and varString[-1] == "\"":
            return str(varString[1:-1])
        # Int
        if regexInt.match(varString):
            return int(varString)
        # Float
        if regexFloat.match(varString):
            return float(varString)
        # Bool
        lower = varString.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False
        # None
        if lower == "none" or lower == "null":
            return None
        # Dict
        if regexDict.match(varString):
            return getDictValue(varString,dicts)
        # Attempt to cast dict and list
        if varString[0] == "{" or varString[0] == "[":
            try:
                return ast.literal_eval(varString)
            except:
                pass
        # Function
        if regexFunction.search(varString):
            functionName = varString.split("(")[0]
            if functionName in functionSafeList:
                functionValue = varString[(len(functionName)+1):-1]

                functionArgs = []

                tempArg = ""
                index = 0
                # Decoding string function arguments to single arguments for typeCasting - Regex maybe faster but has to handle encaspulation of " \" [ ' (, old search regex only worked with "
                while index <= len(functionValue)-1:
                    if functionValue[index] == "\"":
                        tempArg += functionValue[index]
                        index += 1
                        while index <= len(functionValue)-1:
                            if functionValue[index] != "\"":
                                tempArg += functionValue[index]
                                index += 1
                            else:
                                tempArg += functionValue[index]
                                if (functionValue[index-1] != "\\") or (functionValue[index-1] == "\\" and functionValue[index-2] == "\\"):
                                    tempArg = tempArg.replace("\\\\","\\")
                                    break
                                index += 1
                    elif functionValue[index] == "[":
                        while index <= len(functionValue)-1:
                            if functionValue[index] != "]":
                                tempArg += functionValue[index]
                                index += 1
                            else:
                                tempArg += functionValue[index]
                                index += 1
                                break
                    else:
                        functionFound = 0
                        inQuote = False
                        while index <= len(functionValue)-1:
                            if functionFound > 0:
                                if functionValue[index] == "\"":
                                    if functionValue[index-1] != "\\" and functionValue[index-2] != "\\":
                                        inQuote = not inQuote
                                if not inQuote: 
                                    if functionValue[index] == "(":
                                        functionFound += 1
                                    elif functionValue[index] == ")":
                                        functionFound -= 1
                                        if functionFound == 0:
                                            tempArg += functionValue[index]
                                            index += 1
                                            break
                                tempArg += functionValue[index]
                                index += 1
                            elif functionValue[index] == "(":
                                tempArg += functionValue[index]
                                index += 1
                                if regexFunctionOpen.search(tempArg):
                                    functionFound += 1
                            elif functionValue[index] != "," and functionValue[index] != ")":
                                tempArg += functionValue[index]
                                index += 1
                            else:
                                break
                    
                    if tempArg != "":
                        value = typeCast(tempArg.strip(),dicts,functionSafeList)
                        functionArgs.append(value)
                        tempArg = ""
                    index+=1

                # Catch any execution errors within functions
                try:
                    if len(functionArgs) > 0:
                        a = functionSafeList[functionName](*functionArgs)
                        return a
                    else:
                        return functionSafeList[functionName]()
                except Exception as e:
                    raise jimi.exceptions.functionCallFailure(functionName,''.join(traceback.format_exception(type(e), e, e.__traceback__)))
    # Default to exsiting
    return varString

def handelTypes(_object):
    # Handle none native json types
    if type(_object) is ObjectId:
        return str(_object)
    else:
        return _object

def jsonToClass(_class,json):
    members = [attr for attr in dir(_class) if not callable(getattr(_class, attr)) and not "__" in attr and attr ]
    for member in members:
        foundAndSet = False
        for key, value in json.items():
            if key == member:
                valueObject = handelTypes(value)
                if type(getattr(_class,member)) == type(valueObject):
                    setattr(_class,member,valueObject)
                    foundAndSet = True
                    break
                elif type(getattr(_class,member)) == str:
                    setattr(_class,member,str(valueObject))
                    foundAndSet = True
                    break
                elif type(getattr(_class,member)) == float and type(valueObject) == int:
                    setattr(_class,member,float(valueObject))
                    foundAndSet = True
                    break
                elif type(getattr(_class,member)) == int and type(valueObject) == float:
                    setattr(_class,member,int(valueObject))
                    foundAndSet = True
                    break
        if not foundAndSet:
            setattr(_class,member,type(getattr(_class,member))())
    return _class

def classToJson(_class,hidden=False):
    members = [attr for attr in dir(_class) if not callable(getattr(_class, attr)) and not "__" in attr and attr ]
    result = {}
    validTypes = [str,int,bool,float,list,dict]
    for member in members:
        if type(getattr(_class,member)) in validTypes:
            # Skips hidden values
            if not hidden:
                if member[0] != "_":
                    result[member] = handelTypes(getattr(_class,member))
            else:
                result[member] = handelTypes(getattr(_class,member))
        else:
            result[member] = str(type(getattr(_class,member)))
    return result


def dictToJson(json):
    def rebuildList(jsonList):
        rebuiltList = []
        standardTypes = [str,int,bool,float,list,None]
        for item in jsonList:
            if type(item) is dict:
                rebuiltList.append(dictToJson(item))
            elif type(item) is list:
                rebuiltList.append(rebuildList(item))
            elif type(item) in standardTypes:
                rebuiltList.append(item)
            else:
                rebuiltList.append(str(type(item)))
        return rebuiltList
    rebuiltJson = {}
    standardTypes = [str,int,bool,float,list,None]
    for key, value in json.items():
        if type(value) is dict:
            rebuiltJson[key] = dictToJson(value)
        elif type(value) is list:
            rebuiltJson[key] = rebuildList(value)
        elif type(value) in standardTypes:
            rebuiltJson[key] = value
        else:
            rebuiltJson[key] = str(type(value))
    return rebuiltJson

def listToJson(listObj):
    def rebuildList(jsonList):
        rebuiltList = []
        standardTypes = [str,int,bool,float,list,None]
        for item in jsonList:
            if type(item) is dict:
                rebuiltList.append(dictToJson(item))
            elif type(item) is list:
                rebuiltList += rebuildList(item)
            elif type(item) in standardTypes:
                rebuiltList.append(item)
            else:
                rebuiltList.append(str(type(item)))
        return rebuiltList
    rebuiltJson = rebuildList(listObj)
    return rebuiltJson

def unicodeEscapeDict(dictVar):
    resultItem = {}
    standardTypes = [str,int,bool,float,list,None]
    for key, value in dictVar.items():
        newKey = key.replace(".","\\u002E").replace("$","\\u0024")
        if type(value) is dict:
            resultItem[newKey] = unicodeEscapeDict(value)
        elif type(value) is list:
            newList = []
            for item in value:
                if type(item) is dict:
                    newList.append(unicodeEscapeDict(item))
                elif type(item) in standardTypes:
                    newList.append(item)
                else:
                    newList.append(str(item))
            resultItem[newKey] = newList
        elif type(value) in standardTypes:
            resultItem[newKey] = value
        else:
            resultItem[newKey] = str(value)
    return resultItem

def unicodeUnescapeDict(dictVar):
    resultItem = {}
    for key, value in dictVar.items():
        try:
            newKey = key.replace("\\u002E",".").replace("\\u0024","$")
        except AttributeError:
            pass
        if type(value) is dict:
            resultItem[newKey] = unicodeUnescapeDict(value)
        elif type(value) is list:
            newList = []
            for item in value:
                if type(item) is dict:
                    newList.append(unicodeUnescapeDict(item))
                else:
                    newList.append(item)
            resultItem[newKey] = newList
        else:
            resultItem[newKey] = value
    return resultItem

def unicodeUnescape(var):
    return var.replace("\\u002E",".").replace("\\u0024","$")

def locateModel(classType,modelType):
    # Check Core Model First
    try:
        mod = __import__("core.models.{0}".format(classType), fromlist=["_{0}".format(classType)])
        class_ = getattr(mod, "_{0}".format(classType))
        if class_ in modelType:
            return class_
    except ModuleNotFoundError:
        pass
    # Check Plugins Second
    plugins = os.listdir("plugins")
    # Look in all plugin folders
    for plugin in plugins:
        models = os.listdir(Path("plugins/{0}/models".format(plugin)))
        # Looking in all .py files within models dir
        for model in models:
            if len(model) > 3:
                if model[-3:] == ".py":
                    # Bruteforce attempt to load classType within model file
                    try:
                        mod = __import__("plugins.{0}.models.{1}".format(plugin,model[:-3]), fromlist=["_{0}".format(classType)])
                        class_ = getattr(mod, "_{0}".format(classType))
                        # Check that loaded class base ( parent class ) is within supplied ( expected ) modelType
                        if class_.__bases__[0] in modelType:
                            return class_
                    except ModuleNotFoundError:
                        pass
                    except AttributeError:
                        pass
    return None

# Reloads all loaded modules - NOT WORKING!
def reload():
    import sys
    import importlib
    for mod in sys.modules:
        try:
            for moduleItem in mod.__dict__.items():
                if len(moduleItem) == 2:
                    if type(moduleItem[1]) is types.ModuleType:
                        importlib.reload(moduleItem[1])
        except:
            pass

apiURL = "http://{0}:{1}/{2}".format(jimi.config["system"]["accessAddress"],jimi.config["system"]["accessPort"],jimi.config["api"]["base"])
def apiCall(methord,apiEndpoint,jsonData=None,token=None,overrideURL=None,timeout=2,overrideAPIBase=None):
    if overrideURL != None:
        if overrideAPIBase != None:
            url = "{0}/{1}/{2}".format(overrideURL,overrideAPIBase,apiEndpoint)
        else:
            url = "{0}/{1}/{2}".format(overrideURL,jimi.config["api"]["base"],apiEndpoint)                   
    else:
        url = "{0}/{1}".format(apiURL,apiEndpoint)

    headers = {}
    if token:
        headers["x-api-token"] = token
    response = None
    try:
        if methord == "GET":
            response = requests.get(url,proxies=jimi.config["api"]["proxy"],headers=headers,allow_redirects=False,timeout=timeout)
        elif methord == "POST":
            response = requests.post(url,json=jsonData,proxies=jimi.config["api"]["proxy"],headers=headers,allow_redirects=False,timeout=timeout)
        elif methord == "PUT":
            response = requests.put(url,json=jsonData,proxies=jimi.config["api"]["proxy"],headers=headers,allow_redirects=False,timeout=timeout)
        elif methord == "DELETE":
            response = requests.delete(url,proxies=jimi.config["api"]["proxy"],headers=headers,allow_redirects=False,timeout=timeout)
    except Exception as e:
        pass
    return response

def isBase64(s):
    if len(s) == 88 and s[-2:] == "==":
        try:
            enc = base64.b64encode(base64.b64decode(s)).decode()
            return enc == s
        except base64.binascii.Error:
            pass
    return False

def getObjectMemoryUsage(obj):
    BLACKLIST = type, ModuleType, FunctionType
    """sum size of object & members."""
    if isinstance(obj, BLACKLIST):
        raise TypeError('getsize() does not take argument of type: '+ str(type(obj)))
    seen_ids = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, BLACKLIST) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = get_referents(*need_referents)
    return size

def lower_dict(d):
    new_dict = dict((k.lower(), v) for k, v in d.items())
    return new_dict

def dictValue(d,value):
    try:
        return d[value]
    except:
        return None
 
def roundTime(dt=None, roundTo=60):
   if dt == None : dt = datetime.datetime.now()
   seconds = (dt.replace(tzinfo=None) - dt.min).seconds
   rounding = (seconds+roundTo/2) // roundTo * roundTo
   return dt + datetime.timedelta(0,rounding-seconds,-dt.microsecond)

def getFileHash(filename,insecure=False):
    sha256_hash = hashlib.sha256()
    if insecure:
        maxBytes = jimi.settings.getSetting("storage","maxBytesChecked")
        counter = 0
        with open(filename, "rb") as f:
            for byte_block in iter(lambda: f.read(4096),b""):
                sha256_hash.update(byte_block)
                counter += 4096
                if counter > maxBytes:
                    sha256_hash.update(f"{filename}-{os.path.getsize(filename)}".encode("utf-8"))
                    break
    else:
        with open(filename, "rb") as f:
            for byte_block in iter(lambda: f.read(4096),b""):
                sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def getStringHash(string):
    return hashlib.sha256(string.encode('utf-8')).hexdigest()

def safeFilepath(filename,basePath=""):
    base = os.path.join(Path("{0}/{1}".format(baseDir,basePath)),'')
    return not os.path.commonprefix((os.path.abspath(Path(filename)),base)) != base

def reloadModulesWithinPath(moduleName):
    modules = []
    for key, module in sys.modules.items():
        if moduleName in module.__name__:
            modules.append(module)
    for module in modules:
        importlib.reload(module)

def splitList(list,amount=1):
    if amount < 1:
        amount = 1
    try:
        return [list[i * amount:(i + 1) * amount] for i in range((len(list) + amount - 1) // amount )]
    except:
        return list

# To be removed in a future release after plugins stop using it
def replaceBackspaces(string):
    return string.replace("\b","")

def getDateFromTimestamp(timestamp):
    ts = datetime.datetime.fromtimestamp(timestamp)
    return ts.strftime("%d-%m-%Y %H:%M:%S")

def generateRSAKeys():
    subprocess.run(["openssl","genrsa","-out",str(Path("data/temp/private.pem")),"2048"])
    subprocess.run(["openssl","rsa","-in",str(Path("data/temp/private.pem")),"-outform","PEM", "-pubout","-out",str(Path("data/temp/sessionPub.pem"))])
    subprocess.run(["openssl","rsa","-in",str(Path("data/temp/private.pem")),"-out",str(Path("data/temp/sessionPriv.pem")), "-outform","PEM"])
    with open(str(Path("data/temp/sessionPub.pem"))) as f:
        sessionPublicKey = f.read()
    with open(str(Path("data/temp/sessionPriv.pem"))) as f:
        sessionPrivateKey = f.read()
    os.remove(Path("data/temp/sessionPub.pem"))
    os.remove(Path("data/temp/sessionPriv.pem"))
    os.remove(Path("data/temp/private.pem"))
    return sessionPublicKey, sessionPrivateKey

def getCentreOffset(flowData,newCentre):
    x = [x["x"] for x in flowData]
    y = [x["y"] for x in flowData]
    centroid = (sum(x) / len(flowData), sum(y) / len(flowData))
    for node in flowData:
        node["x"] -= centroid[0] - newCentre["x"]
        node["y"] -= centroid[1] - newCentre["y"]
    return flowData

def getSearchPeriodTimestamp(searchStart,searchEnd):
    searchStartMatch = re.match(r"([0-9]+)([A-z]+)",searchStart)
    if searchStartMatch:
        if searchStartMatch.groups()[1] in ["millisecond", "milliseconds", "millis", "ms"]:
            startTime = datetime.datetime.now() - datetime.timedelta(milliseconds=int(searchStartMatch.groups()[0]))
        elif searchStartMatch.groups()[1] in ["second", "seconds", "s", "sec", "secs"]:
            startTime = datetime.datetime.now() - datetime.timedelta(seconds=int(searchStartMatch.groups()[0]))
        elif searchStartMatch.groups()[1] in ["minute", "minutes", "m", "min"]:
            startTime = datetime.datetime.now() - datetime.timedelta(minutes=int(searchStartMatch.groups()[0]))
        elif searchStartMatch.groups()[1] in ["hour", "hours", "h", "hr", "hrs"]:
            startTime = datetime.datetime.now() - datetime.timedelta(hours=int(searchStartMatch.groups()[0]))
        elif searchStartMatch.groups()[1] in ["day", "days", "d"]:
            startTime = datetime.datetime.now() - datetime.timedelta(days=int(searchStartMatch.groups()[0]))
        elif searchStartMatch.groups()[1] in ["week", "weeks", "w"]:
            startTime = datetime.datetime.now() - datetime.timedelta(weeks=int(searchStartMatch.groups()[0]))
        elif searchStartMatch.groups()[1] in ["month", "months", "mon"]:
            startTime = datetime.datetime.now() - relativedelta.relativedelta(months=int(searchStartMatch.groups()[0]))
        elif searchStartMatch.groups()[1] in ["year", "years", "y", "yr", "yrs"]:
            startTime = datetime.datetime.now() - relativedelta.relativedelta(years=int(searchStartMatch.groups()[0]))

    if searchEnd:
        searchEndMatch = re.match(r"([0-9]+)([A-z]+)",searchEnd)
        if searchEndMatch:
            if searchEndMatch.groups()[1] in ["millisecond", "milliseconds", "millis", "ms"]:
                endTime = datetime.datetime.now() - datetime.timedelta(milliseconds=int(searchEndMatch.groups()[0]))
            elif searchEndMatch.groups()[1] in ["second", "seconds", "s", "sec", "secs"]:
                endTime = datetime.datetime.now() - datetime.timedelta(seconds=int(searchEndMatch.groups()[0]))
            elif searchEndMatch.groups()[1] in ["minute", "minutes", "m", "min"]:
                endTime = datetime.datetime.now() - datetime.timedelta(minutes=int(searchEndMatch.groups()[0]))
            elif searchEndMatch.groups()[1] in ["hour", "hours", "h", "hr", "hrs"]:
                endTime = datetime.datetime.now() - datetime.timedelta(hours=int(searchEndMatch.groups()[0]))
            elif searchEndMatch.groups()[1] in ["day", "days", "d"]:
                endTime = datetime.datetime.now() - datetime.timedelta(days=int(searchEndMatch.groups()[0]))
            elif searchEndMatch.groups()[1] in ["week", "weeks", "w"]:
                endTime = datetime.datetime.now() - datetime.timedelta(weeks=int(searchEndMatch.groups()[0]))
            elif searchEndMatch.groups()[1] in ["month", "months", "mon"]:
                endTime = datetime.datetime.now() - relativedelta.relativedelta(months=int(searchEndMatch.groups()[0]))
            elif searchEndMatch.groups()[1] in ["year", "years", "y", "yr", "yrs"]:
                endTime = datetime.datetime.now() - relativedelta.relativedelta(years=int(searchEndMatch.groups()[0]))

        return startTime, endTime
    return startTime, datetime.datetime.now()
