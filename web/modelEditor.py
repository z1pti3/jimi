from flask import Flask, request, render_template, make_response, redirect, send_file, flash

from core import api, model

@api.webServer.route("/model/", methods=["GET"])
def modelEditorMainPage():
    return render_template("modelEditorList.html")
