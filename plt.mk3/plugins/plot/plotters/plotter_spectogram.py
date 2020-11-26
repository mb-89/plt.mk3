from PySide2 import QtCore, QtWidgets, QtGui
import pyqtgraph as pg
from scipy import signal
from .__plotter__ import Plotter as _P
import numpy as np
import math
import pandas as pd

class Plotter(_P):
    def getPlot(self,ds=None):
        return Spectogram()

class Spectogram(pg.GraphicsLayout):
    def __init__(self):
        super().__init__()
        self.T,self.Y = self.buildExampleDataFrame()
        self.f, self.t, self.Sxx = self.calcSpec(self.T,self.Y,1024,128)

        self.addSpectogramElements()
        self.addTimePlotAndOptions()
        self.addROIplot()

        self.redraw()
        self.drawreforder(1)
        self.fliproi()

        qGraphicsGridLayout = self.ci.layout
        qGraphicsGridLayout.setRowStretchFactor(0, 2)
        qGraphicsGridLayout.setRowStretchFactor(1, 1)
        qGraphicsGridLayout.setRowStretchFactor(2, 1)

    def calcSpec(self,T,Y,N,ol):
        f, t, Sxx = signal.spectrogram(
                np.array(Y), 
                1/(T[1]-T[0]),
                nperseg = N,
                noverlap = ol,
                scaling = 'spectrum',
                mode='magnitude')
        return f, t, Sxx

    def addSpectogramElements(self):
        p1 = self.addPlot(row=0,col=0)
        img = pg.ImageItem()
        img.setOpts(axisOrder='row-major')
        self.img = img
        p1.addItem(img)
        self.refplot = p1.plot([0],[0],pen=pg.mkPen('r'))
        #self.roi = pg.PolyLineROI([[0,0],[1,1]],closed=False,movable=False)
        #p1.addItem(self.roi)
        hist = pg.HistogramLUTItem()
        hist.setImageItem(img)
        self.addItem(hist)
        self.hist = hist

        # Sxx contains the amplitude for each pixel
        img.setImage(self.Sxx)
        # Scale the X and Y Axis to time and frequency (standard is pixels)
        img.scale(self.t[-1]/np.size(self.Sxx, axis=1),
                self.f[-1]/np.size(self.Sxx, axis=0))
        # Limit panning/zooming to the spectrogram
        self.p1 = p1
        p1.setLimits(xMin=0, xMax=self.t[-1], yMin=0, yMax=500)
        for x in p1.axes:
            ax = p1.getAxis(x)
            ax.setZValue(1)
        # Add labels to the axis
        # If you include the units, Pyqtgraph automatically scales the axis and adjusts the SI prefix (in this case kHz)
        p1.setLabel('left', "Frequency", units='Hz')
        p1.showGrid(True,True,1)
    
    def buildExampleDataFrame(self):
        T = np.arange(0,30,0.0002)
        Y = [0 for x in T]
        Sig = SignalLib()
        Sig.addRamp(T,Y,1,9,2500)
        Sig.addRamp(T,Y,20,9,-2500)

        h1      = Sig.addHarmonic(T,Y,0.1,10, doNotApply=True)
        h2      = Sig.addHarmonic(T,Y,0.2,10, doNotApply=True)
        dist1   = Sig.addFixedFreqSin(T,10,5,50,1, doNotApply=True)
        dist2   = Sig.addResonance(T,Y,750, 0.4, 50,50, doNotApply=True)

        #smallramp = Sig.addRamp(T,Y,2,3,300, doNotApply=True)
        #Sig.addRamp(T,smallramp,5,3,-300)

        np.random.seed(19680801)
        Y = Sig.Sum(Y,0.01 * np.random.random(size=len(T)))
        Y = Sig.Sum(Y,h1)
        Y = Sig.Sum(Y,h2)
        Y = Sig.Sum(Y,dist1)
        Y = Sig.Sum(Y,dist2)

        df = pd.DataFrame({'Time_s':T, 'speed':Y})
        df.set_index("Time_s", inplace=True)
        df.to_csv("spec.csv")

        return T,Y

    def addTimePlotAndOptions(self):
        p2 = self.addPlot(row=1,col=0)
        p2.setXLink(self.p1)
        p2.plot(self.T,self.Y)
        p2.showGrid(True,True,1)
        p2.setLabel('bottom', "Time", units='s')
        p2.setLabel('left', "speed", units='rpm')

        buttoncontainer = QtWidgets.QGraphicsProxyWidget()
        buttoncontainerWidget = QtWidgets.QWidget()
        L = QtWidgets.QVBoxLayout()

        WindowLabel = QtWidgets.QLabel("<font color='white'>window</font>")
        Windowsize = QtWidgets.QLineEdit()
        Windowsize.setText("1024")
        Windowsize.setReadOnly(True)
        Windowsize.setMaximumWidth(30)
        Windowsize.textChanged.connect(self.redraw)
        Windowsizeplus = QtWidgets.QPushButton("++")
        Windowsizeplus.setMaximumWidth(25)
        Windowsizeplus.clicked.connect(lambda:self.Windowsize.setText(str(int(self.Windowsize.text())*2)))
        Windowsizeminus = QtWidgets.QPushButton("--")
        Windowsizeminus.setMaximumWidth(25)
        Windowsizeminus.clicked.connect(lambda:self.Windowsize.setText(str(int(self.Windowsize.text())//2)))
        L0 = QtWidgets.QHBoxLayout()
        L0.setSpacing(0)
        L0.setContentsMargins(0,0,0,0)
        L0.addWidget(WindowLabel)
        L0.addWidget(Windowsize)
        L0.addWidget(Windowsizeminus)
        L0.addWidget(Windowsizeplus)
        self.Windowsize=Windowsize

        OverlapLabel = QtWidgets.QLabel("<font color='white'>overlap</font>")
        Overlapsize = QtWidgets.QLineEdit()
        Overlapsize.setText("128")
        Overlapsize.setReadOnly(True)
        Overlapsize.setMaximumWidth(30)
        Overlapsize.textChanged.connect(self.redraw)
        Overlapsizeplus = QtWidgets.QPushButton("++")
        Overlapsizeplus.setMaximumWidth(25)
        Overlapsizeplus.clicked.connect(lambda:self.Overlapsize.setText(str(int(self.Overlapsize.text())*2)))
        Overlapsizeminus = QtWidgets.QPushButton("--")
        Overlapsizeminus.setMaximumWidth(25)
        Overlapsizeminus.clicked.connect(lambda:self.Overlapsize.setText(str(int(self.Overlapsize.text())//2)))
        L1 = QtWidgets.QHBoxLayout()
        L1.setSpacing(0)
        L1.setContentsMargins(0,0,0,0)
        L1.addWidget(OverlapLabel)
        L1.addWidget(Overlapsize)
        L1.addWidget(Overlapsizeminus)
        L1.addWidget(Overlapsizeplus)
        self.Overlapsize=Overlapsize

        OrderLabel = QtWidgets.QLabel("<font color='white'>ref order</font>")
        currOrder = QtWidgets.QDoubleSpinBox()
        currOrder.setValue(1.0)
        currOrder.setSingleStep(0.1)
        currOrder.valueChanged.connect(self.drawreforder)
        L2 = QtWidgets.QHBoxLayout()
        L2.setSpacing(0)
        L2.setContentsMargins(0,0,0,0)
        L2.addWidget(OrderLabel)
        L2.addWidget(currOrder)

        HPLabel = QtWidgets.QLabel("<font color='white'>HP freq</font>")
        HPfreq = QtWidgets.QDoubleSpinBox()
        HPfreq.setMaximum(501)
        HPfreq.setMinimum(0)
        HPfreq.setValue(10)
        HPfreq.setSingleStep(10)
        HPfreq.valueChanged.connect(self.redraw)
        L3 = QtWidgets.QHBoxLayout()
        L3.setSpacing(0)
        L3.setContentsMargins(0,0,0,0)
        L3.addWidget(HPLabel)
        L3.addWidget(HPfreq)
        self.HPfreq=HPfreq

        LPLabel = QtWidgets.QLabel("<font color='white'>LP freq</font>")
        LPfreq = QtWidgets.QDoubleSpinBox()
        LPfreq.setMaximum(501)
        LPfreq.setMinimum(0)
        LPfreq.setValue(501)
        LPfreq.setSingleStep(10)
        LPfreq.valueChanged.connect(self.redraw)
        L4 = QtWidgets.QHBoxLayout()
        L4.setSpacing(0)
        L4.setContentsMargins(0,0,0,0)
        L4.addWidget(LPLabel)
        L4.addWidget(LPfreq)
        self.LPfreq=LPfreq

        L.addLayout(L0)
        L.addLayout(L1)
        L.addLayout(L2)
        L.addLayout(L3)
        L.addLayout(L4)
        L.addItem(QtWidgets.QSpacerItem(10,10,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding))

        L.setSpacing(0)
        L.setContentsMargins(0,0,0,0)
        buttoncontainerWidget.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        buttoncontainerWidget.setLayout(L)
        buttoncontainer.setWidget(buttoncontainerWidget)
        #cont = self.addItem(buttoncontainer,row=1, col=1)

        qGraphicsGridLayout = self.ci.layout
        qGraphicsGridLayout.setRowStretchFactor(0, 2)
        qGraphicsGridLayout.setRowStretchFactor(1, 1)
        qGraphicsGridLayout.setRowStretchFactor(2, 2)

        self.plt = self.img

    def drawreforder(self,x=None, updateCall=False):
        if x is None: x = self.lastOrder
        self.lastOrder = x
        def freqreflect(x):
            while True:
                gt = x>500
                lt = x<0
                if not gt and not lt: break
                if gt:x = 500-(x-500)
                else: x=-x
            return x

        Y = [freqreflect(abs(y)*SIG2HZ*x) for y in self.relevantYs]
        self.refOrder=Y
        try:self.refplot.setData(self.relevantTs,Y)
        except AttributeError: return

        self.updateroi()

    def redraw(self):
        self.calc()
        self.plt.setImage(self.Sxx)

        # Fit the min and max levels of the histogram to the data available
        self.hist.setLevels(np.min(self.Sxx), np.percentile(self.Sxx,97))
        # This gradient is roughly comparable to the gradient used by Matplotlib
        # You can adjust it and then save it using hist.gradient.saveState()
        self.hist.gradient.restoreState(
                {'mode': 'rgb',
                'ticks': [(0.8, (0, 182, 188, 255)),
                        (1.0, (246, 111, 0, 255)),
                        (0.0, (75, 0, 113, 255))]})

        # Scale the X and Y Axis to time and frequency (standard is pixels)
        self.plt.resetTransform()
        self.plt.scale(self.t[-1]/np.size(self.Sxx, axis=1),self.f[-1]/np.size(self.Sxx, axis=0))
        # Limit panning/zooming to the spectrogram
        self.p1.setLimits(xMin=0, xMax=self.t[-1], yMin=0, yMax=500)
        self.updateroi()

    def updateroi(self):
        #if self.rel2Order:
        if False:
            L = self.Sxx.shape[1]
            y = [floor(x/500.0*L) for x in self.refOrder]
            f = [self.Sxx[idx,x] for idx,x in enumerate(y)]
            self.p3.plot(self.relevantTs,f, clear=True)
        else:
            selected = self.roi.getArrayRegion(self.Sxx, self.plt)
            x = self.t if self.roiHori else self.f
            y = selected.mean(axis=0 if self.roiHori else 1)
            L = min(len(x),len(y))
            self.p3.plot(x[:L],y[:L], clear=True)

        #inf line:
        if not self.roiHori:
            t = self.roi.pos()[0]
            f = np.interp(t,self.relevantTs,self.refOrder)
            isoLine = pg.InfiniteLine(pos=f,angle=90, movable=False, pen='r')
            self.p3.addItem(isoLine)

        self.p3.autoRange()
        if self.roiHori:    self.p3.setLabel('bottom', "Time", units='s')
        else:               self.p3.setLabel('bottom', "Freq", units='Hz')

    def fliproi(self,hori=False, rel2Order = False):
        self.roi.setPos(self.roibounds[f"x0y0_{'v' if not hori else 'h'}"])
        self.roi.setSize(self.roibounds[f"wh_{'v' if not hori else 'h'}"])
        self.roiHori = hori
        self.rel2Order = rel2Order
        self.updateroi()

    def addROIplot(self):
        p3 = self.addPlot(row=2,col=0)
        self.roiplot = p3.plot([0,0],[0,1])
        p3.showGrid(True,True,1)

        p3.setLabel('left', "Ampl at ROI", units='rpm')
        self.roibounds = {
            "x0y0_h": [self.T[0], 250],
            "wh_h": [(self.T[-1]-self.T[0])-1, 1],

            "x0y0_v": [(self.T[-1]-self.T[0])/2.0+self.T[0], 1],
            "wh_v": [(self.T[2]-self.T[0]), 499]
        }
        self.roiHori = True
        #self.roi = pg.ROI([self.T[-1]/2.0, 0], [(self.T[2]-self.T[0]), 499], pen='r',movable=False,
        self.roi = pg.ROI(self.roibounds["x0y0_v"], self.roibounds["wh_v"], pen='r',movable=False,
        maxBounds=QtCore.QRect(
            self.T[0],
            0,
            self.T[-1]-self.T[0],
            500))
        self.roi.addTranslateHandle((0.5,0.5))
        self.p1.addItem(self.roi)
        self.roi.sigRegionChanged.connect(self.updateroi)
        self.p3 = p3

        buttoncontainer = QtWidgets.QGraphicsProxyWidget()
        buttoncontainerWidget = QtWidgets.QWidget()
        L = QtWidgets.QVBoxLayout()
        ROI_H_Button = QtWidgets.QPushButton('ROI hori')
        ROI_H_Button.clicked.connect(lambda:self.fliproi(True))
        L.addWidget(ROI_H_Button)
        ROI_V_Button = QtWidgets.QPushButton('ROI vert')
        ROI_V_Button.clicked.connect(lambda:self.fliproi(False))
        L.addWidget(ROI_V_Button)
        ROI_O_Button = QtWidgets.QPushButton('ROI ref order')
        ROI_O_Button.clicked.connect(lambda:self.fliproi(True,True))
        L.addWidget(ROI_O_Button)
        L.addItem(QtWidgets.QSpacerItem(10,10,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding))

        L.setSpacing(0)
        L.setContentsMargins(0,0,0,0)
        buttoncontainerWidget.setAttribute(QtCore.Qt.WA_NoSystemBackground)

        buttoncontainerWidget.setLayout(L)
        buttoncontainer.setWidget(buttoncontainerWidget)

        self.addItem(buttoncontainer,row=2, col=1)

    def drawreforder(self,x=None, updateCall=False):
        if x is None: x = self.lastOrder
        self.lastOrder = x
        def freqreflect(x):
            while True:
                gt = x>500
                lt = x<0
                if not gt and not lt: break
                if gt:x = 500-(x-500)
                else: x=-x
            return x

        Y = [freqreflect(abs(y)*SIG2HZ*x) for y in self.relevantYs]
        self.refOrder=Y
        #Y = [abs(y)/60.0*x for y in self.relevantYs]
        
        #self.updateroi()
        #Y = [abs(y)/60.0*x for y in self.Y]

        #Lt = len(self.t)-1
        #Lf = len(self.f)-1
        #F = [self.Sxx[f,t] for t,f in zip(
        #    [min(np.searchsorted(self.t, tt),Lt) for tt in self.T],
        #    [min(np.searchsorted(self.f, ff),Lf) for ff in Y]
        #    )]
        #self.roi.setPoints([(x,y) for x,y in zip(self.T[::10000],Y[::10000])])
        try:self.refplot.setData(self.relevantTs,Y)
        except AttributeError: return

        self.updateroi()
        #self.roiplot.setData(self.T,F)

class SignalLib():
    def addRamp(self, T,Y, startTime, dt, endVal, doNotApply = False):
        newsig = [0 for x in Y]
        for idx,t in enumerate(T):
            trel = max(0.0,min(1.0,(t-startTime)/dt))
            newsig[idx] += trel*endVal

        if doNotApply:return newsig
        for idx, x in enumerate(newsig):
            Y[idx] += x
        return newsig

    def Sum(self,s1,s2):
        return [x+y for x,y in zip(s1, s2)]

    def addHarmonic(self, T, Y, order, amp, doNotApply = False):
        newsig = [0 for x in Y]
        freqs = [0 for x in Y]
        freqInts = [0 for x in Y]
        lastFreqInt = 0
        dt = (T[1]-T[0])
        for idx,(t,y) in enumerate(zip(T,Y)):
            freq = y*order
            freqs[idx] = freq
            freqInts[idx] = lastFreqInt+freqs[idx]*dt
            lastFreqInt = freqInts[idx]
            ft = lastFreqInt*2*math.pi
            val = math.sin(ft)*amp
            newsig[idx] = val
        if doNotApply:return newsig
        for idx, x in enumerate(newsig):
            Y[idx] += x
        return newsig

    def addFixedFreqSin(self, T, starttime, dt, freq, amp, doNotApply = False):
        newsig = [0 for x in T]

        for idx,t in enumerate(T):
            if t<starttime: continue
            if t>starttime+dt: continue
            newsig[idx] = math.sin((t-starttime)*freq*2*math.pi)*amp
        if doNotApply:return newsig
        for idx, x in enumerate(newsig):
            Y[idx] += x
        return newsig

    def addResonance(self, T,Y, midfreq, order, range, amp, doNotApply = False):
        newsig = [0 for x in Y]

        for idx,(t,y) in enumerate(zip(T,Y)):
            if y<(midfreq-range): continue
            if y>(midfreq+range): continue
            relAmp = (range-abs(midfreq-y))/range
            newsig[idx] = math.sin(t*midfreq*order*2*math.pi)*amp*relAmp
        if doNotApply:return newsig
        for idx, x in enumerate(newsig):
            Y[idx] += x
        return newsig