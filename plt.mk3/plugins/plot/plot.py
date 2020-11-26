import sys
import os.path as op
sys.path.append(op.abspath(op.join(op.dirname(__file__),"..")))
from __plugin__ import Plugin as _P
from __plugin__ import publicFun
from . import plotters
from .plotters import *
from PySide2 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
import pyqtgraph.exporters
import tempfile
import os
import math
import numpy as np
import pandas as pd
import inspect

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
        plotinfo = self.app.plugins["data"].getPlotInfo()
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
    def run(self):
        graphs = self.createLayout()
        self.plot(graphs)

    def createLayout(self):
        #plotinfo["dfs"] contains the dataframes that were selected
        #plotinfo["dss"] contains the dataseries that are plotted on at least one y axis

        graphs = []
        for idx in range(9):graphs.append(Graph(self.plottypes))

        for ds in self.plotinfo["dss"].values():
            yaxes = tuple(int(x)-1 for x in ds["Yax"].split(", "))
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
    def __init__(self, plottypes):
        self.dss = []
        self.plottypes = plottypes
    def buildgraph(self, _plotinfo, _widget, _row, _col, _coordsystems):
        #first, we get local variables for all dataframes:
        for _k,_v in _plotinfo["dfs"].items():
            if _k.startswith("DF"):
                vars()[_k] = _v
        #now we get a shortcut for all dataseries names:
        for _k,_ds in _plotinfo["dss"].items():
            if _k.startswith("DS"):
                vars()[_ds["#"]] = _ds["name"]
        
        #finally, loop over all dataframes again and use the shortcuts to plot the data:
        _L = len(_plotinfo["dfs"])*len(self.dss)
        _cnt = 0
        for _k,_v in _plotinfo["dfs"].items():
            vars()["DF"] = vars()[_k]
            _scope = vars()
            _builtins = {"math":math, "np":np, "pd":pd, "plots":self.plottypes.plotterContainer}
            _xnames = []
            _ynames = {}

            for _ds in self.dss:
                if not _ds["y=f(...)"].startswith("plots."): continue
                vars()["DS"] = _ds["name"]
                #lets do the special plots first. here,
                #the ydata expression returns a GraphicsLayoutWidget
                #this also means we dont do the rest of the loop
                #and instantly return instead.
                self.plottypes.setCurrentContext(_plotinfo, self.dss)
                _ydataexpr = _ds["y=f(...)"]
                _target = eval(_ydataexpr, {'__builtins__': _builtins}, _scope)
                _widget.addItem(_target,row=_row,col=_col)
                return _target

            _target = _widget.addPlot(row=_row,col=_col)
            _target.addLegend()
            _target.showGrid(x = True, y = True, alpha = 0.3)

            for _ds in self.dss:
                vars()["DS"] = _ds["name"]
                if _ds["y=f(...)"].startswith("plots."):
                    continue
                _ydataexpr = _ds["y=f(...)"]
                _triggerexpr = _ds["Trig"]
                try: _ydata = eval(_ydataexpr, {'__builtins__': _builtins}, _scope)
                except: continue #if we didnt find anything
                _xdata = _ydata.index
                _xnames.append(_xdata.name)
                _ynames[_ydata.name] = f"Y{len(_ynames)+1}"
                if _triggerexpr:
                    try:
                        _trigvals = eval(_triggerexpr, {'__builtins__': _builtins}, _scope)
                        _xdata -= _trigvals.idxmax()
                    except: pass #if the expression was nonsense, ignore it
                    
                _target.plot(x=_xdata,y=_ydata,pen=(_cnt,_L), name = f'{_ynames[_ydata.name]} @ {_k}')
                _cnt+=1

        _target.setLabel("bottom", "/ ".join(sorted(list(set(_xnames)))))
        _target.setLabel("left", "/ ".join(sorted(list(set([f"{k} ({v})" for k,v in _ynames.items()])))))
        if _coordsystems:_target.setXLink(_coordsystems[0])
        _coordsystems.append(_target)
        return _target

class Plotters():pass

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

    def spectogram(self, ydata):
        #spec = pg.GraphicsLayout()
        #X = [x*0.01 for x in range(0,500)]
        #Y= [math.sin(x) for x in X]
        #plot = spec.addPlot(0,0)
        #plot.plot(X,Y)
        return Plotter().getPlot()

class Widget(pg.GraphicsLayoutWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.plotbib = PlotterBibliothek()