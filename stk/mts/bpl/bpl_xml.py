"""
bpl_xml
-------

Classes for BPL (BatchPlayList) Handling

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.3 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/07/22 13:33:20CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from xml.etree.ElementTree import Element, SubElement, tostring, parse
from xml.dom.minidom import parseString
from xml.sax.saxutils import escape

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.mts.bpl.bpl_base import BplReaderIfc, BplException, BplListEntry

# - clases ------------------------------------------------------------------------------------------------------------


class BPLXml(BplReaderIfc):
    """
    Specialized BPL Class which handles only
    writing and reading of *.bpl Files.
    This class is not a customer Interface,
    it should only be used internal of stk.

    :author:        Robert Hecker
    :date:          12.02.2013
    """
    def __init__(self, filepath):
        """init some internal things"""
        BplReaderIfc.__init__(self, filepath)

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
            root = parse(self._filepath).getroot()
            assert root.tag == "BatchList"
        except:
            raise BplException("'%s' is not a BPL file!" % self._filepath, 1)

        self._rec_list.clear()
        for entry in root:
            rec = BplListEntry(escape(entry.get("fileName")))
            seclist = entry.findall('SectionList')
            for sectelem in seclist:
                sections = sectelem.findall('Section')
                for section in sections:
                    try:
                        start = section.get('startTime')
                        end = section.get('endTime')
                        rel = start.upper().endswith('R')
                        start, end = start.strip('rR'), end.strip('rR')
                        rec.append(long(start), long(end), rel)
                    except ValueError as ex:
                        raise BplException("BPL entry {}, section {} \ncaused error: {}".
                                           format(rec, section.attrib, str(ex)), 1)
                    except AttributeError:
                        raise BplException("BPL entry {}, section {}\nneeds to define 'startTime' and 'endTime'".
                                           format(rec, section.attrib), 1)
            self._rec_list.append(rec)

        return self._rec_list

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
        for rec in self._rec_list:
            entry = SubElement(top, "BatchEntry", {'fileName': rec.filepath})
            secent = SubElement(entry, "SectionList")

            for section in rec:
                SubElement(secent, "Section", {'startTime': "%d%s" % (section.start_ts, "R" if section.rel else ""),
                                               'endTime': "%d%s" % (section.end_ts, "R" if section.rel else "")})

        with open(self._filepath, "wb") as fpo:
            fpo.write(parseString(tostring(top, 'utf-8')).toprettyxml(indent='    ', encoding='UTF-8'))


"""
CHANGE LOG:
-----------
$Log: bpl_xml.py  $
Revision 1.3 2016/07/22 13:33:20CEST Hospes, Gerd-Joachim (uidv8815) 
error with rec file name if section definition is wrong
Revision 1.2 2015/07/10 15:34:39CEST Hospes, Gerd-Joachim (uidv8815)
fix BplXml parse error with other sub elements than SectionList
- Added comments -  uidv8815 [Jul 10, 2015 3:34:40 PM CEST]
Change Package : 356106:1 http://mks-psad:7002/im/viewissue?selection=356106
Revision 1.1 2015/04/23 19:04:42CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/mts/bpl/project.pj
Revision 1.23 2015/02/06 08:10:04CET Mertens, Sven (uidv7805)
using absolute imports
--- Added comments ---  uidv7805 [Feb 6, 2015 8:10:05 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.22 2014/12/09 09:40:37CET Mertens, Sven (uidv7805)
return code alignment
--- Added comments ---  uidv7805 [Dec 9, 2014 9:40:37 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.21 2014/12/08 13:15:10CET Mertens, Sven (uidv7805)
moving append to base class and
- fixing append(str(value)) to only append(value)
--- Added comments ---  uidv7805 [Dec 8, 2014 1:15:11 PM CET]
Change Package : 288767:1 http://mks-psad:7002/im/viewissue?selection=288767
Revision 1.20 2014/12/08 13:08:12CET Mertens, Sven (uidv7805)
update according related CR
--- Added comments ---  uidv7805 [Dec 8, 2014 1:08:12 PM CET]
Change Package : 288767:1 http://mks-psad:7002/im/viewissue?selection=288767
Revision 1.19 2014/11/11 19:53:13CET Hecker, Robert (heckerr)
Added new diff function.
--- Added comments ---  heckerr [Nov 11, 2014 7:53:13 PM CET]
Change Package : 280240:1 http://mks-psad:7002/im/viewissue?selection=280240
Revision 1.18 2014/11/05 15:33:33CET Ahmed, Zaheer (uidu7634)
added get_bpl_list_entries(). Bug fix in __write_section() to write R as well
for section relative end timestamp as per MTS behavior
--- Added comments ---  uidu7634 [Nov 5, 2014 3:33:34 PM CET]
Change Package : 274722:1 http://mks-psad:7002/im/viewissue?selection=274722
Revision 1.17 2014/10/13 13:17:44CEST Mertens, Sven (uidv7805)
removing some pylints
--- Added comments ---  uidv7805 [Oct 13, 2014 1:17:45 PM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.16 2014/10/13 11:14:54CEST Mertens, Sven (uidv7805)
fix for rec list entries to be read out double
--- Added comments ---  uidv7805 [Oct 13, 2014 11:14:54 AM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.15 2014/07/31 11:53:40CEST Hecker, Robert (heckerr)
updated needed imports + small changes.
--- Added comments ---  heckerr [Jul 31, 2014 11:53:40 AM CEST]
Change Package : 252989:1 http://mks-psad:7002/im/viewissue?selection=252989
Revision 1.14 2014/03/24 21:08:11CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:08:11 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.13 2014/03/20 16:48:14CET Hecker, Robert (heckerr)
Updated Code.
--- Added comments ---  heckerr [Mar 20, 2014 4:48:14 PM CET]
Change Package : 224339:1 http://mks-psad:7002/im/viewissue?selection=224339
Revision 1.12 2014/03/16 21:55:54CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:55 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.11 2013/08/27 14:42:07CEST Hecker, Robert (heckerr)
Resolved returning of empty list.
--- Added comments ---  heckerr [Aug 27, 2013 2:42:07 PM CEST]
Change Package : 195175:1 http://mks-psad:7002/im/viewissue?selection=195175
Revision 1.10 2013/07/04 17:50:01CEST Hecker, Robert (heckerr)
Removed pep8 violations.
--- Added comments ---  heckerr [Jul 4, 2013 5:50:01 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.9 2013/07/01 08:55:18CEST Hecker, Robert (heckerr)
Some Renamings from Rec... to Bpl...
Revision 1.8 2013/06/26 17:35:48CEST Hecker, Robert (heckerr)
Made some methods privat, for clear user interface.
--- Added comments ---  heckerr [Jun 26, 2013 5:35:48 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.7 2013/06/26 17:19:02CEST Hecker, Robert (heckerr)
Some finetuning in docstrings and importing.
Revision 1.6 2013/06/26 16:02:40CEST Hecker, Robert (heckerr)
Reworked bpl sub-package.
Revision 1.5 2013/06/26 10:23:25CEST Hecker, Robert (heckerr)
Increased ModuleTest Coverage for Bpl() Class.

- Get split method working and created Module Tests.
- Get write Method working and created Module Tests.
--- Added comments ---  heckerr [Jun 26, 2013 10:23:25 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.4 2013/06/06 12:32:40CEST Raedler, Guenther (uidt9430)
- fix error due to pep8 corrections
--- Added comments ---  uidt9430 [Jun 6, 2013 12:32:41 PM CEST]
Change Package : 184344:1 http://mks-psad:7002/im/viewissue?selection=184344
Revision 1.3 2013/04/03 08:02:20CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:20 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.2 2013/03/01 09:47:22CET Hecker, Robert (heckerr)
Updates Regarding Pep8.
--- Added comments ---  heckerr [Mar 1, 2013 9:47:22 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/13 09:36:18CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/mts/project.pj
"""
