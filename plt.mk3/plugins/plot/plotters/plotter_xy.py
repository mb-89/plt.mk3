import pyqtgraph as pg
from .__plotter__ import Plotter as _P
from .__plotter__ import SubPlot as _SP
from scipy import fft
import numpy as np
from PySide2 import QtCore,QtWidgets,QtGui
import pandas as pd
from scipy import signal
from pyqtgraph import functions as fn

class Plotter(_P):
    def getPlot(self, X, Y, Xnames, Ynames, plotinfo, selectedSeries, sharedCoords):
        return SubPlot(X,Y,Xnames,Ynames,sharedCoords) 

class SubPlot(_SP):
    transparentstyle="background: transparent;color:#969696;border-color: #969696;border-width: 1px;border-style: solid;min-width: 3em;"

    def __init__(self, xdata, ydata, xnames, ynames, sharedCoords):
        super().__init__(xdata, ydata, xnames, ynames, sharedCoords)
        self.df = pd.DataFrame()
        self.plt = self.addPlot(row=1,col=0)
        self.addWidgets()
        self.lines = {}

        def xyname2s(X,Y,yname):
            comments = " / ".join(Y.attrs.get("comments",[]))
            nameAndComments = f"{yname[0]} {comments} @ {yname[1]}"
            return pd.Series(Y,index=X,name=nameAndComments)
        self.updateData(pd.concat([
            xyname2s(X,Y,yname).to_frame() for idx,(X,Y,yname) in enumerate(zip(xdata,ydata,ynames))
        ],axis=1))

        self.plt.addLegend()
        L = len(self.df.columns)

        for idx,colname in enumerate(self.df.columns):
            self.lines[colname] = self.plt.plot(y=self.df[colname],x=self.df[colname].index,pen=(idx,L),name=colname)

        self.plt.setLabels(left=" / ".join(sorted(list(set(x[0] for x in ynames)))), bottom = " / ".join(sorted(list(set(xnames)))))
        self.plt.showGrid(x=True,y=True,alpha=1)
        #self.plt._mousePressEvent=self.plt.mousePressEvent
        #self.plt.mousePressEvent = self.PltMousePressEvent
        
        #,, name = f'{_ynames[_ydata.name]} @ {_k}')
        #      _cnt+=1
        if sharedCoords:
            self.plt.setXLink(sharedCoords[0])
        sharedCoords.append(self.plt)

    def PltMousePressEvent(self, e):
        self.plt._mousePressEvent(e)

    def addWidgets(self):
        C = QtWidgets.QGraphicsProxyWidget()
        W = QtWidgets.QWidget()
        W.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        W.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        LL=QtWidgets.QVBoxLayout()
        LL.setSpacing(2)
        LL.setContentsMargins(0,0,0,0)
        L = QtWidgets.QHBoxLayout()
        L.addItem(QtWidgets.QSpacerItem(10,10,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding))
        L.setSpacing(0)
        L.setContentsMargins(0,0,0,0)
        LL.addLayout(L)
        W.setLayout(LL)
        C.setWidget(W)
        self.addItem(C,col=0)

        self.addons = dict((x.name,x(self)) for x in [
            Addon_cursors,
            Addon_FFT,
            Addon_spec
        ])

        for a in self.addons.values():
            L.addWidget(a.button)
            LL.addWidget(a.content, row = a.row)
            a.fillContent()

    def updateData(self, data):
        self.df = data

    def buildFFTWidgets(self):
        B = QtWidgets.QPushButton("FFT")
        B.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        B.setStyleSheet(f"QPushButton{{{self.transparentstyle}}}")

        FFT = self.addPlot(col=0,row=2)
        FFT.addLegend()
        FFT.showGrid(x=True,y=True,alpha=0.3)
        
        self.FFT = FFT
        self.FFT.setVisible(False)

        B.clicked.connect(self.toggleFFTWidgets)
        return B,None

    def toggleFFTWidgets(self):
        hidden = not self.FFT.isVisible()
        try: R = self.FFTreg
        except AttributeError:
            self.FFT.setLabels(
                left=self.plt.axes["left"]["item"].label.toPlainText(), 
                bottom="ℱ{ "+self.plt.axes["bottom"]["item"].label.toPlainText()+"}"
                )
            R = pg.LinearRegionItem()
            R.setZValue(10)
            t0 = self.df.index[0]
            t1 = self.df.index[-1]
            dt = t1-t0
            R.setRegion([t0+dt/3,t1-dt/3])
            R.sigRegionChanged.connect(self.updateFFTRegion)
            self.plt.addItem(R)
            self.FFTreg = R

        if hidden:self.updateFFTRegion(R)
        self.FFT.setVisible(hidden)
        self.FFTreg.setVisible(hidden)

    def updateFFTRegion(self, range):
        if not self.FFT.isVisible:return
        x0x1 = range.getRegion()
        self.FFT.clearPlots()
        L = len(self.lines)
        for idx,tplt in enumerate(self.lines.values()):
            selectedData = tplt.getData()
            mask = np.logical_and(selectedData[0]>=x0x1[0],selectedData[0]<=x0x1[1])
            X = selectedData[0][mask]
            Y = selectedData[1][mask]
            N = len(X)
            T = (X[-1]-X[0])/N
            yf = 2.0/N * np.abs(fft.fft(Y)[0:N//2])
            xf = np.linspace(0.0, 1.0/(2.0*T),N//2)
            self.FFT.plot(x=xf[1:],y=yf[1:],pen=(idx,L))

class Addon(QtCore.QObject):
    name = "Addon"
    row = 0
    transparentstyle="background: transparent;color:#969696;border-color: #969696;border-width: 1px;border-style: solid;min-width: 3em;"
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.content = QtWidgets.QTreeView()
        self.button = QtWidgets.QPushButton(self.name)
        self.button.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.button.setStyleSheet(f"QPushButton{{{self.transparentstyle}}}")
        self.button.clicked.connect(self.toggle)
        self.content.setVisible(False)

    def fillContent(self):
        pass

    def toggle(self):
        pass

class Addon_cursors(Addon):
    name = "Cursors"

    def __init__(self, parent):
        super().__init__(parent)
        view = self.content
        view.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        view.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        view.setStyleSheet("""
        QTreeView{background-color:transparent;color:#969696}
        QTreeView::section{background-color: transparent;color:#969696}
        QHeaderView{background-color: transparent;color:#969696}
        QHeaderView::section{background-color: transparent;color:#969696}""")

        self.view=view

    def toggle(self):
        hidden = not self.content.isVisible()

        try: vL1 = self.parent.plt.vL1
        except AttributeError:
            vL1 = pg.InfiniteLine(angle=90, movable=True)
            vL2 = pg.InfiniteLine(angle=90, movable=True)
            self.parent.plt.addItem(vL1, ignoreBounds=True)
            self.parent.plt.addItem(vL2, ignoreBounds=True)
            self.parent.plt.vL1 = vL1
            self.parent.plt.vL2 = vL2
            vL1.sigPositionChangeFinished.connect(self.updateCursors)
            vL2.sigPositionChangeFinished.connect(self.updateCursors)
        vL2 = self.parent.plt.vL2

        #now, we know vl1 and vl2.
        vL1.setVisible(hidden)
        vL2.setVisible(hidden)
        if hidden:self.updateCursors()

        self.content.setVisible(hidden)

    def updateCursors(self):
        print("bla")
        df = self.parent.df
        try:mdl=self.view.model().sourceModel()
        except:
            try:xlabel = df.index.name
            except: return
            fltmdl = QtCore.QSortFilterProxyModel()
            mdl = QtGui.QStandardItemModel()
            fltmdl.setSourceModel(mdl)
            self.view.setModel(fltmdl)
            self.view.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        mdl.clear()

        headernames = ["", df.index.name]+[x for x in df.columns]
        L = len(headernames)
        mdl.setHorizontalHeaderLabels(headernames)
        mdl.setColumnCount(L)
        xheadernames = ["@1","@2","Δ","1/Δ"]
        self.view.setMaximumHeight(20*len(xheadernames)+30)
        
        vL1 = self.parent.plt.vL1
        vL2 = self.parent.plt.vL2
        X1 = vL1.value()
        X2 = vL2.value()
        X1vals = df.iloc[np.argmin(abs(df.index.values-X1))]
        X2vals = df.iloc[np.argmin(abs(df.index.values-X2))]
        deltavals = [x2-x1 for x1,x2 in zip(X1vals,X2vals)]
        freqvals = []
        for x in deltavals:
            try:freqvals.append(1.0/x)
            except:freqvals.append(0)
        try:freq = 1.0/(X2-X1)
        except: freq=0
        vals = [
            [str(X1)]+[str(x) for x in X1vals],#these are the values at 1
            [str(X2)]+[str(x) for x in X1vals],#these are the values at 2
            [str(X2-X1)]+[str(x) for x in deltavals],#these are the deltas
            [str(freq)]+[str(x) for x in freqvals],#these are the 1/deltas
        ]
        for rowidx,name in enumerate(xheadernames):
            row = [name]
            for col in range(L-1):
                row.append(vals[rowidx][col])
            mdl.appendRow([QtGui.QStandardItem(x) for x in row])
        for idx in range(L):
            self.view.resizeColumnToContents(L-1-idx)
        self.view.model().invalidate()
        print("blubb")
class Addon_FFT(Addon):
    name = "FFT"
class Addon_spec(Addon):
    name = "Spec"

class Spec(QtCore.QObject):
    def __init__(self, parent, row, col=0):
        super().__init__()
        self.parent = parent
        L = self.parent.addLayout(row=row,col=col)

        #fplt
        self.fplt = L.addPlot(row=0,col=0,colspan=2)
        self.fplt.addLegend()
        self.fplt.showGrid(x=True,y=True,alpha=0.3)

        #hist
        hist = HoriHist()
        L.addItem(hist,row=1,col=0,rowspan=1)
        self.hist = hist

        #rest (wrapped in a proxy)
        self.windowLenRel = 4
        self.windowOverlapRel = 4
        self.windowLenBase = 256

        C = QtWidgets.QGraphicsProxyWidget()
        W = QtWidgets.QWidget()
        W.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        W.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        C.setWidget(W)
        L.addItem(C,row=1,col=1,rowspan=1)


        B = QtWidgets.QPushButton("Spec")
        B.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        B.setStyleSheet(f"QPushButton{{{self.parent.transparentstyle}}}")
        B.clicked.connect(self.toggle)
        self.toggleButton = B
        self.container = L
        L.setVisible(False)

        self.initplt()

    def initplt(self):
        img = pg.ImageItem()
        img.setOpts(axisOrder='row-major')
        self.img = img
        self.hist.setImageItem(img)
        self.fplt.addItem(img)

        self.fplt.showGrid(True,True,1)
        self.fplt.setXLink(self.parent.plt)

    def calc(self):
        col = self.parent.df.columns[0]
        Y=self.parent.df[col].values
        T=self.parent.df.index.values
        L = len(T)
        WL = int(self.windowLenBase*self.windowLenRel)
        self.f, self.t, self.Sxx = signal.spectrogram(
                Y, 
                1/((T[-1]-T[0])/L),
                scaling = 'spectrum',
                mode='magnitude',
                nperseg= WL,
                noverlap=int(WL/8*self.windowOverlapRel))
        self.Sxx*=2.0

    def update(self):
        self.calc()
        # Sxx contains the amplitude for each pixel
        self.img.setImage(self.Sxx)

        # Scale the X and Y Axis to time and frequency (standard is pixels)
        self.img.resetTransform()
        self.img.scale(self.t[-1]/np.size(self.Sxx, axis=1),
                self.f[-1]/np.size(self.Sxx, axis=0))
        self.hist.setLevels(np.min(self.Sxx), np.percentile(self.Sxx,97))
    
        #self.hist.gradient.restoreState(
        #        {'mode': 'rgb',
        #        'ticks': [(0.8, (0, 182, 188, 255)),
        #                (1.0, (246, 111, 0, 255)),
        #                (0.0, (75, 0, 113, 255))]})
    
        # Limit panning/zooming to the spectrogram
        t1 = self.parent.df.index[-1]
        t0 = self.parent.df.index[0]
        freq = len(self.parent.df.index)/(t1-t0)
        self.fplt.setLimits(yMin=0, yMax=freq/2.0)
        for x in self.fplt.axes:
            ax = self.fplt.getAxis(x)
            ax.setZValue(1)

        col = self.parent.df.columns[0]
        self.fplt.setLabels(left=f"ℱ{{{col}}}", bottom=self.parent.plt.axes["bottom"]["item"].label.toPlainText())

    def toggle(self):
        hidden = not self.container.isVisible()
        if hidden: 
            self.hist.imageChanged()
            self.update()
        self.container.setVisible(hidden)
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
        self.vb.setMaximumHeight(152)
        self.vb.setMinimumHeight(45)
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