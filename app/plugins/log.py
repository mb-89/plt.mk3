from .__plugin__ import Plugin as _P
from .__plugin__ import publicFun

import logging
import sys
from PySide2 import QtCore, QtWidgets, QtGui
from functools import partial

class Plugin(_P):
    log2Bar = QtCore.Signal(str)
    log2Wid = QtCore.Signal(str)
    def __init__(self, app):
        super().__init__(app)
        self.log = logging.getLogger(self.app.info["name"])
        self.app.log = self.log
        log = self.log

        log.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(relativeCreated)08d %(levelname)s: %(message)s')
        log._fmt = formatter

        logging.addLevelName(logging.DEBUG, 'DBG ')
        logging.addLevelName(logging.INFO, 'INFO')
        logging.addLevelName(logging.WARNING, 'WARN')
        logging.addLevelName(logging.ERROR, 'ERR ')

        #reroute stdin, stderr
        log._STDerrLogger = StreamToLogger(log, logging.ERROR)
        log._origSTDerr = sys.stderr
        #sys.stderr = log._STDerrLogger
        log._STDoutLogger = StreamToLogger(log, logging.INFO)
        log._origSTDout = sys.stdout
        sys.stdout = log._STDoutLogger

        #add to console
        ch = logging.StreamHandler(log._origSTDout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(log._fmt)
        log.addHandler(ch)

        #add to statusbar
        bar = self.app.gui.statusBar()
        fn = lambda x: bar.showMessage(x, 0)
        connectLog2fn(log, fn, self.log2Bar)

        #add to widget
        self.logwidget = LogWidget(self.app)
        connectLog2fn(log, self.logwidget.append, self.log2Wid)

    def start(self):
        pass
    
    @publicFun(guishortcut="Ctrl+L")
    def toggle(self):
        """
        Toggles the log window
        """
        self.logwidget.togglehide()

def connectLog2fn(log, fn ,s):
        #emit function to connect log msgs to qt signals:
        def emit(obj, sig, logRecord):
            msg = obj.format(logRecord)
            sig.emit(msg)

        hdl = logging.StreamHandler()
        hdl.setFormatter(log._fmt)
        hdl.setLevel(logging.DEBUG)
        hdl.emit = partial(emit,hdl,s)
        s.connect(fn)
        log.addHandler(hdl)

class LogWidget(QtWidgets.QDockWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.lw = QtWidgets.QPlainTextEdit()

        f = QtGui.QFont("monospace")
        f.setStyleHint(QtGui.QFont.TypeWriter)
        self.lw.setFont(f)

        self.lw.setReadOnly(True)
        self.lw.setUndoRedoEnabled(False)
        self.lw.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard)
        self.hide()
        self.setWidget(self.lw)
        self.app.gui.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self)
        self.resize(600,400)
        self.setWindowTitle(self.app.info["name"]+' log')
        self.append = self.lw.appendPlainText

    def togglehide(self):
        self.setVisible(self.isHidden())

class StreamToLogger():
    """
    Fake file-like stream object that redirects writes to a logger instance.
    https://www.electricmonk.nl/log/2011/08/14/redirect-stdout-and-stderr-to-a-logger-in-python/
    """
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):pass