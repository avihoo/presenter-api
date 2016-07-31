# coding=utf-8
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')

import traceback
import sh
import re
import time

import logging.config
logging.config.fileConfig(os.path.dirname(os.path.abspath(__file__)) + '/../conf/logging.conf')

from flask import Flask
from flask import request
from flask import render_template_string
from flask import jsonify
import functools

import presenter.presents.presents_api as presents_api
from conf import configuration

app = Flask(__name__)
helpString = None
INVALID_CHARS = re.compile(u'[,!@%\^\*\(\)=\{\};~`â€™<>\?\\\|]')
HOST = "localhost"
PORT = configuration.PORT


def addStackTrace():
    stackTrace = []
    exc_type, exc_value, exc_traceback = sys.exc_info()
    st = traceback.extract_tb(exc_traceback)
    for stLine in st:
            traceLine = {}
            traceLine["fileName"] = str(stLine[0])
            traceLine["lineNumber"] = str(stLine[1])
            traceLine["methodName"] = str(stLine[2])
            stackTrace.append(traceLine)
    return stackTrace


def resultHanlder(required_args=[], required_headers=[]):
    def resultHanlderf(f):
        @functools.wraps(f)
        def f_resultHanlder(*args, **kwargs):
            if request.method == "POST" and "application/json" not in request.headers.get("content-type", "").lower():
                return "content-type must be application/json", 400, None
            for arg in required_args:
                if not request.args.get(arg):
                    return "The argument %s is required" % arg, 400, None
            for header in required_headers:
                if not request.headers.get(header):
                    return "The header %s is required" % header, 400, None
            returnValue = {}
            returnValue["meta"] = {}
            try:
                t0 = time.time()
                result, meta = f(*args, **kwargs)
                t0 = int((time.time() - t0) * 1000)
                returnValue.update({"data": result})
                returnValue["meta"].update(meta)
                returnValue["meta"]["took"] = t0
                returnValue["meta"]['httpCode'] = 200
                returnValue["meta"]['success'] = True
                return jsonify(**returnValue), 200, None
            except Exception, e:
                returnValue["meta"]['httpCode'] = 500
                returnValue["meta"]['success'] = False
                returnValue["error"] = {}
                returnValue["error"]["message"] = e.message.replace("[", "").replace("]", "")
                returnValue["error"]["stackTrace"] = addStackTrace()
                returnValue['error']['input'] = request.data
                return jsonify(**returnValue), 500, None
        return f_resultHanlder
    return resultHanlderf


def helpPage():
    title = "<h1>Presenter API is up!</h1><br>"
    version = "<h2>Presenter API version 0.1.0 </h2><br><br>"
    helpPage = str(sh.sed(sh.sed(sh.sed(sh.grep(sh.cat(os.path.dirname(os.path.realpath(__file__)) + '/server.py'), "app.route"), 's/@app.route(//'), 's/)//'), '1,2d'))
    helpPage = helpPage.replace("/<", "/[")
    helpPage = helpPage.replace(">'", "]'")
    helpPage = helpPage.replace(">/", "]/")
    helpPage = helpPage.replace("#", "<br>")
    helpPage = helpPage.replace("\n", "<br><br><br>")
    helpPage = helpPage.replace("HOST", HOST)
    helpPage = helpPage.replace("PORT", str(PORT))
    return title + version + helpPage


@app.route('/')
def help():
    return render_template_string(helpPage())


@app.route('/version', methods=['GET'])
def version():
    return "0.1.0"


@app.route('/presents', methods=['GET'])  # example - <a href=http://HOST:PORT/presents?keywords=iphone,galaxy,nexus&min_price=10&max_price=500>http://HOST:PORT/presents?keywords=iphone,galaxy,nexus&min_price=10&max_price=500</a>
@resultHanlder()
def get_presents():
    return presents_api.get_presents(request.args.to_dict())


@app.route('/health', methods=['GET'])
def health():
    return "OK"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=PORT, debug=True, use_reloader=False)
