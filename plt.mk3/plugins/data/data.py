import sys
import os.path as op
sys.path.append(op.abspath(op.join(op.dirname(__file__),"..")))
from __plugin__ import Plugin as _P
from __plugin__ import publicFun
from PySide2 import QtCore, QtWidgets, QtGui
import re
from collections.abc import Sequence
import inspect
from . import parsers
from .parsers import *
import time
import itertools
import enum
import tempfile
import subprocess
import glob

class DSheader(enum.Enum):
    type = 0,
    idx = 1,
    name = 2,
    Yfun = 3,
    Yax = 4,
    Xax = 5,
    Xtrig = 6

app = None

PATH_7Z = "C:\\Program Files\\7-Zip\\7z.exe"

class Plugin(_P):
    def __init__(self, app_in):
        global app
        super().__init__(app_in)
        self.DFmodel = DFModel(app_in)
        self.DSmodel = DSModel(app_in)
        self.widget = Widget(app_in)
        self.parsers = self.getParsers()
        self.app = app_in
        app = app_in
        self.DFmodel.updateView.connect(self.widget.DFview.viewport().repaint)
        self.DSmodel.updateView.connect(self.widget.DSview.viewport().repaint)
        self.widget.DFview.fileDropped.connect(lambda x:self.open(x))
        self.parseResultQueue = []
        self.busyprocessing = False

    @publicFun(guishortcut="Ctrl+o", isAsync = True)
    def open(self, path: str = "") -> int:
        """
        Opens a file on disk and tries to parse the contents into dataframes
        """
        if not path: 
            path = QtWidgets.QFileDialog.getOpenFileNames()
            path = path[0][0]
        if not path: return -1
        self.parse([path])
        return 0

    @publicFun()
    def selectDF(self,  dfnames: str) -> int:
        """
        Selects the given DFs by name, either "DF<x>" or the shortname
        """
        if not dfnames: return -1
        for x in dfnames.split(","): self.DFmodel.setDFselected(x,1)
        return 0

    @publicFun()
    def setYax(self, dsAndAx: str) -> int:
        """
        Sets the target y axis for the given DS, either "DS<x>" or the shortname
        """
        dsAndAx = dsAndAx.split(",")
        if len(dsAndAx) != 2: return -1
        self.DSmodel.setYax(dsAndAx[0], int(dsAndAx[1]), 1)
        return 0

    @publicFun()
    def setYfun(self, dsAndFun: str) -> int:
        """
        Sets the y axis function for the given DS, either "DS<x>" or the shortname
        """
        dsAndFun = dsAndFun.split(",")
        fun = ",".join(dsAndFun[1:])
        dsAndFun = [x for x in (dsAndFun[0],fun) if x]

        if len(dsAndFun) != 2: return -1
        self.DSmodel.setYfun(dsAndFun[0], dsAndFun[1])
        return 0

    @publicFun()
    def setPlotType(self, dsAndType: str) -> int:
        """
        Sets the plot type for the given DS, either "DS<x>" or the shortname
        """
        dsAndType = dsAndType.split(",")
        if len(dsAndType) != 2: return -1
        self.DSmodel.setPlotType(dsAndType[0], dsAndType[1])
        return 0

    @publicFun()
    def addUserFun(self, NameAndFun: str) -> int:
        """
        Adds a user function to the list of dataseries
        """
        NameAndFun = NameAndFun.split(",")
        fun = ",".join(NameAndFun[1:])
        NameAndFun = [x for x in (NameAndFun[0],fun) if x]

        if len(NameAndFun) != 2: return -1
        self.DSmodel.addUserFun(NameAndFun[0], NameAndFun[1])
        return 0

    def start(self):
        self.widget.DFview.setModel(self.DFmodel)
        self.widget.DSview.setModel(self.DSmodel)
        self.widget.start()
    
    def getParsers(self):
        parserList = {}
        for k,v in inspect.getmembers(parsers, inspect.ismodule):
            if k.startswith("_"): continue
            else:
                try:parser = v.Parser
                except: pass
                parserList[k] = parser
        return parserList

    def parse(self, fileList):
        parseList = []
        #we need to go over the list multiple times,
        #bc some parsers might remove multiple entries:
        while fileList:
            target = fileList[0]

            if target.endswith(".7z"):
                self.tempdir = tempfile.TemporaryDirectory()
                line = f'"{PATH_7Z}" x {target} -o"{self.tempdir.name}"'
                result=subprocess.run(line,capture_output=True)
                filesublist = [x for x in glob.glob(self.tempdir.name+"/*.*") if op.isfile(x)]
                self.parse(filesublist)
            
            parser, errmsg = self.getFileParser(target)
            if parser:
                for rf in parser.reservedFiles:
                    if rf in fileList: fileList.remove(rf)
                pr = ParserRunner(parser, self.app)
                parser.done.connect(self.getParserResults)
                parseList.append(pr)
            else:
                self.app.log.warning(f"{target} skipped ({errmsg}).")
                if target.endswith(".csv"):
                    self.app.log.warning("Remember: to parse csv files on the fly, the first line of the file must contain format information")
                    self.app.log.warning('Example format line:')
                    self.app.log.warning('#format:{"sep":",", "header":[0,1], "skiprows":1}')
                    self.app.log.warning('see also: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html')
                fileList.remove(target)
                continue

        #now, we use the threadpool to parse all files in the background
        #print(f"main:{QtCore.QThread.currentThread()}")
        if not self.app.args.get("nomultithread"):
            pool = QtCore.QThreadPool.globalInstance()
            for p in parseList:pool.start(p)
        else:
            for p in parseList: p.run()

    def getParserResults(self, dfs):
        self.parseResultQueue.append(dfs)
        QtCore.QTimer.singleShot(0,self.app.cmdDone.emit)
        QtCore.QTimer.singleShot(0,self.processNextResult)

    def processNextResult(self):
        if self.busyprocessing or not self.parseResultQueue:return
        self.busyprocessing=True
        nxt = self.parseResultQueue.pop(0)
        for x in nxt: self.DFmodel.appendRow(self.DFmodel.df2qtRow(x))
        self.DSmodel.appendColsFromDFs(nxt)
        self.widget.DFview.resizeColumnsToContents()
        self.widget.DSview.resizeColumnsToContents()
        self.busyprocessing = False
        QtCore.QTimer.singleShot(0,self.processNextResult)


    def getFileParser(self, target):
        for pname, p in self.parsers.items():
            parser = p(target, self.app)
            if parser.recognized:
                return parser, ""
        return None, "no parser found"

    def getPlotInfo(self):
        dfs = {}
        dss = {}
        mdl = self.widget.DFview.model().invisibleRootItem()
        for idx in range(mdl.rowCount()):
            df = mdl.child(idx).data(QtCore.Qt.UserRole)
            name = mdl.child(idx).text()
            if df.attrs.get("_selected"):
                dfs[name] = df
        mdl = self.widget.DSview.model().invisibleRootItem()
        for idx in range(mdl.rowCount()):
            ds = mdl.child(idx).data(QtCore.Qt.UserRole)
            shortname = ds.items[DSheader.idx].text()
            name = ds.items[DSheader.name].text()
            if ds.attrs.get("_selected"):dss[shortname] = ds
        return {"dfs":dfs, "dss": dss}

