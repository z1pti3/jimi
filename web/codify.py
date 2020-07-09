import time
import json
import  uuid

from flask import Flask, request, render_template, make_response, redirect

from core import api, model, db, cache, helpers

from core.models import trigger, action, conduct, webui

@api.webServer.route("/codify/", methods=["GET"])
def codify():
    if api.g.sessionData:
        if "admin" in api.g.sessionData:
            if api.g.sessionData["admin"]:
                return render_template("codify.html", CSRF=api.g.sessionData["CSRF"])


@api.webServer.route("/codify/", methods=["POST"])
def codifyRun():
    if api.g.sessionData:
        if "admin" in api.g.sessionData:
            if api.g.sessionData["admin"]:
                data = json.loads(api.request.data)
                apiEndpoint = "codify/run/"
                apiContent = helpers.apiCall("POST",apiEndpoint,jsonData=data,token=api.g.sessionToken).text
                return json.loads(apiContent), 200
    return {"result": " "}, 200
