r"""
framework/valf/__init__.py
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

Wiki Pages with links to other documents
     * http://connext.conti.de/wikis/home#!/wiki/ADAS%20Algo%20Validation/page/VALF%20Validation%20Framework


Demo example Code under
    * http://ims-adas:7001/si/viewproject?projectName=/nfs/projekte1/REPOSITORY/Tools/Validation%5fTools\
      /Lib%5fLibraries/STK%5fScriptingToolKit/05%5fSoftware/05%5fTesting/05%5fTest%5fEnvironment/valfdemo/project.pj


**To run a validation suite using Valf class follow this example:**

.. code-block:: python

    # Import valf module
    from stk.valf import valf

    # set output path for logging ect., logging level and directory of plugins (if not subdir of current HEADDIR):
    vsuite = valf.Valf(os.getenv('HPCTaskDataFolder'), 10)  # logging level DEBUG, default level: INFO

    # mandatory: set config file and version of sw under test
    vsuite.LoadConfig(r'demo\cfg\bpl_demo.cfg')
    vsuite.SetSwVersion('AL_STK_V02.00.06')

    # additional defines not already set in config files or to be overwritten:
    vsuite.SetBplFile(r'cfg\bpl.ini')
    vsuite.SetSimPath(r'\\Lifs010.cw01.contiwan.com\data\MFC310\SOD_Development')

    # start validation:
    vsuite.Run()


:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 10:14:08CEST $
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
Revision 1.2 2020/03/31 10:14:08CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:38:05CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/valf/project.pj
"""
