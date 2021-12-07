from flask import Flask, request, render_template, make_response, redirect, send_file, flash

import jimi
from web import ui

@jimi.api.webServer.route("/modelEditor/", methods=["GET"])
def modelEditorMainPage():
    return render_template("modelEditorList.html", CSRF=jimi.api.g.sessionData["CSRF"])

@jimi.api.webServer.route("/modelEditor/pollTableListModel/<modelType>/<action>/",methods=["GET"])
def tableListModel(modelType,action):
    fields = [ "_id", "name", "lastUpdateTime", "_id" ]
    searchValue = jimi.api.request.args.get('search[value]')
    orderBy = int(jimi.api.request.args.get('order[0][column]'))
    orderDir = jimi.api.request.args.get('order[0][dir]')
    if orderDir == "desc":
        orderDir = -1
    else:
        orderDir = 1
    searchFilter = {}
    if searchValue:
        try:
            searchFilter = { "_id" : jimi.db.ObjectId(searchValue) }
        except:
            searchFilter = { "$or" : [ 
                    { "name" : { "$regex" : ".*{0}.*".format(searchValue), "$options":"i" } },
                    { "comment" : { "$regex" : ".*{0}.*".format(searchValue), "$options":"i" } }
                ] }
    else:
        searchFilter = {}
    class_ = jimi.model.loadModel(modelType)
    if class_:
        access = jimi.db.ACLAccess(jimi.api.g.sessionData,class_.acl,"read")
        if access:
            pagedData = jimi.db._paged(class_.classObject(),sessionData=jimi.api.g.sessionData,fields=fields,query=searchFilter,maxResults=200,sort=[(fields[orderBy],orderDir)])
            table = ui.table(fields,pagedData.total,pagedData.total)
            if action == "build":
                return table.getColumns() ,200
            elif action == "poll":
                start = int(jimi.api.request.args.get('start'))
                data = pagedData.getOffset(start,queryMode=1)
                table.setRows(data)
                return table.generate(int(jimi.api.request.args.get('draw'))) ,200
