from .__parser__ import Parser as _P
import os.path as op
#from scapy.all import rdpcap,IP,TCP,UDP,Raw
import pandas as pd

class Parser(_P):
    parsername = "pcapng"
    def __init__(self, path, app):
        super().__init__(path, app)
        self.recognized = False
        if not op.isfile(path):return
        self.recognized = path.endswith(".pcapng")
        if not self.recognized: return
        self.path = path
        self.reservedFiles.append(path)

    def parse(self):
        self.app.log.info(f"started parsing {op.basename(self.path)} ({self.parsername})")

        cap = rdpcap(self.path)
        cols = {}
        t0 = None
        names = []
        for idx,packet in enumerate(cap):
            proto = "/".join([packet.getlayer(idx).name for idx in range(len(packet.layers()))])
            src = packet[IP].src
            dst = packet[IP].dst
            sprt = ""
            dprt = ""
            if TCP in packet:
                sprt = f":{packet[TCP].sport}"
                dprt = f":{packet[TCP].dport}"
            elif UDP in packet:
                sprt = f":{packet[UDP].sport}"
                dprt = f":{packet[UDP].dport}"
            
            name = f"{proto}/{src}{sprt}/TO/{dst}{dprt}"
            if name not in names: names.append(name)
            nameIdx = names.index(name)
            data = []
            try: data = list(packet[Raw].load)
            except: continue
            #data = idx
            time = float(packet.time)
            if t0 is None: t0 = time
            time -= t0
            frame = {"Time":time,"NIDX":nameIdx}
            for idx, byte in enumerate(data):
                frame[f"Byte{str(idx).zfill(4)}"]=byte
            cols.setdefault(name,[]).append(frame)

        dfs = [pd.DataFrame.from_records(x) for x in cols.values() ]
        dfs = self.postprocess(dfs, disableChunks = True)
        #after the postprocessing, every frame should have a "NIDX" attrib.
        #we will use this to patch the dataframe name
        for df in dfs:
            name = names[int(df.attrs["NIDX"])]
            df.attrs["name"] = df.attrs["name"]+f"/{name}"

        if dfs:self.app.log.info(f"done parsing {op.basename(self.path)}, extracted {len(dfs)} dataframes. ({self.parsername})")
        else: self.app.log.error(f"parsing {op.basename(self.path)} failed.")
        self.done.emit(dfs)

    def postprocess(self, dfs, disableChunks = False):
        for df in dfs:
            if df.columns.nlevels <=1:continue
            df.columns = ['/'.join(col) for col in df.columns]

        return super().postprocess(dfs,disableChunks=disableChunks)