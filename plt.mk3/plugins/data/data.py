
import sys
import os.path as op
sys.path.append(op.abspath(op.join(op.dirname(__file__),"..")))
from __plugin__ import Plugin as _P
from __plugin__ import publicFun
from PySide2 import QtCore, QtWidgets, QtGui
import inspect
from . import parsers
from .parsers import *
from functools import partial

app = QtCore.QCoreApplication.instance()

PATH_7Z = "C:\\Program Files\\7-Zip\\7z.exe"

class Plugin(_P):
    def __init__(self):

        super().__init__()
        self.parsers = self.getParsers()
        self.dfwidget = DFWidget()
        self.dfs = []
        self.names = {}
        self.dfwidget.view.fileDropped.connect(lambda x:self.open(x))

    def start(self):
        self.extendDfs([])
        self.dfwidget.start()

    def extendDfs(self, newdfs):
        if newdfs:
            newdfs = [x for x in newdfs if x.attrs["name"] not in self.names]
            for x in newdfs:self.names[x.attrs["name"]] = x.attrs["#"]
            self.dfs.extend(newdfs)
        self.mdl = DFModel(self.dfs)
        self.dfwidget.view.setModel(self.mdl)
        self.dfwidget.resizeColumnsToContents()

    def parseFile(self, filepath):
        for x in self.parsers.values():
            try: dfs = x().parse(filepath)
            except UserWarning:continue
            break
        else:
            app.log.error(f"no parser found for <{filepath}>")
            return
        pf = partial(self.extendDfs, dfs)
        QtCore.QTimer.singleShot(0,pf)

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

    def resizeColumnsToContents(self):
        data = self.view.model()._data
        if not data:return
        L = len(data[0].columns)
        for idx in range(L):
            self.view.resizeColumnToContents(L-idx-1)

class DFView(QtWidgets.QTableView):
    fileDropped = QtCore.Signal(str)
    def __init__(self):
        super().__init__()
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setHighlightSections(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setItemDelegate(DFDelegate())

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():  e.accept()
        else:                       e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.setDropAction(QtCore.Qt.CopyAction)
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            for url in e.mimeData().urls():
                self.fileDropped.emit(str(url.toLocalFile()))
        else:
            e.ignore()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            self.toggleCurrItemSelected()
        else: super().keyPressEvent(event)

    def toggleCurrItemSelected(self):
        selectedIDX = self.selectedIndexes()
        if selectedIDX is None or len(selectedIDX) == 0: return
        for x in set(x.row() for x in selectedIDX):
            self.model().toggleDFselected(x)
        self.repaint()

class DFDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        sel = index.model().selectedRows
        if index.row() in sel: option.font.setWeight(QtGui.QFont.Bold)
        QtWidgets.QStyledItemDelegate.paint(self, painter, option, index)

    def createEditor(self, parent, opt, index):
        data = index.model()._data[index.row()]
        key = list(data.attrs.keys())[index.column()]

        if key.startswith("idxcol"):
            cb = QtWidgets.QComboBox(parent)
            cb.addItems([data.index.name]+list(data.columns))
            def value(x):
                return x.currentText()
            cb._value = partial(value,cb)
            return cb

        elif key.startswith("idxtara"):
            le = QtWidgets.QLineEdit(parent)
            def value(x):
                txt = x.text()
                return "DF.index[0]" if not txt else txt
            le._value = partial(value,le)
            return le

    def setModelData(self, editor, model, index):
        data = model._data[index.row()]
        key = list(data.attrs.keys())[index.column()]
        v = editor._value()
        data.attrs[key] = v
        data.reset_index(inplace = True)
        data.set_index(v,inplace = True)
        app.log.info(f"re-indexed {data.attrs['name']} to {v}")


#https://learndataanalysis.org/display-pandas-dataframe-with-pyqt5-qtableview-widget/
class DFModel(QtCore.QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self.selectedRows = []

    def rowCount(self, parent=None):
        return len(self._data)
    def columnCount(self, parent=None):
        if not self._data:return 0
        return len(self._data[0].attrs.keys())
    def headerData(self, col, orientation, role):
        if not self._data:return None
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return list(self._data[0].attrs.keys())[col]
        return None
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                #return str(self._data.iloc[index.row(), index.column()])
                row = index.row()
                col = index.column()
                data = self._data[row].attrs
                key = list(data.keys())[col]
                sel = row in self.selectedRows and col == 0
                return f"{'*' if sel else ''}{data[key]}"
        return None

    def flags(self, index):
        Qt = QtCore.Qt
        f = Qt.ItemIsSelectable|Qt.ItemIsEnabled
        if list(self._data[0].attrs.keys())[index.column()].endswith("*"): f|=Qt.ItemIsEditable
        return f

    def toggleDFselected(self, row):
        if row in self.selectedRows: self.selectedRows.remove(row)
        else:self.selectedRows.append(row)