class Widget(QtWidgets.QDockWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.DFview = DFView()
        self.DSview = DSview()

        w = QtWidgets.QWidget()
        w.setMinimumWidth(300)
        l = QtWidgets.QVBoxLayout()
        w.setLayout(l)
        l.addWidget(self.DFview)
        l.addWidget(self.DSview)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(0)
        self.setWidget(w)
        self.setWindowTitle("data")

    def start(self):
        self.app.gui.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self)
        self.setHidden(False)
        for idx in range(len(self.DFview.model().header)):
            self.DFview.resizeColumnToContents(idx)
        for idx in range(len(DSheader)):
            self.DSview.resizeColumnToContents(idx)

### dataframe stuff --------------------------------------------------------------------------------
class DFModel(QtGui.QStandardItemModel):
    updateView = QtCore.Signal()
    header = ["#", "name", "rows", "cols", "src"]
    srcattr = ["idx", "name", "rows", "cols", "srcfile"]
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setHorizontalHeaderLabels(self.header)
        self.setColumnCount(len(self.header))

    def df2qtRow(self, df):
        row = []
        attrs="\n".join(f"{k}: {v}" for k,v in df.attrs.items())
        for idx in range(len(self.header)):
            item = QtGui.QStandardItem(str(df.attrs[self.srcattr[idx]]))
            item.setToolTip(attrs)
            item.setData(df, QtCore.Qt.UserRole)
            row.append(item)
        return row

    def setDFselected(self, nameOrIdx, newval = -1):
        #newval : 0 = off, 1 = on, -1 = toggle (default)
        try: attrs = nameOrIdx.data(QtCore.Qt.UserRole).attrs
        except:attrs = None
        if attrs is None:
            root = self.invisibleRootItem()
            dfnames = [root.child(idx).text() for idx in range(root.rowCount())]
            shortnames = [root.child(idx,1).text() for idx in range(root.rowCount())]
            if nameOrIdx in dfnames:    attrs = root.child(dfnames.index(nameOrIdx)).data(QtCore.Qt.UserRole).attrs
            if nameOrIdx in shortnames: attrs = root.child(shortnames.index(nameOrIdx)).data(QtCore.Qt.UserRole).attrs

        if attrs is None:return
        isSelected = attrs.get("_selected")
        attrs["_selected"] = not isSelected
        self.updateView.emit()

