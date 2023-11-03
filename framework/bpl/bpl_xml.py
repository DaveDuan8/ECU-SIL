"""
bpl_xml
-------

Classes for BPL (BatchPlayList) Handling

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:00:01CEST $
"""
# - import Python modules ----------------------------------------------------------------------------------------------
from sys import version_info as vinfo
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.sax.saxutils import escape

# - import framework modules -------------------------------------------------------------------------------------------------
from framework.bpl.bpl_base import BplReaderIfc, BplException, BplListEntry

if vinfo < (3, 0):
    from types import StringTypes
else:
    StringTypes = (str,)


# - classes ------------------------------------------------------------------------------------------------------------
class BPLXml(BplReaderIfc):
    """
    Specialized BPL Class which handles only
    writing and reading of *.bpl Files.
    This class is not a customer Interface,
    it should only be used internal of framework.

    :author:        Robert Hecker
    :date:          12.02.2013
    """

    def read(self):
        """
        Read the whole content of the Batch Play List into internal storage,
        and return all entries as a list.

        :return:        List of Recording Objects
        :rtype:         BplList
        :author:        Robert Hecker
        :date:          12.02.2013
        """
        try:
            root = parse(self.filepath if self._fp is None else self._fp).getroot()
            assert root.tag == "BatchList"
        except:
            raise BplException("'%s' is not a BPL file!" % self.filepath, 1)

        self.clear()
        for entry in root:
            rec = BplListEntry(escape(entry.get("fileName")))
            seclist = entry.findall('SectionList')
            for sectelem in seclist:
                sections = sectelem.findall('Section')
                for section in sections:
                    start, stop = section.get('startTime'), section.get('endTime')
                    rel = (start.upper().endswith('R'), stop.upper().endswith('R'),)
                    start, stop = start.strip('rR'), stop.strip('rR')
                    try:
                        rec.append(int(start), int(stop), rel)
                    except ValueError as ex:
                        raise BplException("BPL entry {}, section {} \ncaused error: {}".
                                           format(rec, section.attrib, str(ex)), 1)
                    except AttributeError:
                        raise BplException("BPL entry {}, section {}\nneeds to define 'startTime' and 'endTime'".
                                           format(rec, section.attrib), 1)
            self.append(rec)

        return self

    def write(self):
        """
        Write the complete list inside the internal storage into a file.

        :return:     nothing
        :rtype:      None
        :raise e:    if file writing fails.
        :author:     Robert Hecker
        :date:       12.02.2013
        """
        top = Element('BatchList')
        for rec in self:
            if type(rec) in StringTypes:
                rec = BplListEntry(rec)
            entry = SubElement(top, "BatchEntry", {'fileName': rec.filepath})
            secent = SubElement(entry, "SectionList")

            for section in rec:
                SubElement(secent, "Section", {'startTime': "%d%s" % (section.start_ts, "R" if section.rel[0] else ""),
                                               'endTime': "%d%s" % (section.end_ts, "R" if section.rel[1] else "")})

        data = parseString(tostring(top, 'utf-8')).toprettyxml(indent='    ', encoding='UTF-8')
        if self._fp:
            self._fp.write(data)
        else:
            with open(self.filepath, "wb") as fpo:
                fpo.write(data)


"""
CHANGE LOG:
-----------
$Log: bpl_xml.py  $
Revision 1.2 2020/03/31 09:00:01CEST Leidenberger, Ralf (uidq7596) 
intial update
Revision 1.1 2020/03/25 20:58:04CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/bpl/project.pj
"""
