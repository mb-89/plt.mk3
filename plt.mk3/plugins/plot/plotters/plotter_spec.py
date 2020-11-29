from PySide2 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
from scipy import signal
from .__plotter__ import Plotter as _P
from .__plotter__ import SubPlot as _SP
import numpy as np
import math
import pandas as pd
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
from pyqtgraph import mkPen

class Plotter(_P):
    def getPlot(self, X, Y, Xnames, Ynames, plotinfo, selectedSeries, sharedCoords):
        return SubPlot(X,Y,Xnames,Ynames,sharedCoords) 

class SubPlot(_SP):
    def __init__(self, xdata, ydata, xnames, ynames, sharedCoords):
        super().__init__(xdata[0], ydata[0], xnames[0], ynames[0], sharedCoords)
        self.windowLenRel = 4
        self.windowOverlapRel = 4
        self.windowLenBase = 256
        self.addSpecPlot()
        self.layout.setRowStretchFactor(0,3)

    def calc(self):
        Y=self.ydata
        T=self.xdata
        L = len(T)
        WL = int(self.windowLenBase*self.windowLenRel)
        self.f, self.t, self.Sxx = signal.spectrogram(
                np.array(Y), 
                1/((T[-1]-T[0])/L),
                scaling = 'spectrum',
                mode='magnitude',
                nperseg= WL,
                noverlap=int(WL/8*self.windowOverlapRel))
        self.Sxx*=2.0

    def addSpecPlot(self):
        #self.p2 = pg.ViewBox()
        self.p1 = self.addPlot(row=0,col=0,rowspan=2)
        #self.p2 = self.addPlot(row=5,col=0)
        
        img = pg.ImageItem()
        img.setOpts(axisOrder='row-major')
        self.img = img
        self.p1.addItem(img)
        hist = pg.HistogramLUTItem()
        hist.setImageItem(img)
        self.addItem(hist,row=0,col=1,rowspan=1)
        self.hist = hist
        #self.addTimePlot()
        self.redraw()
        self.addWidgets()
        #self.p1.vb.sigResized.connect(self.updateViews)
        if self.sharedCoords:
            self.p1.setXLink(self.sharedCoords[0])
        self.sharedCoords.append(self.p1)


    def addTimePlot(self):
        plt=self.p2.plot(x=self.xdata, y=self.ydata)
        self.p2.showGrid(x=True,y=True,alpha=0.3)
        self.p2.setXLink(self.p1)

    def setWindowLen(self, len):
        self.windowLenRel = len
        self.redraw()

    def setWindowOverlap(self, len):
        self.windowOverlapRel = len
        self.redraw()

    def redraw(self):
        self.calc()
        # Sxx contains the amplitude for each pixel
        self.img.setImage(self.Sxx)

        # Scale the X and Y Axis to time and frequency (standard is pixels)
        self.img.resetTransform()
        self.img.scale(self.t[-1]/np.size(self.Sxx, axis=1),
                self.f[-1]/np.size(self.Sxx, axis=0))
        #self.hist.setLevels(np.min(self.Sxx), np.percentile(self.Sxx,97))
        self.hist.gradient.restoreState(
                {'mode': 'rgb',
                'ticks': [(0.8, (0, 182, 188, 255)),
                        (1.0, (246, 111, 0, 255)),
                        (0.0, (75, 0, 113, 255))]})

        # Limit panning/zooming to the spectrogram
        self.p1.setLimits(xMin=0, xMax=self.t[-1], yMin=0, yMax=self.f[-1])
        for x in self.p1.axes:
            ax = self.p1.getAxis(x)
            ax.setZValue(1)
        # Add labels to the axis
        # If you include the units, Pyqtgraph automatically scales the axis and adjusts the SI prefix (in this case kHz)
        self.p1.setLabel('left', "Frequency", units='Hz')
        self.p1.showGrid(True,True,1)

        #overlay the time values
        #QtCore.QTimer.singleShot(0,self.addYoverlay)

    ## Handle view resizing 
    def updateViews(self):
        ## view has resized; update auxiliary views to match
        self.p2.setGeometry(self.p1.vb.sceneBoundingRect())
        ## need to re-update linked axes since this was called
        ## incorrectly while views had different shapes.
        ## (probably this should be handled in ViewBox.resizeEvent)
        self.p2.linkedViewChanged(self.p1.vb, self.p2.XAxis)

    def addYoverlay(self):
        self.p1.showAxis('right')
        self.p1.scene().addItem(self.p2)
        self.p1.getAxis('right').linkToView(self.p2)
        self.p2.setXLink(self.p1)
        #p2.plot(self.xdata,self.ydata,pen=mkPen('y', width=1, style=QtCore.Qt.DashLine) )
        self.p2.addItem(pg.PlotCurveItem(y=self.ydata.values,x=self.xdata.values, pen='y'))

    def addWidgets(self):
        slidercontainer = QtWidgets.QGraphicsProxyWidget()
        slidercontainerWidget = QtWidgets.QWidget()
        L = QtWidgets.QHBoxLayout()

        LL = QtWidgets.QVBoxLayout()
        LL.setSpacing(0)
        LL.setContentsMargins(0,0,0,0)
        windowlenslider = QtWidgets.QSlider(QtCore.Qt.Orientation.Vertical)
        windowlenslider.setMinimum(1)
        windowlenslider.setMaximum(8)
        windowlenslider.setValue(4)
        windowlenslider.valueChanged.connect(self.setWindowLen)
        LL.addWidget(QtWidgets.QLabel('<font color="#FFFFFF"><b>WL</b></font>'))
        LL.addWidget(windowlenslider)

        OL = QtWidgets.QVBoxLayout()
        OL.setSpacing(0)
        OL.setContentsMargins(0,0,0,0)
        windowoverlapslider = QtWidgets.QSlider(QtCore.Qt.Orientation.Vertical)
        windowoverlapslider.setMinimum(1)
        windowoverlapslider.setMaximum(8)
        windowoverlapslider.setValue(4)
        windowoverlapslider.valueChanged.connect(self.setWindowOverlap)
        OL.addWidget(QtWidgets.QLabel('<font color="#FFFFFF"><b>OL</b></font>'))
        OL.addWidget(windowoverlapslider)

        L.addItem(QtWidgets.QSpacerItem(10,10,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding))
        L.addLayout(LL)
        L.addLayout(OL)
        L.addItem(QtWidgets.QSpacerItem(10,10,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding))

        L.setSpacing(0)
        L.setContentsMargins(0,0,0,0)
        slidercontainerWidget.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        slidercontainerWidget.setLayout(L)
        slidercontainer.setWidget(slidercontainerWidget)
        self.addItem(slidercontainer,row=1, col=1,rowspan=1)