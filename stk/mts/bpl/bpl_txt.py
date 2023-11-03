"""
bpl_txt
-------

Classes for BPL (BatchPlayList) Handling

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/05/20 07:58:38CEST $
"""
# - import STK modules ------------------------------------------------------------------------------------------------
from stk.mts.bpl.bpl_base import BplReaderIfc, BplListEntry


# - clases ------------------------------------------------------------------------------------------------------------
class BPLTxt(BplReaderIfc):
    """Specialized BPL Class which handles only
    writing and reading of *.txt Files.
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

        :rtype: list
        :return: The list of file entries or None if there is no entry.
        """
        self._rec_list.clear()
        with open(self._filepath) as hfile:
            self._rec_list = [BplListEntry(i.strip()) for i in hfile]

        return self._rec_list

    def write(self):
        """Write the complete recfilelist to the file.

        :rtype: number or None
        :return: 0 if successfully or None if error
        """
        with open(self._filepath, "w") as hfile:
            for item in self._rec_list:
                hfile.write("%s\n" % item)


"""
CHANGE LOG:
-----------
$Log: bpl_txt.py  $
Revision 1.2 2016/05/20 07:58:38CEST Mertens, Sven (uidv7805) 
pylint fix
Revision 1.1 2015/04/23 19:04:42CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/mts/bpl/project.pj
Revision 1.11 2015/02/06 08:09:51CET Mertens, Sven (uidv7805)
using absolute imports
--- Added comments ---  uidv7805 [Feb 6, 2015 8:09:52 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.10 2014/12/08 13:15:09CET Mertens, Sven (uidv7805)
moving append to base class and
- fixing append(str(value)) to only append(value)
--- Added comments ---  uidv7805 [Dec 8, 2014 1:15:10 PM CET]
Change Package : 288767:1 http://mks-psad:7002/im/viewissue?selection=288767
Revision 1.9 2014/12/08 13:09:15CET Mertens, Sven (uidv7805)
update again because MKS has communication problems...
--- Added comments ---  uidv7805 [Dec 8, 2014 1:09:16 PM CET]
Change Package : 288767:1 http://mks-psad:7002/im/viewissue?selection=288767
Revision 1.8 2014/12/08 13:08:04CET Mertens, Sven (uidv7805)
update according related CR
--- Added comments ---  uidv7805 [Dec 8, 2014 1:08:04 PM CET]
Change Package : 288767:1 http://mks-psad:7002/im/viewissue?selection=288767
Revision 1.7 2014/11/11 19:53:07CET Hecker, Robert (heckerr)
Added new diff function.
--- Added comments ---  heckerr [Nov 11, 2014 7:53:08 PM CET]
Change Package : 280240:1 http://mks-psad:7002/im/viewissue?selection=280240
Revision 1.6 2014/11/11 10:55:30CET Hecker, Robert (heckerr)
BugFix to remove whitespaces.
--- Added comments ---  heckerr [Nov 11, 2014 10:55:31 AM CET]
Change Package : 279920:1 http://mks-psad:7002/im/viewissue?selection=279920
Revision 1.5 2014/11/05 15:29:51CET Ahmed, Zaheer (uidu7634)
added get_bpl_list_entries
--- Added comments ---  uidu7634 [Nov 5, 2014 3:29:52 PM CET]
Change Package : 274722:1 http://mks-psad:7002/im/viewissue?selection=274722
Revision 1.4 2014/10/13 13:17:44CEST Mertens, Sven (uidv7805)
removing some pylints
--- Added comments ---  uidv7805 [Oct 13, 2014 1:17:44 PM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.3 2014/10/13 11:14:53CEST Mertens, Sven (uidv7805)
fix for rec list entries to be read out double
--- Added comments ---  uidv7805 [Oct 13, 2014 11:14:54 AM CEST]
Change Package : 271081:1 http://mks-psad:7002/im/viewissue?selection=271081
Revision 1.2 2014/07/31 11:53:38CEST Hecker, Robert (heckerr)
updated needed imports + small changes.
--- Added comments ---  heckerr [Jul 31, 2014 11:53:39 AM CEST]
Change Package : 252989:1 http://mks-psad:7002/im/viewissue?selection=252989
Revision 1.1 2014/07/11 16:53:40CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/mts/project.pj
"""
