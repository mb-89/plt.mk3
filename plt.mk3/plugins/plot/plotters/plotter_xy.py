import pyqtgraph as pg
from .__plotter__ import Plotter as _P
from .__plotter__ import SubPlot as _SP
from scipy import fft
import numpy as np
from PySide2 import QtCore,QtWidgets,QtGui
import pandas as pd

class Plotter(_P):
    def getPlot(self, X, Y, Xnames, Ynames, plotinfo, selectedSeries, sharedCoords):
        return SubPlot(X,Y,Xnames,Ynames,sharedCoords) 

class SubPlot(_SP):
    transparentstyle="background: transparent;color:#969696;border-color: #969696;border-width: 1px;border-style: solid;min-width: 3em;"

    def __init__(self, xdata, ydata, xnames, ynames, sharedCoords):
        super().__init__(xdata, ydata, xnames, ynames, sharedCoords)
        self.df = pd.DataFrame()
        self.addWidgets()
        self.lines = {}

        def xyname2s(X,Y,yname):
            comments = " / ".join(Y.attrs.get("comments",[]))
            nameAndComments = f"{yname[0]} {comments} @ {yname[1]}"
            return pd.Series(Y,index=X,name=nameAndComments)

        self.updateData(pd.concat([
            xyname2s(X,Y,yname).to_frame() for idx,(X,Y,yname) in enumerate(zip(xdata,ydata,ynames))
        ],axis=1))

        self.plt = self.addPlot(row=1,col=0)
        self.plt.addLegend()
        L = len(self.df.columns)

        for idx,colname in enumerate(self.df.columns):
            self.lines[colname] = self.plt.plot(y=self.df[colname],x=self.df[colname].index,pen=(idx,L),name=colname)

        self.plt.setLabels(left=" / ".join(sorted(list(set(x[0] for x in ynames)))), bottom = " / ".join(sorted(list(set(xnames)))))
        self.plt.showGrid(x=True,y=True,alpha=0.3)
        #,, name = f'{_ynames[_ydata.name]} @ {_k}')
        #      _cnt+=1
        if sharedCoords:
            self.plt.setXLink(sharedCoords[0])
        sharedCoords.append(self.plt)

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
        
        addonList = [
            self.buildFFTWidgets,
            self.buildCursorWidgets
        ]
        for a in addonList:
            Cursorbutton, CursorWidgetAndRow = a()
            if Cursorbutton:        L.addWidget(Cursorbutton)
            if CursorWidgetAndRow:  LL.addWidget(CursorWidgetAndRow[0], row = CursorWidgetAndRow[1],col=0)

        W.setLayout(LL)
        C.setWidget(W)
        self.addItem(C,col=0)

    def updateData(self, data):
        self.df = data
    
    def buildCursorWidgets(self):
        B = QtWidgets.QPushButton("C")
        B.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        B.setStyleSheet(f"QPushButton{{{self.transparentstyle}}}")

        P = QtWidgets.QTreeView()
        P.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        P.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        P.setStyleSheet("""
        QTreeView{background-color:transparent;color:#969696}
        QTreeView::section{background-color: transparent;color:#969696}
        QHeaderView{background-color: transparent;color:#969696}
        QHeaderView::section{background-color: transparent;color:#969696}""")

        self.cursorPanel=P
        self.cursorPanel.setVisible(False)
        B.clicked.connect(self.toggleCursorWidgets)
        return B, (P,0)

    def toggleCursorWidgets(self):
        hidden = self.cursorPanel.isHidden()

        try: vL1 = self.plt.vL1
        except AttributeError:
            vL1 = pg.InfiniteLine(angle=90, movable=True)
            vL2 = pg.InfiniteLine(angle=90, movable=True)
            self.plt.addItem(vL1, ignoreBounds=True)
            self.plt.addItem(vL2, ignoreBounds=True)
            self.plt.vL1 = vL1
            self.plt.vL2 = vL2
            vL1.sigPositionChanged.connect(self.updateCursorData)
            vL2.sigPositionChanged.connect(self.updateCursorData)
        vL2 = self.plt.vL2

        #now, we know vl1 and vl2.
        vL1.setVisible(hidden)
        vL2.setVisible(hidden)
        if hidden:self.updateCursorData()

        self.cursorPanel.setVisible(hidden)

    def updateCursorData(self):
        mdl = self.cursorPanel.model()
        if mdl: mdl.clear()
        if not mdl:
            try:xlabel = self.df.index.name
            except: return
            mdl = QtGui.QStandardItemModel()
            self.cursorPanel.setModel(mdl)
            self.cursorPanel.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        headernames = ["", self.df.index.name]+[x for x in self.df.columns]
        L = len(headernames)
        mdl.setHorizontalHeaderLabels(headernames)
        mdl.setColumnCount(L)
        xheadernames = ["@1","@2","Δ","1/Δ"]
        self.cursorPanel.setMaximumHeight(20*len(xheadernames)+30)
        vL1 = self.plt.vL1
        vL2 = self.plt.vL2
        X1 = vL1.value()
        X2 = vL2.value()
        X1vals = self.df.iloc[np.argmin(abs(self.df.index.values-X1))]
        X2vals = self.df.iloc[np.argmin(abs(self.df.index.values-X2))]
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
            self.cursorPanel.resizeColumnToContents(L-1-idx)

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
