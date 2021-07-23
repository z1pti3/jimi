import cherrypy
from flask import Flask, request, make_response, redirect, g, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
import _thread

base = "/api/1.0/"
webServer = None

def createServer(name, **kwargs):
	global webServer
	webServer = Flask(name,**kwargs)
	webServer.wsgi_app = ProxyFix(webServer.wsgi_app)

def startServer(threaded,webserverArguments):
	global webServer
	cherrypy.tree.graft(webServer.wsgi_app, '/')
	cherrypy.config.update(webserverArguments)
	if threaded:
		_thread.start_new_thread(cherrypy.engine.start, ())
	else:
		cherrypy.engine.start()
