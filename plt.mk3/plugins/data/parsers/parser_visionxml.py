from .__parser__ import Parser as _P
from lxml import etree
import numpy as np
import pandas as pd
import os.path as op

class Parser(_P):
    def __init__(self, path, app):
        super().__init__(path, app)
        if not op.isfile(path):return
        if not path.endswith(".xml"):return
        rootxml = etree.parse(path).getroot()
        isVisionXML = (rootxml.tag == "DataSet") or (rootxml.tag == "DataMatrix")
        if not isVisionXML:return
        self.path = path
        self.recognized = True
        self.reservedFiles.append(path)
        self.rootxml = rootxml

    def parse(self):
        self.app.log.info(f"started parsing {op.basename(self.path)} (visionxml)")

        dfs = self.analyzevisionxml()
        dfs = self.postprocess(dfs)

        if dfs:self.app.log.info(f"done parsing {op.basename(self.path)}, extracted {len(dfs)} dataframes. (visionxml)")
        else: self.app.log.error(f"parsing {op.basename(self.path)} failed.")
        self.done.emit(dfs)

    def analyzevisionxml(self):
        dirname = op.dirname(self.path)
        dataframes = []
        #first, clean up the xml and resolve all children:
        xml = self.rootxml.find("VisionStructure")
        self._recursiveResolveXMLchildren(xml, dirname)

        #get all mass data files
        massData = []
        for record in (x for x in xml.iter("AssociatedRecord") if x.find("Name").text == "MassData"):
            path = [record.find("RecordRef").text]
            target = record.getparent()
            columnInfo = target.getparent().find("Private").find("Columns")
            while target != xml:
                nameelem = target.find("RecordRef")
                if nameelem is not None:
                    path.append(op.dirname(target.find("RecordRef").text))
                target=target.getparent()
            path = op.join(dirname, *reversed(path))
            if op.isfile(path) and op.getsize(path):
                massData.append((path,columnInfo))

        #parse all data matrices
        L = len(massData)
        idx = 0
        for f, cols in massData:
            basename = op.basename(op.dirname(f))
            self.app.log.info(f"extracting datamatrix {f}...")
            dtypes = self.getdtypes(cols)
            data = np.fromfile(f, dtype=dtypes)
            df = pd.DataFrame(data)
            for x in df.columns:
                if x.startswith("$pad"):
                    del df[x]
            dataframes.append(df)

        return dataframes

    def getdtypes(self, cols):
        dtypeListlist = []
        dt = np.dtype([('a', 'i4'), ('b', 'i4'), ('c', 'i4'), ('d', 'f4'), ('e', 'i4'),
                    ('f', 'i4', (256,))])

        colnames = []
        nrOfplaceHolders = 0
        for col in cols.iter("Column"):

            quantityName = col.find("Quantity").text
            signame = col.find("Signal").text.replace("\\","").replace("_","/")
            if signame in colnames: quantityName = "IGNORE"
            else:                   colnames.append(signame)
            unit = col.find("Unit").text
            fullname = signame+"_"+quantityName#+"_"+unit
            if   quantityName is None:
                raise UserWarning("invalid rawdata")

            elif quantityName == "Logical":
                dtypeListlist.append((fullname,'b'))
                dtypeListlist.append((f"$pad{nrOfplaceHolders}",'V7'))
                nrOfplaceHolders+=1
                #mask="b7x"

            elif quantityName in ["Integer", "Integer Flag"]:
                dtypeListlist.append((f"$pad{nrOfplaceHolders}",'V4'))
                dtypeListlist.append((fullname,'i4'))
                nrOfplaceHolders+=1

            elif quantityName in ["Text", "IGNORE"]:
                #dtypeListlist.append((fullname,'i4'))
                dtypeListlist.append((f"$pad{nrOfplaceHolders}",'V8'))
                nrOfplaceHolders+=1

            else:
                type = np.dtype('d')
                dtypeListlist.append((fullname,type))

        return np.dtype(dtypeListlist)

    def _recursiveResolveXMLchildren(self, xml, dirname):
        for ch in list(xml.iterchildren("Child")):
            file = op.join(dirname, ch.find("RecordRef").text)
            tmproot = etree.parse(file).getroot()
            chxml = tmproot
            #if not chxml: continue
            #tmproot.remove(chxml)
            namechild = etree.SubElement(chxml, "Name")
            namechild.text = ch.find("Name").text
            recordchild = etree.SubElement(chxml, "RecordRef")
            recordchild.text = ch.find("RecordRef").text
            xml.remove(ch)
            chxml.tag = namechild.text.replace(" ","")
            xml.append(chxml)