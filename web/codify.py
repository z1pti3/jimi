import time
import json
import  uuid
from flask import Flask, request, render_template, make_response, redirect

import jimi

@jimi.api.webServer.route("/codify/", methods=["GET"])
def codify():
    return render_template("codify.html", CSRF=jimi.api.g.sessionData["CSRF"])


@jimi.api.webServer.route("/codify/", methods=["POST"])
def codifyRun():
    data = json.loads(jimi.api.request.data)
    data["sessionData"] = jimi.api.g.sessionData
    apiEndpoint = "codify/run/"
    timeout = 60
    if "timeout" in data:
        timeout = int(data["timeout"])
    try:
        apiContent = jimi.helpers.apiCall("POST",apiEndpoint,jsonData=data,token=jimi.api.g.sessionToken,timeout=timeout).text
    except:
        return { "result" : "An error happend - Maybe the flow has taken too long to respond for codify?" }, 200
    return json.loads(apiContent), 200
