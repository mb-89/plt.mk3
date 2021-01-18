from .__plugin__ import Plugin as _P
from .__plugin__ import publicFun
from PySide2 import QtCore, QtWidgets
import re
from functools import partial
import os.path as op

app = QtCore.QCoreApplication.instance()

class Plugin(_P):
    @staticmethod
    def getDependencies():
        return ["log"]

    def __init__(self):
        super().__init__()
        self.widget = Widget()

    @publicFun(guishortcut="Ctrl+^")
    def toggle(self):
        self.widget.togglehide()

    @publicFun(guishortcut="Ctrl+Space")
    def autocomplete(self):
        self.widget.autocomplete()

    def start(self):self.widget.start()

    def parse(self, cmd): 
        if cmd:
            self.widget.parse(cmd)

class Widget(QtWidgets.QDockWidget):
    def __init__(self, ):
        super().__init__(app.gui)
        self.txt = QtWidgets.QComboBox(self)
        self.txt.setEditable(True)
        self.txt.setFocusPolicy(QtCore.Qt.StrongFocus)
        empty = QtWidgets.QWidget(self)
        self.setTitleBarWidget(empty)
        self.setWindowTitle("cmd")
        self.setWidget(self.txt)
        self.txt.lineEdit().returnPressed.connect(self.parse)
        app.gui.addDockWidget(QtCore.Qt.TopDockWidgetArea, self)
        self.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        self.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
        self.setVisible(False)
        self.comp = None

    def autocomplete(self):
        if not self.comp:return
        if self.txt.currentText () == "": self.comp.setCompletionPrefix("")
        self.comp.complete()

    def togglehide(self):
        hidden = self.isHidden()
        self.setVisible(hidden)
        if hidden:QtCore.QTimer.singleShot(0,self.txt.setFocus)

    def start(self):
        list = sorted(app.publicfuns.keys())
        comp = QtWidgets.QCompleter(list)
        comp.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.txt.setCompleter(comp)
        self.comp = comp

    def parse(self, txt=None):
        if txt is None or isinstance(txt,int):
            txt = self.txt.currentText()
            self.txt.clearEditText()
            app.plugins["log"].logwidget.setVisible(True)

        if op.isfile(fp := op.abspath(txt)):
            filecmds = open(fp,"r").readlines()
            if filecmds:
                app.log.info(f">>> executing {fp}")
            for idx, cmd in enumerate(filecmds):
                x = cmd.strip()
                if not x:continue
                QtCore.QTimer.singleShot(idx+1, partial(self.parse,x) )
            return

        cmdmatches = re.findall(r"(.*?)\((.*)\)",txt)
        if cmdmatches: cmdmatches = [x for x in cmdmatches[0] if x]
        app.log.info(f">>> {txt}")
        if len(cmdmatches)==1:
            cmd = cmdmatches[0]
            args = []
        elif len(cmdmatches)>1:
            cmd = cmdmatches[0]
            args = cmdmatches[1]
        else:
            cmd = "?"
            args = [txt.replace("?","")]
            args = [x for x in args if x]
        try:
            if cmd == "?":
                if args:
                    targetfun = app.publicfuns[args[0]]
                    docstring = targetfun.getDescr()
                    app.log.info("="*30)
                    app.log.info(args[0]+":")
                    for line in docstring.split("\n"):
                        app.log.info(line)
                    #get inputs (TODO)
                    #get outputs (TODO)
                    app.log.info("="*30)
                else:
                    #print general help
                    app.log.info(f"{app.info['name']} help:")
                    app.log.info(f"{app.info['description']}")
                    app.log.info("="*30)
                    app.log.info(f"Ctrl+Space for autocomplete.")
                    app.log.info(f"enter <function name> for help on function (eg: 'log.toggle' shows help on log.toggle).")
                    app.log.info(f"enter <function name>(args) to call a function (eg: 'log.toggle()' toggles log.")
                    app.log.info("="*30)
                    app.log.info(f"Functions available:")
                    for fn in sorted(app.publicfuns.keys()):
                        app.log.info(fn)
                app.execNextCmd()
            else:
                p = partial(app.publicfuns[cmd].trigger, args)
                app.cmdbacklog.append(p)
                app.execNextCmd()
        except KeyError:
            app.log.error(f"<<< invalid command")
        #app.log.info("")