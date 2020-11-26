import pyqtgraph as pg
from .__plotter__ import Plotter as _P
from scipy import fft
import numpy as np

class Plotter(_P):
    def getPlot(self,ds):
        L = pg.GraphicsLayout()
        FofT = L.addPlot(row=0, col=0)
        FofF = L.addPlot(row=1, col=0)
        region = pg.LinearRegionItem()
        
        FofT.plot(x=ds.index,y=ds.values)
        FofT.addItem(region)
        FofT.showGrid(x = True, y = True, alpha = 0.3)
        FofT.addLegend()
        FofF.showGrid(x = True, y = True, alpha = 0.3)
        FofF.addLegend()

        t0 = ds.index[0]
        t1 = ds.index[-1]
        dt = t1-t0
        region.setZValue(10)
        region.setRegion([t0+dt/3,t1-dt/3])
        region.sigRegionChanged.connect(self.updateRegion)

        self.data = ds
        self.FofF = FofF
        self.updateRegion(region)

        return L

    def updateRegion(self, range):
        x0x1 = range.getRegion()
        self.FofF.clearPlots()
        selectedData = self.data[x0x1[0]:x0x1[1]]
        N = len(selectedData)
        T = selectedData.index[1]-selectedData.index[0]
        yf = 2.0/N * np.abs(fft.fft(selectedData.values)[0:N//2])
        xf = np.linspace(0.0, 1.0/(2.0*T),N//2)
        
        self.FofF.plot(x=xf[1:],y=yf[1:])
