import os
import sys
import json
from pathlib import Path

pluginName = sys.argv[1]
pluginPath = sys.argv[2]

print("Starting")
print("pluginName = {0}".format(pluginName))
print("pluginPath = {0}".format(pluginPath))
print("")

def scan(path):
    def extractFunction(defLine):
        if "(" in defLine and ")" in defLine:
            defType = defLine.split("(")[1].split(")")[0]
            defName = defLine.split("(")[0].split(" ")[1]
            return defName, defType
        return defLine.split(" ")[1].split(":")[0], ""
    def extractVariables(variableLines):
        vars = []
        for variableLine in variableLines:
            if "=" in variableLine:
                vars.append([variableLine.split("=")[0].strip(),variableLine.split("=")[1].strip()])
        return vars
    modules = {}
    for path, subdirs, files in os.walk(Path(path)):
        for name in files:
            fullname = os.path.join(path, name)
            if fullname.endswith(".py"):
                with open(fullname, "r") as f:
                    content = f.read()
                classes = []
                withinClass = False
                classBuffer = []
                for line in content.split("\n"):
                    if not withinClass:
                        if line.startswith("class"):
                            withinClass = True
                            classBuffer.append(line)
                    else:
                        if not line.startswith("\t") and not line.startswith(" "):
                            withinClass = False
                            if classBuffer:
                                classes.append(classBuffer)
                            classBuffer = []
                        else:
                            classBuffer.append(line.strip())
                for c in classes:
                    defName, defType = extractFunction(c[0])
                    if defType not in modules:
                        modules[defType] = {}
                    vars = extractVariables(c[1:])
                    try:
                        modulePath = "{0}.{1}".format(path.split(pluginPath)[1].replace("/",".").replace("\\","."),name.split(".py")[0])
                        modules[defType][defName] =  { "path" : modulePath, "vars" : vars }
                    except:
                        pass
    return modules

def hasManifest(name,path):
    return os.path.isfile(Path("{0}/{1}.json".format(path,name)))

def loadManifest(name,path):
    manifest = ""
    with open(Path("{0}/{1}.json".format(path,name)), "r") as f:
        manifest = f.read()
    return json.loads(manifest)

def writeManifest(name,path,manifest):
    with open(Path("{0}/{1}.json".format(path,name)), "w") as f:
        f.write(json.dumps(manifest,indent=3))

print("[] Scanning Plugin Path", end="\r")
modules = scan(pluginPath)
print("[X] Scanning Plugin Path")
print("[] Checking Manifest", end="\r")
if hasManifest(pluginName,pluginPath):
    print("[X] Checking Manifest - Using existing")
    manifest = loadManifest(pluginName,pluginPath)
else:
    print("[X] Checking Manifest - Creating new")
    manifest = {
        "name" : pluginName.lower(),
        "author" : "",
        "version" : 0.0,
        "categories" : [],
        "description" : "",
        "icon" : None,
        "requirements" : {
            "jimi_min_version" : None,
            "jimi_max_version" : None,
            "plugins" : []
        },
        "collections" : { },
        "triggers" : { },
        "actions" : { },
        "settings" : { }
    }

print("[] Updating Manifest", end="\r")
for classType in modules:
    for module in modules[classType]:
        if f"_{pluginName}" == module and classType == "plugin._plugin":
            for field in modules[classType][module]["vars"]:
                if field[0] == "version":
                    manifest["version"] = float(field[1])
        objectType = ""
        if classType.endswith("db._document"):
            objectType = "collections"
        elif classType.endswith("trigger._trigger"):
            objectType = "triggers"
        elif classType.endswith("action._action"):
            objectType = "actions"
        if objectType:
            objectName = module
            if objectName.startswith("_"):
                objectName = objectName[1:]
            if objectName not in manifest[objectType]:
                fields = []
                for field in modules[classType][module]["vars"]:
                    inputType = "input"
                    if field[1] == "bool()":
                        inputType = "checkbox"
                    elif field[1] == "list()" or field[1] == "dict()":
                        inputType = "json-input"
                    fields.append({
                        "schema_item" : field[0], 
                        "schema_value" : field[0], 
                        "type" : inputType, 
                        "label" : field[0], 
                        "description" : ""
                    })

                manifest[objectType][objectName] = {
                    "display_name" : objectName,
                    "className" : module,
                    "class_location" : modules[classType][module]["path"],
                    "description" : "",
                    "fields" : fields,
                    "data_out" : {
                        "result" : { 
                            "description" : "Returns True when successful.",
                            "type" : "boolean",
                            "always_present" : True,
                            "values" : {
                                "True" : { "description" : "Successful." },
                                "False" : { "description" : "Failure." }
                            }
                        },
                        "rc" : {
                            "description" : "Returns the exit code for the action.",
                            "type" : "number",
                            "always_present" : True,
                            "values" : {
                                "0" : { "description" : "Successful." }
                            }
                        }
                    }
                }
print("[X] Updating Manifest")

print("[] Writing Manifest", end="\r")
writeManifest(pluginName,pluginPath,manifest)
print("[X] Writing Manifest")
print("Done")