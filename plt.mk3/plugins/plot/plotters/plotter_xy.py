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
        plt = self.addPlot()
        plt.addLegend()
        L = len(ydata)
        for idx,(X,Y,yname) in enumerate(zip(xdata,ydata,ynames)):
            comments = " / ".join(Y.attrs.get("comments",[]))
            nameAndComments = f"{yname[0]} {comments} @ {yname[1]}"
            plt.plot(x=X,y=Y,pen=(idx,L),name=nameAndComments)

        plt.setLabels(left=" / ".join(sorted(list(set(x[0] for x in ynames)))), bottom = " / ".join(sorted(list(set(xnames)))))
        plt.showGrid(x=True,y=True,alpha=0.3)
        #,, name = f'{_ynames[_ydata.name]} @ {_k}')
        #      _cnt+=1
        if sharedCoords:
            plt.setXLink(sharedCoords[0])
        sharedCoords.append(plt)
