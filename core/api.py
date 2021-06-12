from os import wait
import waitress
from flask import Flask, request, make_response, redirect, g, send_file
import _thread

base = "/api/1.0/"
webServer = None

def createServer(name, **kwargs):
	global webServer
	webServer = Flask(name,**kwargs)

def startServer(threaded,**kwargs):
	global webServer
	if threaded:
		_thread.start_new_thread(waitress.serve, (webServer,), kwargs)
	else:
		waitress.serve(webServer,**kwargs)
