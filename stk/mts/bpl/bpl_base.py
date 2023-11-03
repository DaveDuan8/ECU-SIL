"""
bpl_base
--------

Classes for BPL (BatchPlayList) Handling

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/07/22 18:06:10CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from abc import ABCMeta, abstractmethod

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.error import StkError


# - classes -----------------------------------------------------------------------------------------------------------
class BplException(StkError):
    """used by Bpl class to indicate file handling problems

    **errno:**

        - 1: file format wrong
        - 2: file cannot be opened
    """
    def __init__(self, msg, errno):
        StkError.__init__(self, msg, errno)


class BplReaderIfc(object):
    """interface for BplReader Subclasses, like BPLIni, BPLtxt, BPLxml"""
    __metaclass__ = ABCMeta

    def __init__(self, filepath):
        """holding path to file and rec list
        """
        self._filepath = filepath
        self._rec_list = BplList()

    def __str__(self):
        """my repr"""
        return "<BPL file '%s'>" % self._filepath

    @abstractmethod
    def read(self):
        """init"""
        pass

    @abstractmethod
    def write(self):
        """
        Write the complete list inside the internal storage into a file.

        :return:     nothing
        :rtype:      None
        :raise e:    if file writing fails.
        :author:     Robert Hecker
        :date:       12.02.2013
        """
        pass

    def append(self, value):
        """
        Appends a new BPL-Entry into the internal Storage.

        :param value: BpllistEntry with Section information.
        :type value:  BplListEntry
        :return:     nothing
        :rtype:      None
        :raise e:    if append fails.
        :author:     Robert Hecker
        :date:       12.02.2013
        """
        self._rec_list.append(value)

    def get_bpl_list_entries(self):
        """
        Get list of `BplListEntry` under the BPL
        :return:     List of `BplListEntry`
        :rtype:      list
        """
        return self._rec_list


class BplListEntry(object):
    """
    This class is a Data-Container which holds following Information:
     - RecFilePath
     - list of all Sections applied to the file.

    :author:        Robert Hecker
    :date:          26.06.2013
    """
    def __init__(self, filepath):
        """set default values
        :param filepath: full path to rec file
        :type filepath:  str
        """
        self.filepath = filepath.strip()
        self._sectionlist = []
        self._iter_idx = 0

    def append(self, start_ts, end_ts, rel):
        """
        append one section entry into this BplListEntry.

        :param start_ts: StartTimestamp of Section
        :type start_ts:  uint
        :param end_ts:   EndTimestamp of Section
        :type end_ts:    uint
        :param rel:      relative Timestamp Format (True/False)
        :type rel:       bool
        :return:         -
        :rtype:          -
        :author:         Robert Hecker
        :date:           20.06.2013
        """
        self._sectionlist.append(Section(start_ts, end_ts, rel))

    def has_sections(self):
        """
        check if bpllistentry contains at least one section.

        :return: True if entry contains sections, otherwise False
        :rtype: bool
        """
        return len(self._sectionlist) > 0

    def get_sections(self):
        """
        return sections under bpllistentry

        :return: list of `Section`
        :rtype: list
        """
        return self._sectionlist

    @property
    def sectionlist(self):
        """kept for backward compatibility

        please use iterator instead if possible:

        ..python::

            for section in listentry:
                print(section)
        """
        return self._sectionlist

    def __len__(self):
        """:return: amount of sections in list"""
        return len(self._sectionlist)

    def __getitem__(self, item):
        """:return: returns a specific entry"""
        return self._sectionlist[item]

    def __iter__(self):
        """start iterating through sections"""
        self._iter_idx = 0
        return self

    def next(self):
        """:return: next section from list"""
        if self._iter_idx < len(self._sectionlist):
            self._iter_idx += 1
            return self._sectionlist[self._iter_idx - 1]
        else:
            raise StopIteration

    def __str__(self):
        """:return: path to my own"""
        return str(self.filepath)

    def __eq__(self, other):
        if isinstance(other, BplListEntry):
            return self.filepath == other.filepath
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result


class BplList(list):
    """
    This class is the main data-container for the Bpl()-Class.
    It is build out of a list of BplListEntries

    :author:        Robert Hecker
    :date:          26.06.2013
    """
    def __init__(self):
        list.__init__(self)

    def bpl2dict(self):
        """
        converts the BplList to a dictionary, it leaves out the relative Timestamp flag!!

        You need to know / check by yourself if the Timestamps are relative or absolute

        :return: dict with all sections per recfile {'rec1':[(23, 34), (47, 52)], 'rec2:[(31, 78)], ...}
        :rtype:  dictionary

        :author: Joachim Hospes
        :date:   17.07.2014
        """
        return {b.filepath: [(s.start_ts, s.end_ts) for s in b] for b in self}

    def clear(self):
        """
        delete the whole internal RecFileList.

        :author:        Robert Hecker
        :date:          20.06.2013
        """
        self.__delslice__(0, len(self))


class Section(object):
    """
    This class is a Data-Container which hold the Section Information
    for bpl-lists.

    :author:        Robert Hecker
    :date:          26.06.2013
    """
    def __init__(self, start_ts, end_ts, rel):
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.rel = rel

    def __str__(self):
        return str({"start_ts": self.start_ts, "end_ts": self.end_ts, 'rel': self.rel})

    def sect2list(self):
        """converts Section in tuple like (start_ts, end_ts, rel)
        """
        return self.start_ts, self.end_ts, self.rel


"""
CHANGE LOG:
-----------
$Log: bpl_base.py  $
Revision 1.2 2016/07/22 18:06:10CEST Hospes, Gerd-Joachim (uidv8815) 
strip to BplEntry filepath, no extra test for now
Revision 1.1 2015/04/23 19:04:41CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/mts/bpl/project.pj
Revision 1.13 2015/04/23 15:19:10CEST Hospes, Gerd-Joachim (uidv8815)
enhance docu
--- Added comments ---  uidv8815 [Apr 23, 2015 3:19:10 PM CEST]
Change Package : 328888:1 http://mks-psad:7002/im/viewissue?selection=328888
Revision 1.12 2015/03/11 17:25:50CET Hospes, Gerd-Joachim (uidv8815)
remove replacement of lifs
--- Added comments ---  uidv8815 [Mar 11, 2015 5:25:50 PM CET]
Change Package : 316149:1 http://mks-psad:7002/im/viewissue?selection=316149
Revision 1.11 2015/02/06 08:09:26CET Mertens, Sven (uidv7805)
using absolute imports
--- Added comments ---  uidv7805 [Feb 6, 2015 8:09:26 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.10 2014/12/08 13:15:07CET Mertens, Sven (uidv7805)
moving append to base class and
- fixing append(str(value)) to only append(value)
--- Added comments ---  uidv7805 [Dec 8, 2014 1:15:08 PM CET]
Change Package : 288767:1 http://mks-psad:7002/im/viewissue?selection=288767
Revision 1.9 2014/12/08 13:08:02CET Mertens, Sven (uidv7805)
update according related CR
--- Added comments ---  uidv7805 [Dec 8, 2014 1:08:02 PM CET]
Change Package : 288767:1 http://mks-psad:7002/im/viewissue?selection=288767
Revision 1.8 2014/11/27 15:19:37CET Mertens, Sven (uidv7805)
real list inheritance usage as list already has slicing implemented
--- Added comments ---  uidv7805 [Nov 27, 2014 3:19:37 PM CET]
Change Package : 283682:1 http://mks-psad:7002/im/viewissue?selection=283682
Revision 1.7 2014/11/05 15:30:23CET Ahmed, Zaheer (uidu7634)
defined get_bpl_list_entries in abstract class
added get_sections function
--- Added comments ---  uidu7634 [Nov 5, 2014 3:30:24 PM CET]
Change Package : 274722:1 http://mks-psad:7002/im/viewissue?selection=274722
Revision 1.6 2014/10/13 13:17:42CEST Mertens, Sven (uidv7805)
removing some pylints
--- Added comments ---  uidv7805 [Oct 13, 2014 1:17:43 PM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.5 2014/10/13 11:14:06CEST Mertens, Sven (uidv7805)
moving BplList, PplListEntry and Section class to base as being recursively imported
--- Added comments ---  uidv7805 [Oct 13, 2014 11:14:07 AM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.4 2014/07/31 11:50:18CEST Hecker, Robert (heckerr)
Added ReaderInterface.
--- Added comments ---  heckerr [Jul 31, 2014 11:50:18 AM CEST]
Change Package : 252989:1 http://mks-psad:7002/im/viewissue?selection=252989
Revision 1.3 2013/06/26 10:23:24CEST Hecker, Robert (heckerr)
Increased ModuleTest Coverage for Bpl() Class.
- Get split method working and created Module Tests.
- Get write Method working and created Module Tests.
--- Added comments ---  heckerr [Jun 26, 2013 10:23:24 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.2 2013/03/01 09:47:21CET Hecker, Robert (heckerr)
Updates Regarding Pep8.
--- Added comments ---  heckerr [Mar 1, 2013 9:47:21 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/13 09:36:16CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
    05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/mts/project.pj
"""
