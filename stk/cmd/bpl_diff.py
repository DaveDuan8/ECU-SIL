"""
bpl_diff
--------

*call syntax*
C:\\> python bpl_diff -i <first.bpl> <second.bpl> -o <diff.bpl> [-s]

this program compares first and second input bpl's batch entries
against each other (without sections) and produces a difference
of both into an out file.
Option -s let's it compare with case sensitivity

:org:           Continental AG
:author:        uidv7805

:version:       $Revision: 1.4 $
:contact:       $Author: Ahmed, Zaheer (uidu7634) $ (last change)
:date:          $Date: 2017/08/31 10:28:10CEST $
"""
from sys import argv, executable
from os import path, system

# Defines -------------------------------------------------------------------------------------------------------------

SCRIPT = path.join(path.dirname(__file__), "bpl_operator.py")

# Functions -----------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    if len(argv) > 1:
        print("!!! usage of bpl_diff is deprecated, please use '%s xor %s'" % (SCRIPT, " ".join(argv[1])))
    else:
        print("!!! usage of bpl_diff is deprecated, please use '%s' instead" % SCRIPT)

    system("%s %s xor %s" % (executable.replace("_o.exe",".exe"), SCRIPT,
                             (" ".join(argv[1:]) if len(argv) > 1 else "")))

"""
CHANGE LOG:
-----------
$Log: bpl_diff.py  $
Revision 1.4 2017/08/31 10:28:10CEST Ahmed, Zaheer (uidu7634) 
bug fix to use python.exe
Revision 1.3 2017/08/29 15:36:18CEST Ahmed, Zaheer (uidu7634) 
adaption to choose correct python.exe in the running program context
Revision 1.2 2016/03/30 13:23:45CEST Mertens, Sven (uidv7805) 
pylint fix
Revision 1.1 2015/04/23 19:03:42CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.3 2015/01/15 16:51:59CET Hospes, Gerd-Joachim (uidv8815)
use bpl_operator instead
--- Added comments ---  uidv8815 [Jan 15, 2015 4:52:00 PM CET]
Change Package : 294951:1 http://mks-psad:7002/im/viewissue?selection=294951
Revision 1.2 2014/10/09 14:37:18CEST Mertens, Sven (uidv7805)
adding docu
--- Added comments ---  uidv7805 [Oct 9, 2014 2:37:19 PM CEST]
Change Package : 270435:1 http://mks-psad:7002/im/viewissue?selection=270435
Revision 1.1 2014/10/09 14:01:08CEST Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/cmd/project.pj
"""
