import sys
import os.path as op
sys.path.append(op.abspath(op.join(op.dirname(__file__),"..")))
from __plugin__ import Plugin as _P
from __plugin__ import publicFun

from . import plotters
from .plotters import *
from . import functions
from .functions import *

from PySide2 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
import pyqtgraph.exporters
import tempfile
import os
import math
import numpy as np
import pandas as pd
import inspect

DSHeader = None

class Plugin(_P):
    def __init__(self, app):
        super().__init__(app)
        self.widget = Widget(app)
        app.gui.setCentralWidget(self.widget)
        self.app = app

    @publicFun(guishortcut="F5")
    def plot(self) -> int:
        """
        Plots the selected series functions of the selected frames vs the selected axes
        """
        global DSHeader
        plotinfo = self.app.plugins["data"].getPlotInfo()
        DSHeader = self.app.plugins["data"].DSmodel.header
        runner = PlotRunner(plotinfo, self.widget)

        #pool = QtCore.QThreadPool.globalInstance()
        #pool.start(runner)
        runner.run()
        return 0

    @publicFun(guishortcut="Ctrl+s")
    def save(self) -> int:
        """
        Puts the current figure in the clipboard
        """
        target = op.join(tempfile.gettempdir(),"plt.mk3.png")
        exporter = pg.exporters.ImageExporter(self.widget.scene())
        exporter.export(target)
        img = QtGui.QImage(target)
        os.remove(target)
        self.app.clipboard().setImage(img,QtGui.QClipboard.Clipboard)
        self.app.log.info(f"moved current fig to clipboard")
        return 0

class PlotRunner(QtCore.QRunnable):
    def __init__(self, plotinfo, widget):
        super().__init__()
        self.plotinfo = plotinfo
        self.widget = widget
        self.coordsystems = []
        self.plottypes = self.widget.plotbib
        self.functions = self.widget.funbib
    def run(self):
        graphs = self.createLayout()
        self.plot(graphs)

    def createLayout(self):
        #plotinfo["dfs"] contains the dataframes that were selected
        #plotinfo["dss"] contains the dataseries that are plotted on at least one y axis
        self.coordsystems = []
        graphs = []
        for idx in range(9):graphs.append(Graph(self.plottypes, self.functions))

        for ds in self.plotinfo["dss"].values():
            yaxes = tuple(int(x)-1 for x in ds.items[DSHeader.Yax].text().split(", "))
            for yax in yaxes: graphs[yax].dss.append(ds)
        
        return tuple(self.chunks(tuple(x for x in graphs if x.dss),3))

    def plot(self, graphs):
        w = self.widget
        w.clear()
        for colidx,col in enumerate(graphs):
            for rowidx,row in enumerate(col):
                row.buildgraph(self.plotinfo, w, rowidx, colidx, self.coordsystems)

    def chunks(self, lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

class Graph():
    def __init__(self, plottypes,functions):
        self.dss = []
        self.plottypes = plottypes
        self.functions = functions

    def buildgraph(self, _plotinfo, _widget, _row, _col, _coordsystems):
        #first, we get local variables for all dataframes:
        for _k,_v in _plotinfo["dfs"].items():
            if _k.startswith("DF"):
                vars()[_k] = _v

        #now we get a shortcut for all dataseries names:
        for _k,_ds in _plotinfo["dss"].items():
            if _k.startswith("DS"):
                vars()[_ds.items[DSHeader.idx].text()] = _ds.items[DSHeader.name].text()
        
        #now we walk over all ds that are plotted in this graph and evaluate the X,Y,trig expressions
        _ydatas = []
        _xdatas = []

        _L = len(_plotinfo["dfs"])*len(self.dss)
        _cnt = 0
        _xnames = []
        _ynames = []
        for _k,_v in _plotinfo["dfs"].items():
            #fill all dataseries attrs with the attrs from the df:
            vars()["DF"] = vars()[_k]
            for _k2 in vars()[_k].keys():
                vars()[_k][_k2].attrs = {}
                for _k3,_v3 in vars()[_k].attrs.items():
                    vars()[_k][_k2].attrs[_k3]=_v3
            _scope = vars()
            _builtins = {"math":math, "np":np, "pd":pd, "funs": self.functions.funContainer}

            for _ds in self.dss:
                vars()["DS"] = _ds.items[DSHeader.name].text()
                _ydataexpr = _ds.items[DSHeader.Yfun].text()
                _triggerexpr = _ds.items[DSHeader.Xtrig].text()
                try: _ydata = eval(_ydataexpr, {'__builtins__': _builtins}, _scope)
                except: continue #if we didnt find anything
                _xdata = _ydata.index
                _xnames.append(_xdata.name)
                _ynames.append((_ds.items[DSHeader.name].text(),_k))
                if _triggerexpr:
                    try:
                        _trigvals = eval(_triggerexpr, {'__builtins__': _builtins}, _scope)
                        _xdata -= _trigvals.idxmax()
                    except: pass #if the expression was nonsense, ignore it
                
                #if we are here, we have a valid xdata and ydata we can collect
                _ydatas.append(_ydata)
                _xdatas.append(_xdata)
        
        #after collecting all the data, we can use ydats, xnames, ynames to construct our plot
        #the plotter plugins should return a subclass of __plotter__.SubPlot

        plotter = self.plottypes.plotterDict.get(self.dss[0].items[DSHeader.type].text())
        if not plotter: return
        plt = plotter.getPlot(_xdatas,_ydatas,_xnames,_ynames,_plotinfo,self.dss,_coordsystems)
        _widget.addItem(plt,row=_row,col=_col)

class Plotters():pass
class Functions():pass

class PlotterBibliothek():
    def __init__(self):
        self.context = {"info":None, "dss":None}
        self.dss = None
        self.plotterContainer = Plotters()
        self.plotterDict = {}

        for k,v in self.getPlotters().items():
            self.plotterDict[k] = v()
            self.plotterDict[k].context = self.context
            setattr(self.plotterContainer,k,self.plotterDict[k].getPlot)

    def setCurrentContext(self, plotinfo, dss):
        self.context["info"] = plotinfo
        self.context["dss"] = dss

    def getPlotters(self):
        plotterList = {}
        for k,v in inspect.getmembers(plotters, inspect.ismodule):
            if k.startswith("_"): continue
            else:
                try:plotter = v.Plotter
                except: pass
                plotterList[k.replace("plotter_","")] = plotter
        return plotterList

class FunctionBibliothek():
    def __init__(self):

        self.funContainer = Functions()
        self.funDict = {}

        for k,v in self.getFunctions().items():
            self.funDict[k] = v()
            setattr(self.funContainer,k,self.funDict[k].calc)

    def getFunctions(self):
        funList = {}
        for k,v in inspect.getmembers(functions, inspect.ismodule):
            if k.startswith("_"): continue
            else:
                try:function = v.Function
                except: pass
                funList[k.replace("function_","")] = function
        return funList

class Widget(pg.GraphicsLayoutWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.plotbib = PlotterBibliothek()
        self.funbib = FunctionBibliothek()