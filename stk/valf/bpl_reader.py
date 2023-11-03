"""
stk/valf/bpl_reader
-------------------

The component for reading mts batch play list.

**User-API Interfaces**

    - `stk.valf` (complete package)
    - `BPLReader` (this module)


:org:           Continental AG
:author:        Sorin Mogos

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:43CEST $

"""
# - import STK modules ------------------------------------------------------------------------------------------------
from stk.valf.obs.coll_reader import CollectionReader


# - classes -----------------------------------------------------------------------------------------------------------
class BPLReader(CollectionReader):
    """
    Observer class to handle Batch Play Lists provided by a bpl file
    called by Process_Manager during the different states.

    BPLReader is replaced by `CollectionReader` providing an easy interface to handle both:
    bpl files and catalog collections.
    """
    def __init__(self, data_manager, component_name, bus_name="BUS_BASE"):
        """deprecated"""
        CollectionReader.__init__(self, data_manager, component_name, bus_name, bpl=True)


"""
$Log: bpl_reader.py  $
Revision 1.1 2015/04/23 19:05:43CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.46 2015/03/12 10:44:31CET Mertens, Sven (uidv7805) 
using absolute import
--- Added comments ---  uidv7805 [Mar 12, 2015 10:44:32 AM CET]
Change Package : 314923:4 http://mks-psad:7002/im/viewissue?selection=314923
Revision 1.45 2015/03/03 09:46:05CET Mertens, Sven (uidv7805)
docu update (provided now by CollectionReader)
--- Added comments ---  uidv7805 [Mar 3, 2015 9:46:05 AM CET]
Change Package : 312115:1 http://mks-psad:7002/im/viewissue?selection=312115
Revision 1.44 2015/01/12 13:41:50CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Jan 12, 2015 1:41:50 PM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.43 2014/12/19 11:26:53CET Mertens, Sven (uidv7805)
- alignment of BplReader and CollectionReader,
- using walk / listdir without isfile check first to speed up a bit
--- Added comments ---  uidv7805 [Dec 19, 2014 11:26:53 AM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.42 2014/11/21 10:19:47CET Hospes, Gerd-Joachim (uidv8815)
update ports class docu
--- Added comments ---  uidv8815 [Nov 21, 2014 10:19:47 AM CET]
Change Package : 282158:1 http://mks-psad:7002/im/viewissue?selection=282158
Revision 1.41 2014/09/25 11:51:58CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fix
--- Added comments ---  uidv8815 [Sep 25, 2014 11:51:59 AM CEST]
Change Package : 265727:1 http://mks-psad:7002/im/viewissue?selection=265727
Revision 1.40 2014/09/22 17:48:06CEST Hospes, Gerd-Joachim (uidv8815)
fix correction
--- Added comments ---  uidv8815 [Sep 22, 2014 5:48:08 PM CEST]
Change Package : 265727:1 http://mks-psad:7002/im/viewissue?selection=265727
Revision 1.39 2014/09/22 17:44:21CEST Hospes, Gerd-Joachim (uidv8815)
correct string for sim_file_base
--- Added comments ---  uidv8815 [Sep 22, 2014 5:44:24 PM CEST]
Change Package : 265727:1 http://mks-psad:7002/im/viewissue?selection=265727
Revision 1.38 2014/09/22 16:43:50CEST Hospes, Gerd-Joachim (uidv8815)
file names as string for the data ports
--- Added comments ---  uidv8815 [Sep 22, 2014 4:43:51 PM CEST]
Change Package : 265727:1 http://mks-psad:7002/im/viewissue?selection=265727
Revision 1.37 2014/09/22 13:02:18CEST Hospes, Gerd-Joachim (uidv8815)
add _tstp exclude for sim output file list
--- Added comments ---  uidv8815 [Sep 22, 2014 1:02:19 PM CEST]
Change Package : 265726:1 http://mks-psad:7002/im/viewissue?selection=265726
Revision 1.36 2014/09/19 16:42:16CEST Hospes, Gerd-Joachim (uidv8815)
add test to catch load for several files without sections
--- Added comments ---  uidv8815 [Sep 19, 2014 4:42:16 PM CEST]
Change Package : 264210:1 http://mks-psad:7002/im/viewissue?selection=264210
Revision 1.35 2014/09/19 14:47:52CEST Hospes, Gerd-Joachim (uidv8815)
fix bracket position
Revision 1.34 2014/09/19 13:37:19CEST Hospes, Gerd-Joachim (uidv8815)
add CurrentSections to provide sections provided in bpl file, update test_bpl
--- Added comments ---  uidv8815 [Sep 19, 2014 1:37:19 PM CEST]
Change Package : 264210:1 http://mks-psad:7002/im/viewissue?selection=264210
Revision 1.33 2014/09/18 15:10:44CEST Hospes, Gerd-Joachim (uidv8815)
allow boolean False to deactivate ExactMatch, test updated
--- Added comments ---  uidv8815 [Sep 18, 2014 3:10:44 PM CEST]
Change Package : 264211:1 http://mks-psad:7002/im/viewissue?selection=264211
Revision 1.32 2014/08/29 13:49:25CEST Hospes, Gerd-Joachim (uidv8815)
using new module stk.util.tds and its functions to change LIFS010 to fast server
--- Added comments ---  uidv8815 [Aug 29, 2014 1:49:26 PM CEST]
Change Package : 259660:1 http://mks-psad:7002/im/viewissue?selection=259660
Revision 1.31 2014/08/19 10:15:45CEST Hospes, Gerd-Joachim (uidv8815)
extend bpl docu: path is part of CurrentFile port
--- Added comments ---  uidv8815 [Aug 19, 2014 10:15:46 AM CEST]
Change Package : 253112:3 http://mks-psad:7002/im/viewissue?selection=253112
Revision 1.30 2014/03/26 14:26:13CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 26, 2014 2:26:13 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.29 2014/03/25 13:28:19CET Hospes, Gerd-Joachim (uidv8815)
bpl_reader and test updated
--- Added comments ---  uidv8815 [Mar 25, 2014 1:28:20 PM CET]
Change Package : 224411:1 http://mks-psad:7002/im/viewissue?selection=224411
Revision 1.28 2013/11/13 16:20:39CET Hospes, Gerd-Joachim (uidv8815)
add ActivateHpcAutoSplit method and usage of port HpcAutoSplit to Valf class,
updated tests and epydoc for all related files
--- Added comments ---  uidv8815 [Nov 13, 2013 4:20:40 PM CET]
Change Package : 206278:1 http://mks-psad:7002/im/viewissue?selection=206278
Revision 1.27 2013/10/18 13:58:53CEST Hospes, Gerd-Joachim (uidv8815)
correct include to adapt to new stk.__init__
--- Added comments ---  uidv8815 [Oct 18, 2013 1:58:54 PM CEST]
Change Package : 190320:1 http://mks-psad:7002/im/viewissue?selection=190320
Revision 1.26 2013/08/13 17:17:51CEST Hospes, Gerd-Joachim (uidv8815)
pep8 fixes
--- Added comments ---  uidv8815 [Aug 13, 2013 5:17:52 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.25 2013/08/12 16:35:01CEST Hospes, Gerd-Joachim (uidv8815)
fixes found with test_bpl_reader.py,  removed section handling,
needs to be reworked
--- Added comments ---  uidv8815 [Aug 12, 2013 4:35:01 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.24 2013/08/07 18:12:31CEST Hospes, Gerd-Joachim (uidv8815)
adapt to new BplList class
--- Added comments ---  uidv8815 [Aug 7, 2013 6:12:32 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.23 2013/07/04 11:17:50CEST Hospes, Gerd-Joachim (uidv8815)
changes for new module valf:
- process_manager initiates data_manager at init instead of load_config
- bpl uses correct module path
- processbar with simple 'include sys' to redirect process bar output
--- Added comments ---  uidv8815 [Jul 4, 2013 11:17:51 AM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.22 2013/05/29 15:55:31CEST Mertens, Sven (uidv7805)
ooops, missing W
--- Added comments ---  uidv7805 [May 29, 2013 3:55:31 PM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.21 2013/05/29 15:48:10CEST Mertens, Sven (uidv7805)
using local pylint ignores
Revision 1.20 2013/05/22 17:56:59CEST Hospes, Gerd-Joachim (uidv8815)
add feature "SimSelection" to enter list of indices for particular bpl/cat
list selection
--- Added comments ---  uidv8815 [May 22, 2013 5:56:59 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.19 2013/05/15 18:14:04CEST Hospes, Gerd-Joachim (uidv8815)
pylint/pep8 corrections
--- Added comments ---  uidv8815 [May 15, 2013 6:14:04 PM CEST]
Change Package : 169590:1 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.18 2013/04/12 14:47:07CEST Mertens, Sven (uidv7805)
enabling the use of a connection string on observer level.
Each of them is allowed to have an additional InputData in config,
e.g. ("connectionString", "DBQ=racadmpe;Uid=DEV_MFC31X_ADMIN;Pwd=MFC31X_ADMIN"),
("dbPrefix", "DEV_MFC31X_ADMIN.").
--- Added comments ---  uidv7805 [Apr 12, 2013 2:47:08 PM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.17 2013/04/11 14:29:44CEST Ahmed-EXT, Zaheer (uidu7634)
Exact match feature is added
--- Added comments ---  uidu7634 [Apr 11, 2013 2:29:44 PM CEST]
Change Package : 178419:2 http://mks-psad:7002/im/viewissue?selection=178419
Revision 1.16 2013/04/05 14:46:40CEST Ahmed-EXT, Zaheer (uidu7634)
Fixed bug for duplicate entries in simulation files list
--- Added comments ---  uidu7634 [Apr 5, 2013 2:46:41 PM CEST]
Change Package : 178419:2 http://mks-psad:7002/im/viewissue?selection=178419
Revision 1.15 2013/04/05 11:17:41CEST Hospes, Gerd-Joachim (uidv8815)
fix documentation
--- Added comments ---  uidv8815 [Apr 5, 2013 11:17:41 AM CEST]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.14 2013/04/03 17:17:59CEST Hospes, Gerd-Joachim (uidv8815)
next indentations
Revision 1.13 2013/04/03 17:04:27CEST Hospes, Gerd-Joachim (uidv8815)
missing indentation fixed
--- Added comments ---  uidv8815 [Apr 3, 2013 5:04:28 PM CEST]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.11 2013/04/03 13:49:27CEST Hospes, Gerd-Joachim (uidv8815)
added comments for epydoc
--- Added comments ---  uidv8815 [Apr 3, 2013 1:49:28 PM CEST]
Change Package : 169590:2 http://mks-psad:7002/im/viewissue?selection=169590
Revision 1.10 2013/04/02 10:25:47CEST Raedler, Guenther (uidt9430)
- fixed string convertion errors
--- Added comments ---  uidt9430 [Apr 2, 2013 10:25:48 AM CEST]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.9 2013/03/28 15:25:21CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
--- Added comments ---  uidv7805 [Mar 28, 2013 3:25:21 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.8 2013/03/28 09:33:22CET Mertens, Sven (uidv7805)
pylint: removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 9:33:22 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.7 2013/03/21 17:28:00CET Mertens, Sven (uidv7805)
solving minor pylint error issues
Revision 1.6 2013/03/01 10:23:21CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 10:23:22 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/28 08:12:26CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:27 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/26 20:18:08CET Raedler, Guenther (uidt9430)
- Updates after Pep8 Styleguides
--- Added comments ---  uidt9430 [Feb 26, 2013 8:18:09 PM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.3 2013/02/20 08:21:25CET Hecker, Robert (heckerr)
Adapted to Pep8 Coding Style.
--- Added comments ---  heckerr [Feb 20, 2013 8:21:25 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/13 09:41:09CET Hecker, Robert (heckerr)
Get bpl_reader working with new stk.mts.Bpl class.
--- Added comments ---  heckerr [Feb 13, 2013 9:41:09 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/11 11:06:05CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
    05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/valf/project.pj
------------------------------------------------------------------------------
-- From etk/valf Archive
------------------------------------------------------------------------------
Revision 1.20 2012/07/26 15:23:45CEST Mogos, Sorin (mogoss)
* code imporvements => sim output file search
--- Added comments ---  mogoss [Jul 26, 2012 3:23:52 PM CEST]
Change Package : 134013:1 http://mks-psad:7002/im/viewissue?selection=134013
Revision 1.19 2012/07/20 13:38:41CEST Raedler-EXT, Guenther (uidt9430)
- improved parsing of sim_output folder. Use regex instead of glob.glob()
--- Added comments ---  uidt9430 [Jul 20, 2012 1:38:52 PM CEST]
Change Package : 136608:1 http://mks-psad:7002/im/viewissue?selection=136608
Revision 1.18 2012/06/15 09:58:48CEST Mogos, Sorin (mogoss)
* bug-fix for the case whne there is no simulation file associated to a recording file
--- Added comments ---  mogoss [Jun 15, 2012 9:58:48 AM CEST]
Change Package : 117828:1 http://mks-psad:7002/im/viewissue?selection=117828
Revision 1.17 2012/06/12 09:15:05CEST Mogos, Sorin (mogoss)
* update: added 'Recurse' port for scanning sub-directories while looking
for simulation output files
--- Added comments ---  mogoss [Jun 12, 2012 9:15:14 AM CEST]
Change Package : 117828:1 http://mks-psad:7002/im/viewissue?selection=117828
Revision 1.16 2012/04/24 11:59:32CEST Spruck, Jochen (spruckj)
Add the posibility to read in only export files with a defined post fix name
to the recfilename
--- Added comments ---  spruckj [Apr 24, 2012 11:59:40 AM CEST]
Change Package : 98074:3 http://mks-psad:7002/im/viewissue?selection=98074
Revision 1.15 2011/10/31 11:59:24CET Mogos, Sorin (mogoss)
* fix: imported inspect module
--- Added comments ---  mogoss [Oct 31, 2011 11:59:24 AM CET]
Change Package : 85403:1 http://mks-psad:7002/im/viewissue?selection=85403
Revision 1.14 2011/10/31 11:40:16CET Sorin Mogos (mogoss)
* change: changed stk library path
--- Added comments ---  mogoss [Oct 31, 2011 11:40:16 AM CET]
Change Package : 85403:1 http://mks-psad:7002/im/viewissue?selection=85403
Revision 1.13 2011/07/20 18:34:39CEST Castell Christoph (uidt6394) (uidt6394)
Added PreTerminate() function.
--- Added comments ---  uidt6394 [Jul 20, 2011 6:34:42 PM CEST]
Change Package : 54841:1 http://mks-psad:7002/im/viewissue?selection=54841
Revision 1.12 2011/02/08 15:54:13CET Sorin Mogos (mogoss)
* update: added support for multiple file extentions
--- Added comments ---  mogoss [Feb 8, 2011 3:54:13 PM CET]
Change Package : 58986:1 http://mks-psad:7002/im/viewissue?selection=58986
Revision 1.11 2011/01/25 12:40:11CET Ovidiu Raicu (RaicuO)
Updated to work with sections.
--- Added comments ---  RaicuO [Jan 25, 2011 12:40:11 PM CET]
Change Package : 37852:2 http://mks-psad:7002/im/viewissue?selection=37852
Revision 1.10 2010/10/03 11:46:13CEST Sorin Mogos (mogoss)
* removed component_name parameter from SetDataPort
--- Added comments ---  mogoss [Oct 3, 2010 11:46:13 AM CEST]
Change Package : 51595:1 http://mks-psad:7002/im/viewissue?selection=51595
Revision 1.9 2010/07/20 12:55:00CEST Sorin Mogos (mogoss)
* code optimisation
--- Added comments ---  mogoss [Jul 20, 2010 12:55:00 PM CEST]
Change Package : 47041:2 http://mks-psad:7002/im/viewissue?selection=47041
Revision 1.8 2010/06/28 14:46:12EEST Sorin Mogos (smogos)
* added configuration manager
--- Added comments ---  smogos [2010/06/28 11:46:12Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.7 2010/03/19 10:33:15EET Sorin Mogos (smogos)
* code customisation and bug-fixes
--- Added comments ---  smogos [2010/03/19 08:33:15Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.6 2010/03/04 09:16:28EET Gicu Benchea (gbenchea)
Add the bus constructor parameter
--- Added comments ---  gbenchea [2010/03/04 07:16:28Z]
Change Package : 31947:1 http://LISS014:6001/im/viewissue?selection=31947
Revision 1.5 2010/02/19 12:20:16EET Sorin Mogos (smogos)
* bug-fixes
--- Added comments ---  smogos [2010/02/19 10:20:17Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.4 2010/02/19 11:40:30EET Sorin Mogos (smogos)
* bug-fixes
--- Added comments ---  smogos [2010/02/19 09:40:30Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.3 2010/02/18 15:29:29EET Sorin Mogos (smogos)
* code optimisation and bug-fixes
--- Added comments ---  smogos [2010/02/18 13:29:30Z]
Change Package : 37850:1 http://LISS014:6001/im/viewissue?selection=37850
Revision 1.2 2009/11/18 13:09:44EET Sorin Mogos (smogos)
* some bug-fixes
--- Added comments ---  smogos [2009/11/18 11:09:44Z]
Change Package : 33973:1 http://LISS014:6001/im/viewissue?selection=33973
Revision 1.1 2009/10/30 14:18:40EET dkubera
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/ETK_EngineeringToolKit/
    04_Engineering/VALF_ValidationFrame/04_Engineering/31_PyLib/project.pj
"""
