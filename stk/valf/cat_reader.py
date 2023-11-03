"""
stk/valf/cat_reader
-------------------

The component for reading collection play list from DB.

:org:           Continental AG
:author:        Sorin Mogos

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:44CEST $
"""
# - import STK modules ------------------------------------------------------------------------------------------------
from stk.valf.obs.coll_reader import CollectionReader


# - classes -----------------------------------------------------------------------------------------------------------
class CATReader(CollectionReader):
    """
    Observer class to handle collection lists provided by Catalog DB
    called by Process_Manager during the different states.

    CATReader is replaced by `CollectionReader` providing an easy interface to handle both:
    bpl files and catalog collections.
    """
    def __init__(self, data_manager, component_name, bus_name="BUS_BASE"):
        """deprecated"""
        CollectionReader.__init__(self, data_manager, component_name, bus_name, cat=True)


"""
CHANGE LOG:
-----------
$Log: cat_reader.py  $
Revision 1.1 2015/04/23 19:05:44CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.23 2015/03/12 10:44:47CET Mertens, Sven (uidv7805) 
using absolute import
--- Added comments ---  uidv7805 [Mar 12, 2015 10:44:47 AM CET]
Change Package : 314923:4 http://mks-psad:7002/im/viewissue?selection=314923
Revision 1.22 2015/03/03 09:45:23CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Mar 3, 2015 9:45:23 AM CET]
Change Package : 312115:1 http://mks-psad:7002/im/viewissue?selection=312115
Revision 1.21 2015/02/10 19:39:45CET Hospes, Gerd-Joachim (uidv8815)
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:39:47 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.20 2015/01/12 13:41:49CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Jan 12, 2015 1:41:49 PM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.19 2014/12/19 13:42:57CET Mertens, Sven (uidv7805)
making coll-reader compatible with cat-reader
--- Added comments ---  uidv7805 [Dec 19, 2014 1:42:57 PM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.18 2014/10/09 20:44:10CEST Hecker, Robert (heckerr)
Example usage and change for deprecated porperty.
--- Added comments ---  heckerr [Oct 9, 2014 8:44:10 PM CEST]
Change Package : 270819:1 http://mks-psad:7002/im/viewissue?selection=270819
Revision 1.17 2014/09/22 17:44:25CEST Hospes, Gerd-Joachim (uidv8815)
correct string for sim_file_base
--- Added comments ---  uidv8815 [Sep 22, 2014 5:44:27 PM CEST]
Change Package : 265727:1 http://mks-psad:7002/im/viewissue?selection=265727
Revision 1.16 2014/09/22 16:30:48CEST Hospes, Gerd-Joachim (uidv8815)
file names as strings
--- Added comments ---  uidv8815 [Sep 22, 2014 4:30:49 PM CEST]
Change Package : 265727:1 http://mks-psad:7002/im/viewissue?selection=265727
Revision 1.15 2014/09/22 13:02:27CEST Hospes, Gerd-Joachim (uidv8815)
add _tstp exclude for sim output file list
--- Added comments ---  uidv8815 [Sep 22, 2014 1:02:28 PM CEST]
Change Package : 265726:1 http://mks-psad:7002/im/viewissue?selection=265726
Revision 1.14 2014/08/29 13:48:20CEST Hospes, Gerd-Joachim (uidv8815)
using new module stk.util.tds and its functions to change LIFS010 to fast server
--- Added comments ---  uidv8815 [Aug 29, 2014 1:48:21 PM CEST]
Change Package : 259660:1 http://mks-psad:7002/im/viewissue?selection=259660
Revision 1.13 2014/03/26 14:26:09CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 26, 2014 2:26:10 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.12 2013/05/29 13:52:19CEST Mertens, Sven (uidv7805)
adding pylint ignores locally,
removing isinstance (as explained)
--- Added comments ---  uidv7805 [May 29, 2013 1:52:19 PM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
add feature "SimSelection" to enter list of indices for particular bpl/cat list selection
--- Added comments ---  uidv8815 [May 22, 2013 5:57:00 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.10 2013/04/19 12:50:10CEST Hecker, Robert (heckerr)
Functionality revert to version 1.8.
--- Added comments ---  heckerr [Apr 19, 2013 12:50:10 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.9 2013/04/12 14:46:57CEST Mertens, Sven (uidv7805)
enabling the use of a connection string on observer level.
Each of them is allowed to have an additional InputData in config,
e.g. ("connectionString", "DBQ=racadmpe;Uid=DEV_MFC31X_ADMIN;Pwd=MFC31X_ADMIN"),
("dbPrefix", "DEV_MFC31X_ADMIN.").
--- Added comments ---  uidv7805 [Apr 12, 2013 2:46:57 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.8 2013/03/28 15:25:12CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
--- Added comments ---  uidv7805 [Mar 28, 2013 3:25:13 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.7 2013/03/28 14:20:04CET Mertens, Sven (uidv7805)
pylint: solving some W0201 (Attribute %r defined outside __init__) errors
--- Added comments ---  uidv7805 [Mar 28, 2013 2:20:04 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.6 2013/03/28 09:33:14CET Mertens, Sven (uidv7805)
pylint: removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 9:33:14 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.5 2013/03/01 10:23:22CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 10:23:22 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/28 08:12:18CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:18 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/26 20:18:04CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:18:05 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.2 2013/02/20 08:21:25CET Hecker, Robert (heckerr)
Adapted to Pep8 Coding Style.
--- Added comments ---  heckerr [Feb 20, 2013 8:21:26 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/11 11:06:05CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/valf/project.pj
------------------------------------------------------------------------------
-- From etk/valf Archive
------------------------------------------------------------------------------
Revision 1.13 2012/08/22 09:35:31CEST Mogos, Sorin (mogoss)
* update: added optinal port 'ExactMatch' for exact matchng between the
files given in the collection and the simulation binaries
--- Added comments ---  mogoss [Aug 22, 2012 9:35:34 AM CEST]
Change Package : 155168:1 http://mks-psad:7002/im/viewissue?selection=155168
Revision 1.12 2012/07/20 13:38:52CEST Raedler-EXT, Guenther (uidt9430)
- improved parsing of sim_output folder. Use regex instead of glob.glob()
--- Added comments ---  uidt9430 [Jul 20, 2012 1:38:53 PM CEST]
Change Package : 136608:1 http://mks-psad:7002/im/viewissue?selection=136608
Revision 1.11 2012/04/24 11:59:40CEST Spruck, Jochen (spruckj)
Add the posibility to read in only export files with a defined post fix
name to the recfilename
--- Added comments ---  spruckj [Apr 24, 2012 11:59:41 AM CEST]
Change Package : 98074:3 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.10 2011/10/31 11:40:12CET Mogos, Sorin (mogoss)
* change: changed stk library path
--- Added comments ---  mogoss [Oct 31, 2011 11:40:13 AM CET]
Change Package : 85403:1 http://mks-psad:7002/im/viewissue?selection=85403
Revision 1.9 2011/08/25 14:59:01CEST Sorin Mogos (mogoss)
* change: remove bpl related code
--- Added comments ---  mogoss [Aug 25, 2011 2:59:02 PM CEST]
Change Package : 75815:1 http://mks-psad:7002/im/viewissue?selection=75815
Revision 1.8 2011/08/12 17:43:39CEST Sorin Mogos (mogoss)
* update: added support for bpl file in case that it's set and
collection not specified
--- Added comments ---  mogoss [Aug 12, 2011 5:43:39 PM CEST]
Change Package : 72325:1 http://mks-psad:7002/im/viewissue?selection=72325
Revision 1.7 2011/08/11 13:30:49CEST Sorin Mogos (mogoss)
* fix: some database connection bug-fixes
* fix: improved error handling
--- Added comments ---  mogoss [Aug 11, 2011 1:30:49 PM CEST]
Change Package : 72325:1 http://mks-psad:7002/im/viewissue?selection=72325
Revision 1.6 2011/08/10 12:48:18CEST Sorin Mogos (mogoss)
* fix: unicode to ascii conversion for meas file
--- Added comments ---  mogoss [Aug 10, 2011 12:48:18 PM CEST]
Change Package : 72325:1 http://mks-psad:7002/im/viewissue?selection=72325
"""
