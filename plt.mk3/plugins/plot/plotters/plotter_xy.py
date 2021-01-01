import pyqtgraph as pg
from .__plotter__ import Plotter as _P
from .__plotter__ import SubPlot as _SP
from scipy import fft
import numpy as np
from PySide2 import QtCore,QtWidgets,QtGui
import pandas as pd
from scipy import signal
from pyqtgraph import functions as fn
from functools import partial


class Plotter(_P):
    def getPlot(self, X, Y, Xnames, Ynames, plotinfo, selectedSeries, sharedCoords):
        return SubPlot(X,Y,Xnames,Ynames,sharedCoords) 

class SubPlot(_SP):
    def __init__(self, xdata, ydata, xnames, ynames, sharedCoords):
        super().__init__(xdata, ydata, xnames, ynames, sharedCoords)
        
        addonList = [Addon_Buttons, Addon_meas, Addon_xy, Addon_fft, Addon_spec]
        self.addons = dict( (x.name,x(self)) for x in addonList)

        for k,v in self.addons.items():self.addRowColList(v.getGuiElements())
        for k,v in self.addons.items():v.resolveConnections()

class Addon(QtCore.QObject):
    name = "Addon"
    row = 0
    def __init__(self, parent):
        super().__init__()
        self.parent = parent

    def toggle(self):
        pass

    def getGuiElements(self):
        return []

    def resolveConnections(self):
        pass

    def updateData(self,data):
        pass

class Addon_Buttons(Addon):
    name = "buttons"
    def __init__(self, parent):
        super().__init__(parent)
        buttonnames = ["meas","xy","fft","spec","xcor"]
        self.buttons = dict( (x,QtWidgets.QPushButton(x)) for x in buttonnames )
        for k,v in self.buttons.items():
            v.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            v.setStyleSheet(f"QPushButton{{{self.parent.style}}}")
    
    def getGuiElements(self):
        return list(self.buttons.values())

class Addon_xy(Addon):
    name = "xy"
    startHidden = False
    shareCoords = True
    def __init__(self, parent):
        super().__init__(parent)
        self.plt = pg.PlotItem()
        self.plt.setVisible(not self.startHidden)
        self.plt.setLabels(left=" / ".join(sorted(list(set(x[0] for x in self.parent.ynames)))), bottom = " / ".join(sorted(list(set(self.parent.xnames)))))
        self.plt.showGrid(x=True,y=True,alpha=1)
        if self.shareCoords:
            if self.parent.sharedCoords:
                self.plt.setXLink(self.parent.sharedCoords[0])
            self.parent.sharedCoords.append(self.plt)

    def getGuiElements(self):
        return [self.plt]

    def resolveConnections(self):
        self.parent.addons["buttons"].buttons[self.name].clicked.connect(self.toggle)

    def toggle(self):
        hidden = not self.plt.isVisible()
        self.plt.setVisible(hidden)

    def updateData(self, df):
        self.plt.clearPlots()
        self.plt.addLegend()
        L = len(df.columns)

        for idx,colname in enumerate(df.columns):
            self.parent.lines[colname] = self.plt.plot(y=df[colname],x=df[colname].index,pen=(idx,L),name=colname)

