"""
stk/mts/bpl
-----------

Classes for BPL (BatchPlayList) Handling

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.4 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/07/26 16:38:46CEST $
"""
# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util.ini import Ini
from stk.mts.bpl.bpl_base import BplReaderIfc, BplListEntry

# - defines -----------------------------------------------------------------------------------------------------------
INI_FILE_SECTION_NAME = "SimBatch"
INI_FILE_FILE_COUNT = "FileCount"


# - clases ------------------------------------------------------------------------------------------------------------
class BPLIni(BplReaderIfc):
    """
    Specialized BPL Class which handles only
    writing and reading of *.ini Files.
    This class is not a customer Interface,
    it should only be used internal of stk.

    :author:        Robert Hecker
    :date:          12.02.2013
    """
    def __init__(self, filepath):
        """set up some things
        :param filepath: path to ini file
        """
        BplReaderIfc.__init__(self, filepath)

    def read(self):
        """Reads the batch play list file content.

        @rtype: list
        @return: The list of file entries or None if there is no entry.
        """
        self._rec_list.clear()
        ini = Ini()
        ini.open(self._filepath)
        count = int(ini.read_key(INI_FILE_SECTION_NAME, INI_FILE_FILE_COUNT))

        for item in range(count):
            self._rec_list.append(BplListEntry(ini.read_key(INI_FILE_SECTION_NAME, "File%d" % item).strip(' "')
                                               .replace('\\\\', '\\')))

        return self._rec_list

    def write(self):
        """Write the complete recfilelist to the file.

        @rtype: number or None
        @return: 0 if successfully or None if error
        """
        with open(self._filepath, "w") as hfile:
            hfile.write("[SimBatch]\n")
            hfile.write("FileCount=%d\n" % len(self._rec_list))

            for idx, item in enumerate(self._rec_list):
                hfile.write("File%d=\"%s\"\n" % (idx, str(item).replace('\\', '\\\\')))


"""
CHANGE LOG:
-----------
$Log: bpl_ini.py  $
Revision 1.4 2016/07/26 16:38:46CEST Mertens, Sven (uidv7805) 
move replacement
Revision 1.3 2016/07/26 16:15:07CEST Mertens, Sven (uidv7805)
a bit of simplification
Revision 1.2 2016/05/20 07:57:36CEST Mertens, Sven (uidv7805)
pylint fix
Revision 1.1 2015/04/23 19:04:41CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/mts/bpl/project.pj
Revision 1.24 2015/02/17 19:01:33CET Hospes, Gerd-Joachim (uidv8815)
fix for bug found during valfdemo test
--- Added comments ---  uidv8815 [Feb 17, 2015 7:01:34 PM CET]
Change Package : 307161:1 http://mks-psad:7002/im/viewissue?selection=307161
Revision 1.23 2015/02/06 08:09:39CET Mertens, Sven (uidv7805)
using absolute imports
--- Added comments ---  uidv7805 [Feb 6, 2015 8:09:40 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.22 2014/12/09 09:41:00CET Mertens, Sven (uidv7805)
replace of recfile name!
--- Added comments ---  uidv7805 [Dec 9, 2014 9:41:00 AM CET]
Change Package : 281273:1 http://mks-psad:7002/im/viewissue?selection=281273
Revision 1.21 2014/12/08 13:15:08CET Mertens, Sven (uidv7805)
moving append to base class and
- fixing append(str(value)) to only append(value)
--- Added comments ---  uidv7805 [Dec 8, 2014 1:15:09 PM CET]
Change Package : 288767:1 http://mks-psad:7002/im/viewissue?selection=288767
Revision 1.20 2014/12/08 13:08:03CET Mertens, Sven (uidv7805)
update according related CR
--- Added comments ---  uidv7805 [Dec 8, 2014 1:08:03 PM CET]
Change Package : 288767:1 http://mks-psad:7002/im/viewissue?selection=288767
Revision 1.19 2014/11/11 19:53:11CET Hecker, Robert (heckerr)
Added new diff function.
--- Added comments ---  heckerr [Nov 11, 2014 7:53:12 PM CET]
Change Package : 280240:1 http://mks-psad:7002/im/viewissue?selection=280240
Revision 1.18 2014/11/05 15:32:30CET Ahmed, Zaheer (uidu7634)
added get_bpl_list_entries()
--- Added comments ---  uidu7634 [Nov 5, 2014 3:32:31 PM CET]
Change Package : 274722:1 http://mks-psad:7002/im/viewissue?selection=274722
Revision 1.17 2014/10/13 13:17:43CEST Mertens, Sven (uidv7805)
removing some pylints
--- Added comments ---  uidv7805 [Oct 13, 2014 1:17:43 PM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.16 2014/10/13 11:14:52CEST Mertens, Sven (uidv7805)
fix for rec list entries to be read out double
--- Added comments ---  uidv7805 [Oct 13, 2014 11:14:53 AM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.15 2014/07/31 11:53:37CEST Hecker, Robert (heckerr)
updated needed imports + small changes.
--- Added comments ---  heckerr [Jul 31, 2014 11:53:38 AM CEST]
Change Package : 252989:1 http://mks-psad:7002/im/viewissue?selection=252989
Revision 1.14 2014/03/24 21:08:10CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 24, 2014 9:08:11 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.13 2014/03/16 21:55:46CET Hecker, Robert (heckerr)
added pylintrc.
--- Added comments ---  heckerr [Mar 16, 2014 9:55:46 PM CET]
Change Package : 225494:1 http://mks-psad:7002/im/viewissue?selection=225494
Revision 1.12 2013/07/04 17:47:12CEST Hecker, Robert (heckerr)
Removed some pep8 violations.
--- Added comments ---  heckerr [Jul 4, 2013 5:47:12 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.11 2013/07/01 08:54:25CEST Hecker, Robert (heckerr)
Some Renamings from Rec... to Bpl...
Revision 1.10 2013/06/26 17:35:08CEST Hecker, Robert (heckerr)
REmoved unused Code.
Revision 1.9 2013/06/26 17:19:02CEST Hecker, Robert (heckerr)
Some finetuning in docstrings and importing.
Revision 1.8 2013/06/26 16:02:39CEST Hecker, Robert (heckerr)
Reworked bpl sub-package.
Revision 1.7 2013/06/26 10:23:25CEST Hecker, Robert (heckerr)
Increased ModuleTest Coverage for Bpl() Class.

- Get split method working and created Module Tests.
- Get write Method working and created Module Tests.
Revision 1.6 2013/04/10 09:29:35CEST Mertens, Sven (uidv7805)
file -> f (fix)
--- Added comments ---  uidv7805 [Apr 10, 2013 9:29:36 AM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.5 2013/04/03 08:02:11CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:11 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.4 2013/03/01 09:47:21CET Hecker, Robert (heckerr)
Updates Regarding Pep8.
--- Added comments ---  heckerr [Mar 1, 2013 9:47:21 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/27 17:55:09CET Hecker, Robert (heckerr)
Removed all E000 - E200 Errors regarding Pep8.
--- Added comments ---  heckerr [Feb 27, 2013 5:55:09 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/20 11:51:39CET Hospes, Gerd-Joachim (uidv8815)
fix bpl ini write to use double backslash in path names
--- Added comments ---  uidv8815 [Feb 20, 2013 11:51:39 AM CET]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.1 2013/02/13 09:36:17CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/mts/project.pj
"""
