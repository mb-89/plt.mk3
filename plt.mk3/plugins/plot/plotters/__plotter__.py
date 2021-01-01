import pyqtgraph as pg
from PySide2 import QtCore, QtWidgets, QtGui
import pyqtgraph.functions as fn
import pandas as pd
from functools import partial

transparentCol = "#969696"
transparentStyle=f"background: transparent;color:{transparentCol};border-color: {transparentCol};border-width: 1px;border-style: solid;min-width: 3em;"

class Plotter():
    def getPlot(self):
        return pg.GraphicsLayout()

class FixedGraphicsLayout(pg.GraphicsLayout):
    def addItem(self, item, row=None, col=None, rowspan=1, colspan=1):
        """
        Add an item to the layout and place it in the next available cell (or in the cell specified).
        The item must be an instance of a QGraphicsWidget subclass.
        """
        if row is None:
            row = self.currentRow
        if col is None:
            col = self.currentCol
            
        self.items[item] = []
        for i in range(rowspan):
            for j in range(colspan):
                row2 = row + i
                col2 = col + j
                if row2 not in self.rows:
                    self.rows[row2] = {}
                self.rows[row2][col2] = item
                self.items[item].append((row2, col2))

        borderRect = QtGui.QGraphicsRectItem()

        borderRect.setParentItem(self)
        borderRect.setZValue(1e3)
        borderRect.setPen(fn.mkPen(self.border))

        self.itemBorders[item] = borderRect

        #this does not work in the original src code. i dont care, just ignore the exception...
        try: item.geometryChanged.connect(self._updateItemBorder)
        except:bla = 1

        self.layout.addItem(item, row, col, rowspan, colspan)
        self.layout.activate() # Update layout, recalculating bounds.
                               # Allows some PyQtGraph features to also work without Qt event loop.
        
        self.nextColumn()

    def addLayout(self, row=None, col=None, rowspan=1, colspan=1, **kargs):
        """
        Create an empty GraphicsLayout and place it in the next available cell (or in the cell specified)
        All extra keyword arguments are passed to :func:`GraphicsLayout.__init__ <pyqtgraph.GraphicsLayout.__init__>`
        Returns the created item.
        """
        layout = FixedGraphicsLayout(**kargs)#we need to use the fixed version, otherwise we run into the same problems as with addItem()
        self.addItem(layout, row, col, rowspan, colspan)
        return layout


class SubPlot(FixedGraphicsLayout):
    style = transparentStyle
    color0 = transparentCol

    def __init__(self, xdata, ydata, xnames, ynames, sharedCoords):
        super().__init__()
        self.xdata = xdata
        self.ydata = ydata
        self.xnames = xnames
        self.ynames = ynames
        self.sharedCoords = sharedCoords
        self.lines = {}
        self.addons = {}
        self.proxys = []

        #put data in dataframe
        def xyname2s(idx,X,Y,yname):
            comments = " / ".join(Y.attrs.get("comments",[]))
            nameAndComments = f"{yname[0]} {comments} @ {yname[1]} [Y{idx}]"
            return pd.Series(Y,index=X,name=nameAndComments)

        self.df = pd.concat([xyname2s(idx,X,Y,yname).to_frame() for idx,(X,Y,yname) in enumerate(zip(xdata,ydata,ynames))],axis=1)
        p = partial(self.updateData,self.df)
        QtCore.QTimer.singleShot(0,p)

    def updateData(self, data):
        self.df = data
        for k,v in self.addons.items():v.updateData(self.df)

    def addRowColList(self, rowColList, rowWise = True,  _parent=None,_col=0):
        #we can use this to add widgets from a list. 
        #the list must have the form:
        #[row1, row2, row3, ...]
        #where each row is either itself a list (in this case we interpret it as columns and call this function recursively),
        #or a QGraphicsWidget subclass, in which case we just append it,
        #or a QWidget/QLayout subclass, in which case we build a proxy for it and add it
        #If an item has a rowspan(colspan) attribute, we use it. (TBD)
        colWise = not rowWise
        if _parent is None:_parent=self

        try: nrOfRows = len(_parent.rows)
        except: nrOfRows = 0

        try: elems = tuple(iter(rowColList))
        except:
            #if we are here, we are not a list
            if isinstance(rowColList, QtWidgets.QGraphicsWidget):
                row = 0 if colWise else nrOfRows+1
                _parent.addItem(rowColList, row = row,col=_col)
                rowColList._row=row
            if isinstance(rowColList, pg.GraphicsLayout):
                row = 0 if colWise else nrOfRows+1
                _parent.addLayout(rowColList, row = row,col=_col)
                rowColList._row=row

            if isinstance(rowColList,QtWidgets.QWidget):
                _parent.addWidget(rowColList)
            if isinstance(rowColList,QtWidgets.QLayout):
                _parent.addLayout(rowColList)
            return
        #if we are here, we can iterate
        proxyneededlambda = lambda x: isinstance(x,QtWidgets.QWidget) or isinstance(x,QtWidgets.QLayout)
        proxyneeded = all(proxyneededlambda(x) for x in elems)
        if proxyneeded:
            P = QtWidgets.QGraphicsProxyWidget()
            self.proxys.append(P)
            W = QtWidgets.QWidget()
            W.setAttribute(QtCore.Qt.WA_TranslucentBackground)
            W.setAttribute(QtCore.Qt.WA_NoSystemBackground)
            L= QtWidgets.QHBoxLayout() if rowWise else QtWidgets.QVBoxLayout()
            L.setSpacing(0)
            L.setContentsMargins(0,0,0,0)
            W.setLayout(L)
            P.setWidget(W)
            _parent.addItem(P, row = 0 if colWise else nrOfRows+1,col=_col)
            _subparent = L
        else:
            _subparent = _parent.addLayout(row = 0 if colWise else nrOfRows+1,col=_col)
        for idx,x in enumerate(elems):
            col = 0 if colWise else idx
            self.addRowColList(x,rowWise=not rowWise,_parent=_subparent,_col=col)
        if proxyneeded:
            _subparent.addItem(QtWidgets.QSpacerItem(10,10,QtWidgets.QSizePolicy.Expanding,QtWidgets.QSizePolicy.Expanding))
