import pyqtgraph as pg
from .__plotter__ import Plotter as _P
from .__plotter__ import SubPlot as _SP
from .__plotter__ import Addon as _A
from scipy import fft
import numpy as np
from PySide2 import QtCore,QtWidgets,QtGui
import pandas as pd
from scipy import signal
from pyqtgraph import functions as fn
from functools import partial
from more_itertools import sliced
import json
import struct

class Plotter(_P):
    def getPlot(self, X, Y, Xnames, Ynames, plotinfo, selectedSeries, sharedCoords):
        return SubPlot(X,Y,Xnames,Ynames,sharedCoords) 

class SubPlot(_SP):
    def __init__(self, xdata, ydata, xnames, ynames, sharedCoords):
        super().__init__(xdata, ydata, xnames, ynames, sharedCoords)
        
        self.data = dict( (f'{y.attrs["name"]} @ {y.attrs["idx"]}',y) for y in ydata )
        self.updateData(self.data)
        self.results = {}

        addonList = [Addon_table,Addon_plot]
        self.addons = dict( (x.name,x(self)) for x in addonList)

        for k,v in self.addons.items():self.addRowColList(v.getGuiElements())
        for k,v in self.addons.items():v.resolveConnections()

    def updateData(self, _):
        for k,v in self.addons.items():v.updateData(self.data)

class Addon_table(_A):
    name = "table"
    def __init__(self, parent):
        super().__init__(parent)
        self.tables = [DataTable(self),DataTable(self)]
        self.translator = QtWidgets.QPlainTextEdit()
        self.translator.setPlainText(json.dumps(self.translatorExample, indent=4, sort_keys=True))
        self.translator.textChanged.connect(self.updateProxys)
        self.translator.setStyleSheet(f"QPlainTextEdit{{{self.parent.style}}}")
        VL = QtWidgets.QVBoxLayout()
        lbl = QtWidgets.QLabel("Translator:")
        lbl.setStyleSheet(f"QLabel{{{self.parent.style}}}")
        lbl.setMinimumHeight(20)
        tb = QtWidgets.QPushButton("Run translation")
        tb.setStyleSheet(f"QPushButton{{{self.parent.style}}}")
        tb.clicked.connect(self.translate)
        tb.setMinimumHeight(20)

        VL.addWidget(lbl)
        VL.addWidget(self.translator)
        VL.addWidget(tb)
        self.translator.setMaximumHeight(380)
        VL.addItem(QtWidgets.QSpacerItem(10,10,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding))
        self.translatorLayout = VL
        self.translationsLayout = self.buildTranslationsLayout()

    def buildTranslationsLayout(self):
        self.translations = QtWidgets.QPlainTextEdit()
        self.translations.setPlainText("")
        self.translations.textChanged.connect(self.updateProxys)
        self.translations.setStyleSheet(f"QPlainTextEdit{{{self.parent.style}}}")
        self.translations.setReadOnly(True)
        VL = QtWidgets.QVBoxLayout()
        lbl = QtWidgets.QLabel("Translated dataseries:")
        lbl.setStyleSheet(f"QLabel{{{self.parent.style}}}")
        lbl.setMinimumHeight(20)
        tb = QtWidgets.QPushButton("store translation as dataframe")
        tb.setStyleSheet(f"QPushButton{{{self.parent.style}}}")
        tb.clicked.connect(self.storeTranslation)
        tb.setMinimumHeight(20)
        
        VL.addWidget(lbl)
        VL.addWidget(self.translations)
        VL.addWidget(tb)
        self.translations.setMaximumHeight(380)
        VL.addItem(QtWidgets.QSpacerItem(10,10,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding))
        return VL

    def getGuiElements(self):
        return [ [self.tables+[self.translatorLayout, self.translationsLayout]] ]

    def translate(self):
        results = {}
        for k,v in self.parent.data.items():
            bindata = b"".join([bytes(x.data) for x in v.values])
            for name,format in json.loads(self.translator.toPlainText()).items():
                try:
                    parsedData = [x[0] for x in struct.iter_unpack(format,bindata)]
                except:
                    parsedData = None
                if parsedData is None: continue
                seriesname = f"{name} @ {k}"
                series = pd.Series(parsedData,index=v.index,name=seriesname)
                results[seriesname] = series
        lines = []
        for k,v in results.items():
            line = f"{k}: {len(v)} x {v.dtype}"
            lines.append(line)
        self.translations.setPlainText("\n".join(lines))
        self.parent.results = results
        print(f"datastream parsing done, found {len(results)} series")
        self.parent.addons["plot"].updateSelector()

    def storeTranslation(self):
        results = self.parent.results
        ynames = results.keys()
        ydata = [x for x in results.values()]
        xdata = [x.index for x in results.values()]

        #put data in dataframe
        def xyname2s(idx,X,Y,yname):
            comments = " / ".join(Y.attrs.get("comments",[]))
            nameAndComments = yname
            return pd.Series(Y,index=X,name=nameAndComments)

        df = pd.concat([xyname2s(idx,X,Y,yname).to_frame() for idx,(X,Y,yname) in enumerate(zip(xdata,ydata,ynames))],axis=1)
        df.attrs["name"]="datastream"
        df.attrs["rows"]=len(df)
        df.attrs["cols"]=len(df.columns)
        df.attrs["srcfile"]="datastream"

        QtWidgets.QApplication.instance().plugins["data"].getParserResults([df])

    def updateData(self, data):
        for t in self.tables:
            t.updateData(data)
        self.updateProxys()
    
    def updateProxys(self):
        for proxy in self.parent.proxys:
            proxy.update()
            proxy.updateGeometry()

    translatorExample = {
        "Byte0": "B7x",
        "Byte1": "xB6x",
        "Byte2": "2xB5x",
        "Byte3": "3xB4x",
        "Byte4": "4xB3x",
        "Byte5": "5xB2x",
        "Byte6": "6xBx",
        "Byte7": "7xB",
    }

