import pyqtgraph as pg
from .__plotter__ import Plotter as _P
from .__plotter__ import SubPlot as _SP
from scipy import fft
import numpy as np

class Plotter(_P):
    def getPlot(self, X, Y, Xnames, Ynames, plotinfo, selectedSeries, sharedCoords):
        return SubPlot(X,Y,Xnames,Ynames,sharedCoords) 

class SubPlot(_SP):
    def __init__(self, xdata, ydata, xnames, ynames, sharedCoords):
        super().__init__(xdata, ydata, xnames, ynames, sharedCoords)
        self.tplt = self.buildTimePlot()
        self.fplt = self.buildFreqPlot()

        self.layout.setRowStretchFactor(1,2)
        self.updateRegion(self.region)

    def buildTimePlot(self):
        tplt = self.addPlot(col=0,row=0)
        tplt.addLegend()
        L = len(self.ydata)
        t0 = []
        t1 = []
        self.tplots = []
        for idx,(X,Y,yname) in enumerate(zip(self.xdata,self.ydata,self.ynames)):
            comments = " / ".join(Y.attrs.get("comments",[]))
            nameAndComments = f"{yname[0]} {comments} @ {yname[1]}"
            self.tplots.append(tplt.plot(x=X,y=Y,pen=(idx,L),name=nameAndComments))
            t0.append(min(X))
            t1.append(max(X))
        t0=min(t0)
        t1=max(t1)

        tplt.setLabels(
            left=" / ".join(sorted(list(set(x[0] for x in self.ynames)))), 
            bottom = " / ".join(sorted(list(set(self.xnames))))
        )
        tplt.showGrid(x=True,y=True,alpha=0.3)

        dt = t1-t0
        region = pg.LinearRegionItem()
        region.setZValue(10)
        region.setRegion([t0+dt/3,t1-dt/3])
        region.sigRegionChanged.connect(self.updateRegion)
        tplt.addItem(region)
        self.region = region

        if self.sharedCoords:
            tplt.setXLink(self.sharedCoords[0])
        self.sharedCoords.append(tplt)
        return tplt

    def buildFreqPlot(self):
        fplt = self.addPlot(col=0,row=1)
        fplt.addLegend()
        fplt.showGrid(x=True,y=True,alpha=0.3)
        return fplt

    def updateRegion(self, range):
        x0x1 = range.getRegion()
        self.fplt.clearPlots()
        L = len(self.tplots)
        for idx,tplt in enumerate(self.tplots):
            selectedData = tplt.getData()
            mask = np.logical_and(selectedData[0]>=x0x1[0],selectedData[0]<=x0x1[1])
            X = selectedData[0][mask]
            Y = selectedData[1][mask]
            N = len(X)
            T = (X[-1]-X[0])/N
            yf = 2.0/N * np.abs(fft.fft(Y)[0:N//2])
            xf = np.linspace(0.0, 1.0/(2.0*T),N//2)
            self.fplt.plot(x=xf[1:],y=yf[1:],pen=(idx,L))


