
import sys
import os.path as op
sys.path.append(op.abspath(op.join(op.dirname(__file__),"..")))
from __plugin__ import Plugin as _P
from __plugin__ import publicFun
from PySide2 import QtCore, QtWidgets, QtGui
import inspect
from . import parsers
from .parsers import *

app = None

PATH_7Z = "C:\\Program Files\\7-Zip\\7z.exe"

class Plugin(_P):
    def __init__(self, app_in):
        global app
        super().__init__(app_in)
        app = app_in
        self.parsers = self.getParsers()
        self.dfwidget = DFWidget()
        self.dfs = []

    def start(self):
        self.dfwidget.view.setModel(DFModel(self.dfs))
        self.dfwidget.start()
        self.extendDfs([])
    
    def extendDfs(self, newdfs):
        #if not newdfs: return
        self.dfs.extend(newdfs)
        self.dfwidget.view.repaint()

    def parseFile(self, filepath):
        for x in self.parsers:
            try: x(app).parse(filepath)
            except:continue
            break
        else:
            self.log.error(f"no parser found for <{filepath}>")

    @publicFun(guishortcut="Ctrl+o", isAsync = True)
    def open(self, path: str = "") -> int:
        """
        Opens a file on disk and tries to parse the contents into dataframes
        """
        if not path: 
            path = QtWidgets.QFileDialog.getOpenFileNames()
            path = path[0][0]
        if not path: return -1
        self.parseFile(path)
        return 0

    def getParsers(self):
        parserList = {}
        for k,v in inspect.getmembers(parsers, inspect.ismodule):
            if k.startswith("_"): continue
            else:
                try:parser = v.Parser
                except: pass
                parserList[k] = parser
        return parserList

class DFWidget(QtWidgets.QDockWidget):
    def __init__(self):
        super().__init__()
        self.view = DFView()
        w = QtWidgets.QWidget()
        w.setMinimumWidth(300)
        l = QtWidgets.QVBoxLayout()
        w.setLayout(l)
        l.addWidget(self.view)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(0)
        self.setWidget(w)
        self.setWindowTitle("dataframes")

    def start(self):
        app.gui.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self)
        self.setHidden(False)

class DFView(QtWidgets.QTreeView):
    fileDropped = QtCore.Signal(str)
    def __init__(self):
        super().__init__()
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.setAlternatingRowColors(True)

#https://learndataanalysis.org/display-pandas-dataframe-with-pyqt5-qtableview-widget/
class DFModel(QtCore.QAbstractItemModel):
    header = ["#", "name", "idxcol", "idxtara"]
    def __init__(self, data):
        super().__init__()
        self._data = data
    def rowCount(self, parent=None):
        return len(self._data)
    def columnCount(self, parent=None):
        return len(self.header)
    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.header[col]
        return None
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                #return str(self._data.iloc[index.row(), index.column()])
                return(f"{index.row()},{index.column()}")
        return None