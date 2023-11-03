"""
bpl_base
--------

Classes for BPL (BatchPlayList) Handling

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 20:58:03CET $
"""
# - import STK modules ------------------------------------------------------------------------------------------------
from framework.util.error import StkError


# - classes -----------------------------------------------------------------------------------------------------------
class BplException(StkError):
    """used by Bpl class to indicate file handling problems

    **errno:**

        - 1: file format wrong
        - 2: file cannot be opened
    """
    def __init__(self, msg, errno):
        StkError.__init__(self, msg, errno)


class BplList(list):
    """
    This class is the main data-container for the Bpl()-Class.
    It is build out of a list of BplListEntries

    :author:        Robert Hecker
    :date:          26.06.2013
    """
    def __init__(self):
        super(list, self).__init__()

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


class BplReaderIfc(BplList):
    """interface for BplReader Subclasses, like BPLIni, BPLtxt, BPLxml"""
    def __init__(self, filepath, *args, **kwargs):
        """holding path to file and rec list
        """
        BplList.__init__(self)

        self._kwargs = kwargs
        self._mode = args[0] if len(args) > 0 else "r"

        if not hasattr(filepath, 'read'):
            self.filepath = filepath
            self._fp = None
        else:
            self.filepath = filepath.name
            self._fp = filepath

        self._iter_idx = 0

    def __enter__(self):
        """support with statement"""
        if self._mode in ["r", "a"]:
            self.read()

        return self

    def __exit__(self):
        """support with statement"""
        if self._mode in ["w", "a"]:
            self.write()

    def __str__(self):
        """my repr"""
        return "<BPL: '%s'>" % self.filepath

    def read(self):
        """init"""

    def write(self):
        """
        Write the complete list inside the internal storage into a file.

        :return:     nothing
        :rtype:      None
        :raise e:    if file writing fails.
        :author:     Robert Hecker
        :date:       12.02.2013
        """

    def get_bpl_list_entries(self):
        """
        Get list of `BplListEntry` under the BPL
        :return:     List of `BplListEntry`
        :rtype:      list
        """
        return self


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
        :type rel:       tuple
        :return:         -
        :rtype:          -
        :author:         Robert Hecker
        :date:           20.06.2013
        """
        self._sectionlist.append(Section(start_ts, end_ts, rel if type(rel) == tuple else (rel, rel,)))

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

        .. code-block:: python

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
Revision 1.1 2020/03/25 20:58:03CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/bpl/project.pj
"""
