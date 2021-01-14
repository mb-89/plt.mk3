from PySide2.QtCore import QObject, Signal
import os.path as op
nrOfDataFrames = 0

class Parser(QObject):
    done = Signal(tuple)
    def __init__(self, app):
        self.app = app
        self.name = op.splitext(op.basename(path))[0]

    def parse(self):
        raise UserWarning(f"parser <{self.name}> not implemented")