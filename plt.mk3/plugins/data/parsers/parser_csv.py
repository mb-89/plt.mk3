from .__parser__ import Parser as _P
import os.path as op
import json
from PySide2 import QtCore
from time import sleep
from pandas import read_csv
class Parser(_P):
    def __init__(self, path, app):
        super().__init__(path, app)
        #we only recognize csvs with "#format:{format json}" as the first line.
        if not op.isfile(path):return
        firstline = open(path,"r").readline()
        if not firstline.startswith("#format:"):return
        firstline = firstline.replace("#format:{","{")
        try: dct = json.loads(firstline)
        except json.decoder.JSONDecodeError:
            return
        
        self.path = path
        self.recognized = True
        self.format = dct
        self.reservedFiles.append(path)

    def parse(self):
        self.app.log.info(f"started parsing {op.basename(self.path)} (csv)")
        try:
            df = read_csv(self.path,**self.format)
            if df.empty: df = []
            else: dfs = [df]
        except:dfs = []
        dfs = self.postprocess(dfs)

        if dfs:self.app.log.info(f"done parsing {op.basename(self.path)}, extracted {len(dfs)} dataframes. (csv)")
        else: self.app.log.error(f"parsing {op.basename(self.path)} failed.")
        self.done.emit(dfs)

    def postprocess(self, dfs):
        for df in dfs:
            if df.columns.nlevels <=1:continue
            df.columns = ['_'.join(col) for col in df.columns]
        return super().postprocess(dfs)