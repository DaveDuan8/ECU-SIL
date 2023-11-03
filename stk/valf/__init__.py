"""
stk/valf/__init__.py
--------------------

Subpackage for Running ADAS Algo Validation Framework **ValF**.

This Subpackage provides classes and functions to easily validate simulation output.

**Following Classes are available for the User-API:**

  - `Valf`
  - `CollectionReader`
  - (`BPLReader`, replaced by `CollectionReader`)
  - (`CATReader`, replaced by `CollectionReader`)
  - `SignalExtractor`
  - `DbLinker` simplified version of `DBConnector`
  - `ValfError`

  additional observers used in several projects:

  - `ResultSaver`
  - `TimeChecker`
  - `SODSACObserver`

**Following Defines (classes/constants) are available for the User-API:**
  - `BaseComponentInterface`
  - `signal_defs`

**Empty observer as template for new modules:**

  - `ExampleObserver`

**To get more information about the Validation support you can also check following Links:**

Valf API Documentation.
    * This Document


Valf Training (in MKS):
    * `Valf Training Overview  <http://ims-adas:7001/si/viewrevision?projectName=/nfs/projekte1/REPOSITORY/Tools\
       /Validation%5fTools/Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/01%5fSupporting%5fProcesses\
       /05%5fPresentation/project.pj&selection=Algo%5fValidation%5fOverview%5fTraining.pptx>`_
    * `Valf Training slides <http://ims-adas:7001/si/viewrevision?projectName=/nfs/projekte1/REPOSITORY/Tools\
       /Validation%5fTools/Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/01%5fSupporting%5fProcesses\
       /05%5fPresentation/project.pj&selection=Algo%5fValidation%5fTraining.pptx>`_


Wiki Pages with links to other documents
     * http://connext.conti.de/wikis/home#!/wiki/ADAS%20Algo%20Validation/page/VALF%20Validation%20Framework


Demo example Code under
    * http://ims-adas:7001/si/viewproject?projectName=/nfs/projekte1/REPOSITORY/Tools/Validation%5fTools\
      /Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/05%5fTesting/05%5fTest%5fEnvironment/valfdemo/project.pj


**To run a validation suite using Valf class follow this example:**

.. python::

    # Import valf module
    from stk.valf import valf

    # set output path for logging ect., logging level and directory of plugins (if not subdir of current HEADDIR):
    vsuite = valf.Valf(os.getenv('HPCTaskDataFolder'), 10)  # logging level DEBUG, default level: INFO

    # mandatory: set config file and version of sw under test
    vsuite.LoadConfig(r'demo\\cfg\\bpl_demo.cfg')
    vsuite.SetSwVersion('AL_STK_V02.00.06')

    # additional defines not already set in config files or to be overwritten:
    vsuite.SetBplFile(r'cfg\\bpl.ini')
    vsuite.SetSimPath(r'\\\\Lifs010.cw01.contiwan.com\\data\\MFC310\\SOD_Development')

    # start validation:
    vsuite.Run()


:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.4 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/12 17:36:42CEST $
"""
# - import STK modules ------------------------------------------------------------------------------------------------
from .base_component_ifc import ValidationException
from .base_component_ifc import BaseComponentInterface

from .process_manager import ProcessManager
from .data_manager import DataManager
from .plugin_manager import PluginManager


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.4 2016/08/12 17:36:42CEST Hospes, Gerd-Joachim (uidv8815) 
update docu for DbLinker
Revision 1.3 2016/04/12 15:05:00CEST Hospes, Gerd-Joachim (uidv8815)
fix docu during result saver implementation
Revision 1.2 2015/10/26 16:39:40CET Hospes, Gerd-Joachim (uidv8815)
update mks server to ims-adas
- Added comments -  uidv8815 [Oct 26, 2015 4:39:40 PM CET]
Change Package : 384737:1 http://mks-psad:7002/im/viewissue?selection=384737
Revision 1.1 2015/04/23 19:05:42CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/valf/project.pj
Revision 1.8 2015/03/20 09:15:58CET Mertens, Sven (uidv7805)
lines are too long
--- Added comments ---  uidv7805 [Mar 20, 2015 9:15:58 AM CET]
Change Package : 318794:1 http://mks-psad:7002/im/viewissue?selection=318794
Revision 1.7 2015/02/10 19:39:37CET Hospes, Gerd-Joachim (uidv8815)
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:39:39 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.6 2015/01/30 10:05:24CET Mertens, Sven (uidv7805)
removing non-working ConfigManager from imports
--- Added comments ---  uidv7805 [Jan 30, 2015 10:05:25 AM CET]
Change Package : 288765:1 http://mks-psad:7002/im/viewissue?selection=288765
Revision 1.5 2014/03/26 14:26:09CET Hecker, Robert (heckerr)
Adapted code to python 3.
--- Added comments ---  heckerr [Mar 26, 2014 2:26:09 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.4 2013/11/13 16:20:40CET Hospes, Gerd-Joachim (uidv8815)
add ActivateHpcAutoSplit method and usage of port HpcAutoSplit to Valf class,
updated tests and epydoc for all related files
--- Added comments ---  uidv8815 [Nov 13, 2013 4:20:40 PM CET]
Change Package : 206278:1 http://mks-psad:7002/im/viewissue?selection=206278
Revision 1.3 2013/03/21 17:27:57CET Mertens, Sven (uidv7805)
solving minor pylint error issues
--- Added comments ---  uidv7805 [Mar 21, 2013 5:27:57 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.2 2013/02/11 11:07:44CET Raedler, Guenther (uidt9430)
- added valf classes from etk/valf - renamed files
--- Added comments ---  uidt9430 [Feb 11, 2013 11:07:44 AM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/01/23 07:59:44CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/valf/project.pj
"""
