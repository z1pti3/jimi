from flask import Flask, request, render_template, make_response, redirect, send_file, flash

import jimi

@jimi.api.webServer.route("/model/", methods=["GET"])
def modelEditorMainPage():
    return render_template("modelEditorList.html", CSRF=jimi.api.g.sessionData["CSRF"])