class Addon_fft(Addon_xy):
    name = "fft"
    startHidden = True
    shareCoords = False

    def resolveConnections(self):
        super().resolveConnections()

        timeplot = self.parent.addons["xy"].plt
        specplot = self.parent.addons["spec"].plt
        df = self.parent.df
        R = pg.LinearRegionItem()
        R.lines[0].label = pg.InfLineLabel(R.lines[0],text="FFT",position=.95,movable=False)
        #R.lines[1].label = pg.InfLineLabel(R.lines[1],text="FFT",position=.95,movable=False)
        R.setZValue(10)
        t0 = df.index[0]
        t1 = df.index[-1]
        dt = t1-t0
        R.setRegion([t0+dt/3,t1-dt/3])
        R.sigRegionChanged.connect(self.updateFFTRegion)
        timeplot.addItem(R)
        self.FFTregion = R
        self.FFTregion.setVisible(not self.startHidden)

        R2 = pg.LinearRegionItem()
        R2.lines[0].label = pg.InfLineLabel(R2.lines[0],text="FFT",position=.95,movable=False)
        R2.setZValue(10)
        t0 = df.index[0]
        t1 = df.index[-1]
        dt = t1-t0
        R2.setRegion([t0+dt/3,t1-dt/3])
        specplot.addItem(R2)
        self.specregion = R2
        self.specregion.setVisible(not self.startHidden)

        R.sigRegionChanged.connect(self.updateR2)
        R2.sigRegionChanged.connect(self.updateR1)

    def updateR2(self, reg):self.specregion.setRegion(reg.getRegion())
    def updateR1(self, reg):self.FFTregion.setRegion(reg.getRegion())

    def toggle(self):
        super().toggle()
        visible = self.plt.isVisible()
        if visible:self.updateFFTRegion()
        self.FFTregion.setVisible(visible)
        self.specregion.setVisible(visible)

    def updateData(self, df): self.updateFFTRegion()
    def updateFFTRegion(self, range = None):
        if not self.plt.isVisible():return
        tplt = self.parent.addons["xy"].plt
        if not tplt.isVisible():return
        if range is None: range = self.FFTregion

        x0x1 = range.getRegion()
        self.plt.clearPlots()
        L = len(self.parent.lines)
        for idx,tplt in enumerate(self.parent.lines.values()):
            selectedData = tplt.getData()
            mask = np.logical_and(selectedData[0]>=x0x1[0],selectedData[0]<=x0x1[1])
            X = selectedData[0][mask]
            Y = selectedData[1][mask]
            N = len(X)
            T = (X[-1]-X[0])/N
            yf = 2.0/N * np.abs(fft.fft(Y)[0:N//2])
            xf = np.linspace(0.0, 1.0/(2.0*T),N//2)
            self.plt.plot(x=xf[1:],y=yf[1:],pen=(idx,L))
        
        timeplot = self.parent.addons["xy"].plt
        self.plt.setLabels(
                bottom="ℱ{ "+timeplot.axes["bottom"]["item"].label.toPlainText()+"}"+f" [range: {X[0]:.3f} to {X[-1]:.3f}]"
                )

class Addon_spec(Addon_xy):
    name = "spec"
    startHidden = True

    windowLenRel = 4
    windowOverlapRel = 4
    windowOverlap = 1024/8*4
    windowLenBase = 256
    windowLen = 1024

    def __init__(self, parent):
        super().__init__(parent)
        self.dataCol = 0
        self.img = pg.ImageItem()
        self.img.setOpts(axisOrder='row-major')
        self.hist = HoriHist()
        self.plt.addItem(self.img)
        self.hist.setImageItem(self.img)
        self.hist.setVisible(not self.startHidden)
        self.options = self.buildOptions()
        self.options.setVisible(not self.startHidden)

    def calc(self,df):
        col =df.columns[self.dataCol]
        Y=df[col].values
        T=df.index.values
        L = len(T)

        self.windowLen = int(self.windowLenBase*self.windowLenRel)
        self.windowOverlap = int(self.windowLen/8*self.windowOverlapRel)
        self.opt_overlay.setText(f"Window overlap: {self.windowOverlap}")
        self.opt_windowlen.setText(f"Window len: {self.windowLen}")
        for proxy in self.parent.proxys:
            proxy.update()
            proxy.updateGeometry()

        self.f, self.t, self.Sxx = signal.spectrogram(
                Y, 
                1/((T[-1]-T[0])/L),
                scaling = 'spectrum',
                mode='magnitude',
                nperseg= self.windowLen,
                noverlap=self.windowOverlap)
        self.Sxx*=2.0

    def updateData(self, df = None):
        if df is None:df = self.parent.df
        self.calc(df)
        # Sxx contains the amplitude for each pixel
        self.img.setImage(self.Sxx)

        # Scale the X and Y Axis to time and frequency (standard is pixels)
        self.img.resetTransform()
        self.img.scale(self.t[-1]/np.size(self.Sxx, axis=1),
                self.f[-1]/np.size(self.Sxx, axis=0))
        self.hist.setLevels(np.min(self.Sxx), np.percentile(self.Sxx,97))

        # Limit panning/zooming to the spectrogram
        t1 = df.index[-1]
        t0 = df.index[0]
        freq = len(df.index)/(t1-t0)
        self.plt.setLimits(yMin=0, yMax=freq/2.0)
        for x in self.plt.axes:
            ax = self.plt.getAxis(x)
            ax.setZValue(1)

        timeplot = self.parent.addons["xy"].plt
        col = df.columns[0]
        self.plt.setLabels(left=f"ℱ{{{col}}}", bottom=timeplot.axes["bottom"]["item"].label.toPlainText())

    def getGuiElements(self):
        return [[
            self.plt, 
            [[self.options],[self.hist]]
        ]]

    def resolveConnections(self):
        super().resolveConnections()

    def toggle(self):
        hidden = not self.plt.isVisible()
        if hidden:self.updateData()
        self.plt.setVisible(hidden)
        self.hist.setVisible(hidden)
        self.options.setVisible(hidden)

    def buildOptions(self):
        W = QtWidgets.QWidget()
        L = QtWidgets.QGridLayout()
        W.setLayout(L)

        L.setSpacing(0)
        L.setContentsMargins(0,0,0,0)

        R   = QtWidgets.QPushButton("<");R.setStyleSheet(f"QPushButton{{{self.parent.style}}}")
        Lbl = QtWidgets.QLabel(self.parent.df.columns[self.dataCol]);Lbl.setMaximumWidth(600);Lbl.setStyleSheet(f"QLabel{{{self.parent.style}}}")
        F   = QtWidgets.QPushButton(">");F.setStyleSheet(f"QPushButton{{{self.parent.style}}}")
        R.clicked.connect(lambda:self.setDataCol(-1))
        F.clicked.connect(lambda:self.setDataCol(1))
        self.opt_datacol = Lbl

        OLR   = QtWidgets.QPushButton("<");OLR.setStyleSheet(f"QPushButton{{{self.parent.style}}}")
        OLbl  = QtWidgets.QLabel(f"Window overlap: {self.windowOverlap}");OLbl.setMaximumWidth(600);OLbl.setStyleSheet(f"QLabel{{{self.parent.style}}}")
        OLF   = QtWidgets.QPushButton(">");OLF.setStyleSheet(f"QPushButton{{{self.parent.style}}}")
        OLR.clicked.connect(lambda:self.setOverlap(-1))
        OLF.clicked.connect(lambda:self.setOverlap(1))
        self.opt_overlay = OLbl

        WLR   = QtWidgets.QPushButton("<");WLR.setStyleSheet(f"QPushButton{{{self.parent.style}}}")
        WLbl   = QtWidgets.QLabel(f"Window len: {self.windowLen}");WLbl.setMaximumWidth(600);WLbl.setStyleSheet(f"QLabel{{{self.parent.style}}}")
        WLF   = QtWidgets.QPushButton(">");WLF.setStyleSheet(f"QPushButton{{{self.parent.style}}}")
        WLR.clicked.connect(lambda:self.setWindowlen(-1))
        WLF.clicked.connect(lambda:self.setWindowlen(1))
        self.opt_windowlen = WLbl
        self.opt = W

        L.addWidget(R,0,0)
        L.addWidget(Lbl,0,1)
        L.addWidget(F,0,2)


        L.addWidget(OLR,1,0)
        L.addWidget(OLbl,1,1)
        L.addWidget(OLF,1,2)

        L.addWidget(WLR,2,0)
        L.addWidget(WLbl,2,1)
        L.addWidget(WLF,2,2)

        return W

    def setDataCol(self,inc):
        self.dataCol += inc
        L = len(self.parent.df.columns)
        if self.dataCol<0: self.dataCol = L-1
        if self.dataCol>=L: self.dataCol = 0
        self.opt_datacol.setText(self.parent.df.columns[self.dataCol])
        self.updateData()

    def setOverlap(self,inc):
        self.windowOverlapRel +=inc
        max = 8-1
        if self.windowOverlapRel<1: self.windowOverlapRel = max
        if self.windowOverlapRel>max: self.windowOverlapRel = 1
        self.updateData()

    def setWindowlen(self,inc):
        self.windowLenRel +=inc
        max = 8
        if self.windowLenRel<1: self.windowLenRel = max
        if self.windowLenRel>max: self.windowLenRel = 1
        self.updateData()

class Addon_meas(Addon):
    name="meas"
    startHidden = True

    def __init__(self,parent):
        super().__init__(parent)

        df = self.parent.df
        t0 = df.index[0]
        t1 = df.index[-1]
        dt = t1-t0
        f = len(df.index)/dt

        c1 = measLine(angle=90, movable=True, pos = t0+dt/3); c1._parent = [self.parent,"xy"]
        c2 = measLine(angle=90, movable=True, pos = t0+2*dt/3); c2._parent = [self.parent,"xy"]
        c3 = measLine(angle=90, movable=True, pos = 1*f/6); c3._parent = [self.parent,"fft"]
        c4 = measLine(angle=90, movable=True, pos = 2*f/6); c4._parent = [self.parent,"fft"]

        self.cursors = [c1,c2,c3,c4]
        self.hidden = self.startHidden

    def resolveConnections(self):
        self.parent.addons["buttons"].buttons[self.name].clicked.connect(self.toggle)
        for x in self.cursors:
            x.sigPositionChangeFinished.connect(self.updateData)
            self.parent.addons[x._parent[1]].plt.addItem(x)
            x.setVisible(not self.startHidden)
            

    def getGuiElements(self):
        return []

    def updateData(self, cursordata):
        pass

    def toggle(self):
        for x in self.cursors:
            x.setVisible(self.hidden)
            x.label.valueChanged()
        self.hidden=not self.hidden

class HoriHist(pg.HistogramLUTItem):
    def __init__(self, image=None, fillHistogram=True, rgbHistogram=False, levelMode='mono'):
        pg.GraphicsWidget.__init__(self)
        self.lut = None
        self.imageItem = lambda: None  # fake a dead weakref
        self.levelMode = levelMode
        self.rgbHistogram = rgbHistogram
        
        self.layout = QtGui.QGraphicsGridLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(1,1,1,1)
        self.layout.setSpacing(0)
        self.vb = pg.ViewBox(parent=self)
        self.vb.setMaximumHeight(20)
        self.vb.setMinimumHeight(20)
        self.vb.setMouseEnabled(x=False, y=True)

        self.gradient = pg.GradientEditorItem()
        self.gradient.setOrientation('top')
        self.gradient.loadPreset('viridis')

        self.gradient.setFlag(self.gradient.ItemStacksBehindParent)
        self.vb.setFlag(self.gradient.ItemStacksBehindParent)
        self.layout.addItem(self.gradient, 0, 0)
        self.layout.addItem(self.vb, 1, 0)
        self.axis = pg.AxisItem('bottom', linkView=self.vb, maxTickLength=-10, parent=self)
        self.layout.addItem(self.axis, 2, 0)

        self.regions = [
            pg.LinearRegionItem([0, 1], 'vertical', swapMode='block'),
            #we dont need those here
            #pg.LinearRegionItem([0, 1], 'vertical', swapMode='block', pen='r',brush=fn.mkBrush((255, 50, 50, 50)), span=(0., 1/3.)),
            #pg.LinearRegionItem([0, 1], 'vertical', swapMode='block', pen='g',brush=fn.mkBrush((50, 255, 50, 50)), span=(1/3., 2/3.)),
            #pg.LinearRegionItem([0, 1], 'vertical', swapMode='block', pen='b',brush=fn.mkBrush((50, 50, 255, 80)), span=(2/3., 1.)),
            #pg.LinearRegionItem([0, 1], 'vertical', swapMode='block', pen='w',brush=fn.mkBrush((255, 255, 255, 50)), span=(2/3., 1.))
            ]
        for region in self.regions:
            region.setZValue(1000)
            self.vb.addItem(region)
            region.lines[0].addMarker('<|', 0.5)
            region.lines[1].addMarker('|>', 0.5)
            region.sigRegionChanged.connect(self.regionChanging)
            region.sigRegionChangeFinished.connect(self.regionChanged)
        self.region = self.regions[0]

        add = QtGui.QPainter.CompositionMode_Plus
        self.plots = [
            pg.PlotCurveItem(pen=(200, 200, 200, 100)),  # mono
            pg.PlotCurveItem(pen=(255, 0, 0, 100), compositionMode=add),  # r
            pg.PlotCurveItem(pen=(0, 255, 0, 100), compositionMode=add),  # g
            pg.PlotCurveItem(pen=(0, 0, 255, 100), compositionMode=add),  # b
            pg.PlotCurveItem(pen=(200, 200, 200, 100), compositionMode=add),  # a
            ]
        self.plot = self.plots[0]
        for plot in self.plots:
            self.vb.addItem(plot)
        self.fillHistogram(fillHistogram)

        self.range = None
        self.gradient.sigGradientChanged.connect(self.gradientChanged)
        self.vb.sigRangeChanged.connect(self.viewRangeChanged)

    def paint(self, p, *args):
        if self.levelMode != 'mono':
            return
        
        pen = self.region.lines[0].pen
        rgn = self.getLevels()
        p1 = self.vb.mapFromViewToItem(self, pg.Point(rgn[0],self.vb.viewRect().center().y()))
        p2 = self.vb.mapFromViewToItem(self, pg.Point(rgn[1],self.vb.viewRect().center().y()))
        gradRect = self.gradient.mapRectToParent(self.gradient.gradRect.rect())
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        for pen in [fn.mkPen((0, 0, 0, 100), width=3), pen]:
            p.setPen(pen)
            p.drawLine(p1 - pg.Point(5, 0), gradRect.bottomLeft())
            p.drawLine(p2 + pg.Point(5, 0), gradRect.bottomRight())
            p.drawLine(gradRect.topLeft(), gradRect.bottomLeft())
            p.drawLine(gradRect.topRight(), gradRect.bottomRight())

class measLine(pg.InfiniteLine):
    def __init__(self,*args,**kwargs):
        if "label" in kwargs: kwargs.pop("label")
        if "labelOpts" in kwargs: kwargs.pop("labelOpts")
        super().__init__(*args,**kwargs)
        self._parent = None
        self.label = measLabel(self, text="",movable=True)

class measLabel(pg.InfLineLabel):
    def valueChanged(self):
        if not self.isVisible():
            return
        X = self.line.value()
        if self.line._parent is not None:
            parent = self.line._parent[0].addons[self.line._parent[1]]
            data = parent.plt.dataItems
            headernames = ["X"]+[f"Y{x}" for x in range(len(data))]
            idx = np.argmin(abs(data[0].xData-X))
            vals = [X]+list(x.yData[idx] for x in data)
            lines = []
            for k,v in zip(headernames,vals):
                lines.append(f"{k}:\t{v:.4f}")
            self.setText("\n".join(lines))
        self.updatePosition()