from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtUiTools import QUiLoader
import os.path as op
import plugins
import importlib
import inspect
from functools import partial
import traceback
import qdarkstyle
from string import Template
import glob

class App(QtWidgets.QApplication):
    cmdDone = QtCore.Signal()
    allCmdsDone = QtCore.Signal()
    def __init__(self, args, info):
        super().__init__([])

        self.started = False
        self.info = info
        self.gui = AppWindow()
        self.gui.setWindowTitle(self.info["name"])

        #styletemplate = Template(open(op.join(op.dirname(__file__),"style.css"),"r").read())
        #stylevars = json.loads(open(op.join(op.dirname(__file__),"stylevars.jsonc"),"r").read())
        #stylesheet = styletemplate.substitute(**stylevars)

        self.log = None
        self.args = args
        self.cmdbacklog = []
        self.cmdDone.connect(lambda:self.execNextCmd(notBusyAnymore=True))
        self.cmdbusy = False

        self.plugins = {}
        self.publicfuns = {}

        pluginmods = {}
        for p in glob.glob(op.join(op.dirname(__file__),"..","plugins","*")):
            pb = op.basename(p)
            ok = (op.isdir(p) and not pb.startswith("_"))
            ok |= (pb.endswith(".py") and not pb.startswith("_"))
            if not ok: continue
            if pb.endswith(".py"):pb = pb[:-3]
            #try:
            pluginmodule = importlib.import_module("plugins."+pb)
            #except Exception as e:
            #    estr = f"Error loading plugin <{pb}>: {str(e)}"
            #    QtCore.QTimer.singleShot(0,lambda:self.log.error(estr))
            #    continue
            if hasattr(pluginmodule,"Plugin"):
                pluginmods[pb] = pluginmodule
        
        allmods = list(pluginmods.keys())
        resolvedPlugins = []
        unresolvedPlugins = []
        for k,v in pluginmods.items():
            if all([x in allmods for x in v.Plugin.getDependencies()]):
                plugin = v.Plugin()
                self.plugins[k] = plugin
                resolvedPlugins.append(k)
            else:
                unresolvedPlugins.append(k)

        for k,plugin in self.plugins.items():
            publicfuns = inspect.getmembers(plugin, lambda x: hasattr(x,"__dict__") and "__is_public_fun__" in x.__dict__)
            for name,pf in publicfuns:
                #self.log.info(f"found public fun {name} in {p}")
                sc = FunShortcut(self, k,name,pf)
                self.publicfuns[sc.name] = sc

        if resolvedPlugins: self.log.info(f"Loaded plugins: {', '.join(list(sorted(resolvedPlugins)))}")
        if unresolvedPlugins: self.log.error(f"Skipped plugins (missing dependencies): {', '.join(list(sorted(unresolvedPlugins)))}")

        self.aboutToQuit.connect(self.stop)

    def start(self):
        if self.started: return
        self.started = True
        for p in self.plugins.values(): p.start()
        for idx,cmd in enumerate(self.args["cmds"]):
            p = partial(self.plugins["cmd"].parse, cmd)
            QtCore.QTimer.singleShot(idx,p)

        if self.args["nogui"]:
            if self.args["cmds"]: self.allCmdsDone.connect(self.quit)
            else: QtCore.QTimer.singleShot(0,self.quit)
        else:
            stylesheet = qdarkstyle.load_stylesheet(qt_api='pyside2')
            self.setStyleSheet(stylesheet)
            self.gui.show()

        self.exec_()

    def stop(self):
        if not self.started: return
        self.started = False
        for p in self.plugins.values(): p.stop()
        self.quit()

    def __del__(self):
        self.stop()

    def execNextCmd(self, notBusyAnymore = False):
        if notBusyAnymore or self.args["noAsync"]: self.cmdbusy = False
        if self.cmdbusy:return
        self.cmdbusy = True
        if not self.cmdbacklog:
            self.cmdbusy = False
            self.allCmdsDone.emit()
            return
        cmd = self.cmdbacklog.pop(0)
        cmd()

#https://gist.github.com/cpbotha/1b42a20c8f3eb9bb7cb8
class UiLoader(QUiLoader):
    def __init__(self, baseinstance, customWidgets=None):
        QUiLoader.__init__(self, baseinstance)
        self.baseinstance = baseinstance
        self.customWidgets = customWidgets

    def createWidget(self, class_name, parent=None, name=''):
        if parent is None and self.baseinstance:
            return self.baseinstance
        else:
            if class_name in self.availableWidgets():
                widget = QUiLoader.createWidget(self, class_name, parent, name)
            else:
                try:
                    widget = self.customWidgets[class_name](parent)
                except (TypeError, KeyError) as e:
                    raise Exception('No custom widget ' + class_name + ' found in customWidgets param of UiLoader __init__.')
            if self.baseinstance:
                setattr(self.baseinstance, name, widget)
            return widget

def loadUi(uifile, baseinstance=None, customWidgets=None,
           workingDirectory=None):
    loader = UiLoader(baseinstance, customWidgets)
    if workingDirectory is not None:
        loader.setWorkingDirectory(workingDirectory)
    widget = loader.load(uifile)
    QtCore.QMetaObject.connectSlotsByName(widget)
    return widget

class AppWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        loadUi(op.join(op.dirname(__file__),"app.ui"), self)
        self.trackedWidgets = []

    def _moveEvent(self,e):
        for x in self.trackedWidgets:
            if x.isHidden():return
            center = self.mapToGlobal(QtCore.QPoint(0,0))+self.rect().center()
            x.move(center-x.rect().center())
            x.txt.setFocus()

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
                fn = self.fn
                evalstr = "fn("+argstr+")"
                eval(evalstr) #we do it like this for flexibility
                #self.fn(argstr)
            else:
                #if we are here, check if the function has args.
                #if it has not, call it.
                #if it has, build an input mask
                self.fn()
        except Exception as e:
            tb = traceback.format_exc().split("\n")
            for x in tb:self.app.log.error(x)
            self.app.cmdDone.emit()

    def getDescr(self):
        descr = inspect.getdoc(self.fn)
        if not descr: descr = "descr n/a"
        return descr