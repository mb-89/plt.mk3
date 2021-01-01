from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtUiTools import QUiLoader
import os.path as op
from jsmin import jsmin
import json
import plugins
import importlib
import inspect
from functools import partial
import traceback

class App(QtWidgets.QApplication):
    cmdDone = QtCore.Signal()
    def __init__(self):
        super().__init__([])

        appinfotxt = open(op.join(op.dirname(__file__),"..","..","APPINFO.jsonc"),"r").read()
        self.info = json.loads(jsmin(appinfotxt))
        self.started = False

        self.gui = QUiLoader().load(op.join(op.dirname(__file__),"app.ui"), None)
        self.gui.setWindowTitle(self.info["name"])
        self.log = None
        self.args = []
        self.cmdbacklog = []
        self.cmdDone.connect(lambda:self.execNextCmd(notBusyAnymore=True))
        self.cmdbusy = False

        self.plugins = {}
        self.publicfuns = {}
        for p in ["log", "cmd"]+self.info.get("plugins",[]):
            plugin = importlib.import_module("plugins."+p).Plugin(self)
            self.plugins[p] = plugin
            publicfuns = inspect.getmembers(plugin, lambda x: hasattr(x,"__dict__") and "__is_public_fun__" in x.__dict__)

            for name,pf in publicfuns:
                #self.log.info(f"found public fun {name} in {p}")
                sc = FunShortcut(self, p,name,pf)
                self.publicfuns[sc.name] = sc

        self.aboutToQuit.connect(self.stop)

    def start(self, args):
        if self.started: return
        self.args = args
        self.started = True
        self.gui.show()
        for p in self.plugins.values(): p.start()
        for idx,cmd in enumerate(args["cmds"]):
            p = partial(self.plugins["cmd"].parse, cmd)
            QtCore.QTimer.singleShot(idx,p)
        self.exec_()

    def stop(self):
        if not self.started: return
        self.started = False
        for p in self.plugins.values(): p.stop()
        self.quit()

    def __del__(self):
        self.stop()

    def execNextCmd(self, notBusyAnymore = False):
        if notBusyAnymore or self.args["nomultithread"]: self.cmdbusy = False
        if self.cmdbusy:return
        self.cmdbusy = True
        if not self.cmdbacklog: return
        cmd = self.cmdbacklog.pop(0)
        cmd()

class FunShortcut(QtCore.QObject):
    def __init__(self, app, plugin, name, fn):
        super().__init__()
        self.app = app
        self.shortcut = fn.__dict__["__public_fun_shortcut__"]
        self.fn = fn
        self.argstr = ""
        self.name = f"{plugin}.{name}"
        self.action = QtWidgets.QAction(app)
        self.action.setText(self.name)
        self.action.setToolTip("TBD")
        if self.shortcut:self.action.setShortcut(self.shortcut)
        self.action.triggered.connect(self.execute)
        app.gui.addAction(self.action)

    def trigger(self,argstr):
        self.argstr = argstr
        self.action.trigger()

    def execute(self):
        try:
            if self.argstr:
                argstr = self.argstr
                self.argstr = ""
                self.fn(argstr)
            else:
                self.fn()
        except Exception as e:
            tb = traceback.format_exc().split("\n")
            for x in tb:
                self.app.log.error(x)

    def getDescr(self):
        descr = inspect.getdoc(self.fn)
        if not descr: descr = "descr n/a"
        return descr