class DataTable(QtWidgets.QVBoxLayout):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setContentsMargins(0,0,0,0)
        self.setSpacing(0)
        
        self.table = QtWidgets.QPlainTextEdit()
        self.table.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.table.setStyleSheet(f"QPlainTextEdit{{{self.parent.parent.style}}}")
        self.table.setMaximumHeight(400)
        self.table.setReadOnly(True)
        f = QtGui.QFont("monospace")
        f.setStyleHint(QtGui.QFont.TypeWriter)
        self.table.setFont(f)

        selector = QtWidgets.QComboBox()
        selector.addItems(self.parent.parent.data.keys())
        selector.currentTextChanged.connect(lambda x:self.updateData())

        self.addWidget(selector)
        self.addWidget(self.table)
        self.addItem(QtWidgets.QSpacerItem(10,10,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding))
        self.selector = selector

    def updateData(self,data=None):
        if data is None: data = self.parent.parent.data
        lines = []
        currvals=data[self.selector.currentText()]
        for t,d in zip(currvals.index,currvals.values):
            s=hex(d)[2:]
            if len(s)%2:s="0"+s
            s = " ".join(sliced(s, 2))
            lines.append(f"{t:.4f}\t{s}")

        self.table.setPlainText("\n".join(lines))

class Addon_plot(_A):
    name = "plot"

    def __init__(self, parent):
        super().__init__(parent)
        VL = QtWidgets.QVBoxLayout()
        self.layout = VL
        VL.setContentsMargins(0,0,0,0)
        VL.setSpacing(0)
        selector = QtWidgets.QComboBox()
        selector.currentTextChanged.connect(self.updatePlot)
        selector.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        VL.addWidget(selector)
        self.selector=selector
        self.plt = pg.PlotItem()
        self.plt.showGrid(x=True,y=True,alpha=1)

    def updateSelector(self):
        self.selector.clear()
        self.selector.addItems(self.parent.results.keys())
        width = self.selector.minimumSizeHint().width()
        self.selector.view().setMinimumWidth(width)

    def updatePlot(self, col):
        data = self.parent.results[col]
        self.plt.clear()
        self.plt.plot(y=data.values,x=data.index,pen="r")

    def getGuiElements(self):
        return [[[self.layout],self.plt]]