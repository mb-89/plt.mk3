from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtUiTools import QUiLoader
import os.path as op
from jsmin import jsmin
import json
import plugins
import importlib
import inspect

class App(QtWidgets.QApplication):
    def __init__(self):
        super().__init__([])

        appinfotxt = open(op.join(op.dirname(__file__),"..","..","APPINFO.jsonc"),"r").read()
        self.info = json.loads(jsmin(appinfotxt))
        self.started = False

        self.gui = QUiLoader().load(op.join(op.dirname(__file__),"app.ui"), None)
        self.gui.setWindowTitle(self.info["name"])
        self.log = None
        self.args = []

        self.plugins = {}
        self.shortcuts = {}
        for p in ["log"]+self.info.get("plugins",[]):
            plugin = importlib.import_module("plugins."+p).Plugin(self)
            self.plugins[p] = plugin
            publicfuns = inspect.getmembers(plugin, lambda x: hasattr(x,"__dict__") and "__is_public_fun__" in x.__dict__)

            for name,pf in publicfuns:
                self.log.info(f"found public fun {name} in {p}")
                shortcut = pf.__dict__["__public_fun_shortcut__"]
                if shortcut: self.shortcuts[shortcut] = FunShortcut(self, p,name,shortcut,pf)

        self.aboutToQuit.connect(self.stop)

    def start(self, args):
        if self.started: return
        self.args = args
        self.started = True
        self.gui.show()
        for p in self.plugins.values(): p.start()
        self.exec_()

    def stop(self):
        if not self.started: return
        self.started = False
        for p in self.plugins.values(): p.stop()
        self.quit()

    def __del__(self):
        self.stop()

class FunShortcut(QtCore.QObject):
    def __init__(self, app, plugin, name, shortcut, fn):
        super().__init__()
        self.app = app
        self.shortcut = shortcut
        self.fn = fn
        self.action = QtWidgets.QAction(app)
        self.action.setText(f"{plugin}.{name}")
        self.action.setToolTip("TBD")
        self.action.setShortcut(self.shortcut)
        self.action.triggered.connect(self.execute)
        app.gui.addAction(self.action)
        print(f"registered {name} at {shortcut}")

    def execute(self):
        try:
            self.fn()
        except Exception as e:
            self.app.log.error(e)