"""
stk/img/__init__.py
-------------------

Classes for Image Processing.

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:26CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

# Import Local Python Modules -----------------------------------------------------------------------------------------
from .plot import ValidationPlot
from .plot import DRAWING_W
from .plot import DEF_LINE_STYLES
from .plot import DEF_COLORS
from .plot import DEF_LINE_MARKERS

from .plot import PlotException
from .plot import BasePlot


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2015/04/23 19:04:26CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/img/project.pj
Revision 1.4 2014/03/26 15:13:53CET Hecker, Robert (heckerr) 
Added support for python 3.
--- Added comments ---  heckerr [Mar 26, 2014 3:13:53 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.3 2013/03/22 08:24:34CET Mertens, Sven (uidv7805) 
aligning bulk of files again for peping 8
--- Added comments ---  uidv7805 [Mar 22, 2013 8:24:35 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.2 2013/02/11 10:14:48CET Raedler, Guenther (uidt9430)
- added merged stkPlot and validation_plot
--- Added comments ---  uidt9430 [Feb 11, 2013 10:14:48 AM CET]
Change Package : 174385:1 http://mks-psad:7002/im/viewissue?selection=174385
Revision 1.1 2013/01/23 07:59:38CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/img/project.pj
"""