class DFView(QtWidgets.QTreeView):
    fileDropped = QtCore.Signal(str)
    def __init__(self):
        super().__init__()
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.setAlternatingRowColors(True)
        self.setItemDelegate(DFDelegate())

    def resizeColumnsToContents(self):
        L = len(self.model().header)
        for idx in range(L):
            self.resizeColumnToContents(L-idx-1)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():  e.accept()
        else:                       e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.setDropAction(QtCore.Qt.CopyAction)
            e.accept()
        else:
            e.ignore()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            self.toggleCurrItemSelected()
        else: super().keyPressEvent(event)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            for url in e.mimeData().urls():
                self.fileDropped.emit(str(url.toLocalFile()))
        else:
            e.ignore()

    def toggleCurrItemSelected(self):
        selectedIDX = self.selectedIndexes()
        if selectedIDX is None or len(selectedIDX) == 0: return
        selectedIDX = selectedIDX[0]
        self.model().setDFselected(selectedIDX, -1)

class DFDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        attrs = index.data(QtCore.Qt.UserRole).attrs
        if attrs.get("_selected"): option.font.setWeight(QtGui.QFont.Bold)
        QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)

## dataseries stuff --------------------------------------------------------------------------------
class DSModel(QtGui.QStandardItemModel):
    updateView = QtCore.Signal()
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setHorizontalHeaderLabels([x.name for x in DSheader])
        self.setColumnCount(len(DSheader))
        self.contents = {}
        self.nrOfUserFuns = 0
        self.header = DSheader

    def appendColsFromDFs(self, dfs):
        cols = sorted(list(set(list(itertools.chain(*(list(x.columns)+[x.index.name] for x in dfs))))))
        for col in cols:
            if col in self.contents: continue
            shortname = f"DS{len(self.contents)}"
            DScontainer(self, {}, shortname, col, "DF[DS]")

    def setYax(self, nameOrIdx, Yax, newval = -1):
        #newval : 0 = off, 1 = on, -1 = toggle (default)
        try: attrs = nameOrIdx.attrs
        except:attrs = None
        if attrs is None:
            root = self.invisibleRootItem()
            shortnames = [x.items[DSheader.idx].text() for x in self.contents.values()]
            dsnames = [x.items[DSheader.name].text() for x in self.contents.values()]
            if nameOrIdx in dsnames:    nameOrIdx = root.child(dsnames.index(nameOrIdx)).data(QtCore.Qt.UserRole)
            if nameOrIdx in shortnames: nameOrIdx = root.child(shortnames.index(nameOrIdx)).data(QtCore.Qt.UserRole)

        attrs = nameOrIdx.attrs
        if attrs is None:return
        targetYaxes = attrs.setdefault(f"Yaxes",[])
        if   (Yax in targetYaxes)     and newval in (-1,0): targetYaxes.remove(Yax)
        elif (Yax not in targetYaxes) and newval in (-1,1): targetYaxes.append(Yax)
        attrs["_selected"] = len(targetYaxes)>0
        nameOrIdx.items[DSheader.Yax].setText(", ".join((str(x) for x in targetYaxes)))
        self.updateView.emit()

    def setYfun(self, name, Yfun):
        #newval : 0 = off, 1 = on, -1 = toggle (default)

        root = self.invisibleRootItem()
        dsnames = [x.items[DSheader.name].text() for x in self.contents.values()]
        shortnames = [x.items[DSheader.idx].text() for x in self.contents.values()]
        if name in dsnames:    obj = root.child(dsnames.index(name)).data(QtCore.Qt.UserRole)
        if name in shortnames: obj = root.child(shortnames.index(name)).data(QtCore.Qt.UserRole)
        obj.items[DSheader.Yfun].setText(Yfun)
        self.updateView.emit()

    def setPlotType(self, name, type):
        root = self.invisibleRootItem()
        dsnames = [x.items[DSheader.name].text() for x in self.contents.values()]
        shortnames = [x.items[DSheader.name].text() for x in self.contents.values()]
        if name in dsnames:    obj = root.child(dsnames.index(name)).data(QtCore.Qt.UserRole)
        if name in shortnames: obj = root.child(shortnames.index(name)).data(QtCore.Qt.UserRole)
        obj.items[DSheader.type].setText(type)
        self.updateView.emit()
 

    def addUserFun(self, name, Yfun):
        root = self.invisibleRootItem()
        shortname = f"UF{self.nrOfUserFuns}"
        self.nrOfUserFuns+=1
        DScontainer(self, {}, shortname,name,Yfun)

