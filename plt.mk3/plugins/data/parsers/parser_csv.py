from .__parser__ import Parser as _P
import os.path as op
import json
from PySide2 import QtCore, QtWidgets, QtGui
from time import sleep
from pandas import read_csv
import io
import configparser

KNOWNCSVFORMATS = [
    #{"sep":";", "header":[0], "skiprows":0} #Triggered logger fmt
]

class Parser(_P):
    def __init__(self, path, app):
        super().__init__(path, app)
        self.recognized = False
        #we only recognize csvs with "#format:{format json}" as the first line on the fly.
        if not op.isfile(path):return
        try:
            firstline = open(path,"r").readline()
        except:
            return
        if not firstline.startswith("#format:"):dct=None
        firstline = firstline.replace("#format:{","{")
        try: dct = json.loads(firstline)
        except json.decoder.JSONDecodeError:
            dct=None
        if dct is None and path.endswith(".csv"):
            for format in KNOWNCSVFORMATS:
                ok = self.tryFormat(format,path)
                if ok: 
                    dct=format
                    break
            else:
                mp = ManualParser(self,path)
                mp.exec_()
                dct = mp.result
                KNOWNCSVFORMATS.append(dct)
        if dct is None:return
        
        self.path = path
        self.recognized = True
        self.format = dct
        self.reservedFiles.append(path)

    def tryFormat(self,format,path):
        txt = ""
        with open(path,"r") as f:
            for idx in range(25):
                line = next(f)
                txt+=line
        try:df = read_csv(io.StringIO(txt),**format)
        except: return False
        if df.columns.nlevels >1:
            df.columns = ['_'.join(col) for col in df.columns]
        return len(df.columns)>1

    def parse(self):
        self.app.log.info(f"started parsing {op.basename(self.path)} (csv)")
        try:
            df = read_csv(self.path,**self.format)
            if df.empty: df = []
            else: dfs = [df]
        except:dfs = []
        dfs = self.postprocess(dfs)

        if dfs:self.app.log.info(f"done parsing {op.basename(self.path)}, extracted {len(dfs)} dataframes. (csv)")
        else: self.app.log.error(f"parsing {op.basename(self.path)} failed.")
        self.done.emit(dfs)

    def postprocess(self, dfs):
        for df in dfs:
            df.drop(df.filter(regex="Unname"),axis=1, inplace=True)
            if df.columns.nlevels <=1:continue
            df.columns = ['_'.join(col) for col in df.columns]

        #special case for old control parameter runs:
        if op.dirname(self.path).endswith("/meas") and op.isfile(logfile := op.abspath(op.join(self.path, "..","..","log",op.basename(self.path.replace(".csv",".log"))))):
            #we have a logfile that belongs to the file. Put its contents into the attrs
            cfg = configparser.ConfigParser()
            cfg.read(logfile)
            dct = {s:dict(cfg.items(s)) for s in cfg.sections()} #https://stackoverflow.com/questions/1773793/convert-configparser-items-to-dictionary
            df.attrs.update(dct)
        return super().postprocess(dfs)

class ManualParser(QtWidgets.QDialog):
    def __init__(self, parent,path):
        super().__init__()
        self.parent = parent
        self.path = path
        self.app = parent.app
        self.result = None
        self.setup()
        self.parse()

    def setup(self):
        L=QtWidgets.QVBoxLayout()
        L.setContentsMargins(0,0,0,0)
        L.setSpacing(0)

        rawtxt = QtWidgets.QTreeView()
        parseexpr = QtWidgets.QLineEdit('{"sep":",", "header":[0,1], "skiprows":0}')
        parsedtxt = QtWidgets.QTreeView()

        L.addWidget(rawtxt)
        L.addWidget(parseexpr)
        L.addWidget(parsedtxt)
        self.txt=""

        rawMdl = QtGui.QStandardItemModel()
        rawMdl.setColumnCount(1)
        rawtxt.setModel(rawMdl)
        rawtxt.setHeaderHidden(True)
        rawtxt.setAlternatingRowColors(True)
        rawtxt.resizeColumnToContents(0)

        with open(self.path,"r") as f:
            for idx in range(25):
                line = next(f)
                item = QtGui.QStandardItem(line.strip())
                self.txt+=line
                item.setEditable(False)
                rawMdl.appendRow([item])

        parsemdl = QtGui.QStandardItemModel()
        parsedtxt.setModel(parsemdl)
        parsedtxt.setAlternatingRowColors(True)

        parseexpr.editingFinished.connect(self.parse)
        self.parseexpr = parseexpr
        self.parsemdl =parsemdl
        self.parsedtxt =parsedtxt

        self.rowsAndCols = QtWidgets.QLabel("")
        self.ok = QtWidgets.QPushButton("Ok")
        self.cancel = QtWidgets.QPushButton("cancel")
        self.cancel.clicked.connect(self.reject)
        self.ok.clicked.connect(self.accept)
        self.cancel.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ok.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        L2 = QtWidgets.QHBoxLayout()
        L2.setContentsMargins(0,0,0,0)
        L2.setSpacing(0)
        L2.addItem(QtWidgets.QSpacerItem(5,5,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding))
        L2.addWidget(self.rowsAndCols)
        L2.addWidget(self.cancel)
        L2.addWidget(self.ok)
        L.addLayout(L2)

        self.setLayout(L)
        self.setMinimumWidth(600)
    
    def accept(self):
        self.result = json.loads(self.parseexpr.text())
        super().accept()

    def parse(self):
        self.parsemdl.clear()
        self.ok.setEnabled(False)
        self.rowsAndCols.setText("")
        try:dct = json.loads(self.parseexpr.text())
        except:
            self.parseexpr.setStyleSheet("QLineEdit { background: rgb(255,204,203);}")
            return
        self.parseexpr.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")
        try:df = read_csv(io.StringIO(self.txt),**dct)
        except:
            self.parseexpr.setStyleSheet("QLineEdit { background: rgb(255,204,203);}")
            return
        self.parseexpr.setStyleSheet("QLineEdit { background: rgb(255, 255, 255);}")

        #fix columns:
        if df.columns.nlevels >1:
            df.columns = ['_'.join(col) for col in df.columns]
        self.parsemdl.setHorizontalHeaderLabels(df.columns)
        L=len(df.columns)
        self.parsemdl.setColumnCount(L)

        for idx, row in df.iterrows():
            QtRow = [QtGui.QStandardItem(str(x).strip()) for x in row]
            self.parsemdl.appendRow(QtRow)

        self.rowsAndCols.setText(f"found {L} cols of data (before postprocessing) ")
        self.ok.setEnabled(True)
        for idx in range(L):
            self.parsedtxt.resizeColumnToContents(L-1-idx)

        self.parseexpr.setStyleSheet("QLineEdit { background: rgb(144, 238, 144);}")


