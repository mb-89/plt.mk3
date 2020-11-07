from .__plugin__ import Plugin as _P
from .__plugin__ import publicFun
from PySide2 import QtCore, QtWidgets
import re

class Plugin(_P):
    def __init__(self, app):
        super().__init__(app)
        self.widget = Widget(app)

    @publicFun(guishortcut="Ctrl+^")
    def toggle(self):
        self.widget.togglehide()

    @publicFun(guishortcut="Ctrl+Space")
    def autocomplete(self):
        self.widget.autocomplete()

    def start(self):self.widget.start()

class Widget(QtWidgets.QDockWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.txt = QtWidgets.QLineEdit(self)
        empty = QtWidgets.QWidget(self)
        self.setTitleBarWidget(empty)
        self.setWindowTitle("cmd")
        self.setWidget(self.txt)
        self.txt.returnPressed.connect(self.parse)
        app.gui.addDockWidget(QtCore.Qt.TopDockWidgetArea, self)
        self.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        self.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
        self.setVisible(False)
        self.comp = None

    def autocomplete(self):
        if not self.comp:return
        if self.txt.text() == "": self.comp.setCompletionPrefix("")
        self.comp.complete()

    def togglehide(self):
        self.setVisible(self.isHidden())
        self.txt.setFocus()

    def start(self):
        list = sorted(self.app.publicfuns.keys())
        comp = QtWidgets.QCompleter(list)
        comp.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.txt.setCompleter(comp)
        self.comp = comp

    def parse(self):
        txt = self.txt.text()
        self.txt.clear()
        self.app.plugins["log"].logwidget.setVisible(True)
        cmdmatches = re.findall(r"(.*)\((.*)\)",txt)
        if cmdmatches: cmdmatches = cmdmatches[0]
        self.app.log.info(f">>> {txt}")
        if len(cmdmatches)==1:
            cmd = cmdmatches[0]
            args = []
        elif len(cmdmatches)>1:
            cmd = cmdmatches[0]
            args = cmdmatches[1:]
        else:
            cmd = "?"
            args = [txt.replace("?","")]
            args = [x for x in args if x]
        try:
            if cmd == "?":
                if args:
                    targetfun = self.app.publicfuns[args[0]]
                    docstring = targetfun.getDescr()
                    self.app.log.info("="*30)
                    self.app.log.info(args[0]+":")
                    for line in docstring.split("\n"):
                        self.app.log.info(line)
                    #get inputs (TODO)
                    #get outputs (TODO)
                    self.app.log.info("="*30)
                else:
                    #print general help
                    self.app.log.info(f"{self.app.info['name']} help:")
                    self.app.log.info(f"{self.app.info['description']}")
                    self.app.log.info("="*30)
                    self.app.log.info(f"Ctrl+Space for autocomplete.")
                    self.app.log.info(f"enter <function name> for help on function (eg: 'log.toggle' shows help on log.toggle).")
                    self.app.log.info(f"enter <function name>(args) to call a function (eg: 'log.toggle()' toggles log.")
                    self.app.log.info("="*30)
                    self.app.log.info(f"Functions available:")
                    for fn in sorted(self.app.publicfuns.keys()):
                        self.app.log.info(fn)
            else:
                targetfun = self.app.publicfuns[cmd]
                #do arg parsing later (TODO)
                targetfun.action.trigger()
        except KeyError:
            self.app.log.error(f"<<< invalid command")
        #self.app.log.info("")