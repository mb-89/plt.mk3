import pyqtgraph as pg
from PySide2 import QtCore, QtWidgets, QtGui
import pyqtgraph.functions as fn

class Plotter():
    def getPlot(self):
        return pg.GraphicsLayout()

class SubPlot(pg.GraphicsLayout):
    def __init__(self, xdata, ydata, xnames, ynames, sharedCoords):
        super().__init__()
        self.xdata = xdata
        self.ydata = ydata
        self.xnames = xnames
        self.ynames = ynames
        self.sharedCoords = sharedCoords

    def addRowColList(self, rowColList, rowWise = True):
        #we can use this to add widgets from a list. 
        #the list must have the form:
        #[row1, row2, row3, ...]
        #where each row is either itself a list (in this case we interpret it as columns and call this function recursively),
        #or a QGraphicsWidget subclass, in which case we just append it,
        #or a QWidget/QLayout subclass, in which case we build a proxy for it and add it
        #If an item has a rowspan(colspan) attribute, we use it.
        colWise = not rowWise

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