class DScontainer():
    def __init__(self, parent, attrs, shortname, name,  Yfun):
        self.attrs = attrs
        self.origname = name
        self.items = {
            DSheader.type: QtGui.QStandardItem("xy"),
            DSheader.idx:  QtGui.QStandardItem(shortname),
            DSheader.name: QtGui.QStandardItem(name),
            DSheader.Yfun: QtGui.QStandardItem(Yfun),
            DSheader.Yax:  QtGui.QStandardItem(f""),
            DSheader.Xax:  QtGui.QStandardItem(f""),
            DSheader.Xtrig:QtGui.QStandardItem(f""),
            }
        for x in self.items.values():
             x.setData(self, QtCore.Qt.UserRole)
        parent.contents[self.origname] = self
        parent.appendRow(list(self.items.values()))

class DSview(QtWidgets.QTreeView):
    def __init__(self):
        super().__init__()
        self.setAlternatingRowColors(True)
        self.setItemDelegate(DSDelegate())
    def resizeColumnsToContents(self):
        L = len(DSheader)
        for idx in range(L):
            self.resizeColumnToContents(L-idx-1)

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        if key >= QtCore.Qt.Key_1 and key <= QtCore.Qt.Key_9:
            nr = int(key - QtCore.Qt.Key_1)+1
            self.toggleYax(nr)
        else: super().keyPressEvent(event)

    def toggleYax(self, nr):
        selectedIDX = self.selectedIndexes()
        if selectedIDX is None or len(selectedIDX) == 0: return
        selectedIDX = selectedIDX[0]
        obj = selectedIDX.data(QtCore.Qt.UserRole)
        self.model().setYax(obj, nr, -1)

class DSDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() > 0:
            attrs = index.data(QtCore.Qt.UserRole).attrs
            if attrs.get("_selected"): option.font.setWeight(QtGui.QFont.Bold)
        QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)
    def createEditor(self, parent, option, index):
        if index.column() == 0:
            cb = QtWidgets.QComboBox(parent)
            cb.addItems(list(app.plugins["plot"].widget.plotbib.plotterDict.keys()))
            return cb
        return QtWidgets.QStyledItemDelegate.createEditor(self, parent, option, index)

class ParserRunner(QtCore.QRunnable):
    def __init__(self, parser, parent):
        super().__init__(parent)
        self.parser = parser
    def run(self):
        self.parser.parse()