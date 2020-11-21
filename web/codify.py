import time
import json
import  uuid

from flask import Flask, request, render_template, make_response, redirect

from core import api, model, db, cache, helpers

from core.models import trigger, action, conduct, webui

@api.webServer.route("/codify/", methods=["GET"])
def codify():
    return render_template("codify.html", CSRF=api.g.sessionData["CSRF"])


@api.webServer.route("/codify/", methods=["POST"])
def codifyRun():
    data = json.loads(api.request.data)
    data["sessionData"] = api.g.sessionData
    apiEndpoint = "codify/run/"
    timeout = 60
    if "timeout" in data:
        timeout = int(data["timeout"])
        del data["timeout"]
    try:
        apiContent = helpers.apiCall("POST",apiEndpoint,jsonData=data,token=api.g.sessionToken,timeout=timeout).text
    except:
        return { "result" : "An error happend - Maybe the flow has taken too long to respond for codify?" }, 200
    return json.loads(apiContent), 200
