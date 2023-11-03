"""
stk/rep/__init__.py
-------------------

**Report generation package to create *.pdf reports.**

.. packagetree::
   :style: UML

**User-API Interfaces**


`AlgoTestReport`
    class to build pdf reports with different templates/styles
    for performance, functional or regression tests


`base`
    package for developer defined reports providing only header and footer on page template

Pdf reports are created for a `stk.val.TestRun` stored in the Validation Result DB.
For testing purpose you can also use the interface class `ifc`
which provides the needed TestRun, TestCase and TestStep declarations.

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/11/17 11:53:50CET $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------

# Add PyLib Folder to System Paths ------------------------------------------------------------------------------------

# Import STK Modules --------------------------------------------------------------------------------------------------

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.2 2016/11/17 11:53:50CET Hospes, Gerd-Joachim (uidv8815) 
pylint fixes, remove deprecated methods
Revision 1.1 2015/04/23 19:05:05CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/rep/pdf/project.pj
Revision 1.5 2014/06/26 11:15:59CEST Hospes, Gerd-Joachim (uidv8815)
fine tuning of epydoc for AlgoTestReport and base
--- Added comments ---  uidv8815 [Jun 26, 2014 11:15:59 AM CEST]
Change Package : 243858:2 http://mks-psad:7002/im/viewissue?selection=243858
Revision 1.4 2014/06/05 16:24:19CEST Hospes, Gerd-Joachim (uidv8815)
final fixes after approval from Zhang Luo: cleanup and epydoc, pylint and pep8
--- Added comments ---  uidv8815 [Jun 5, 2014 4:24:19 PM CEST]
Change Package : 237743:1 http://mks-psad:7002/im/viewissue?selection=237743
Revision 1.3 2013/10/25 09:02:29CEST Hecker, Robert (heckerr)
Removed Pep8 Issues.
--- Added comments ---  heckerr [Oct 25, 2013 9:02:29 AM CEST]
Change Package : 202843:1 http://mks-psad:7002/im/viewissue?selection=202843
Revision 1.2 2013/10/21 08:41:43CEST Hecker, Robert (heckerr)
updated doxygen description.
--- Added comments ---  heckerr [Oct 21, 2013 8:41:43 AM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.1 2013/10/18 11:12:45CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/
STK_ScriptingToolKit/04_Engineering/stk/rep/pdf/project.pj
"""
