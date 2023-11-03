"""
stk/util/callstack.py
---------------------

Stand alone utility functions.


:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:28CEST $
"""
# Import Python Modules --------------------------------------------------------
import inspect


# Functions --------------------------------------------------------------------
def get_callstack(stack=None, frame=None):
    """
    return the whole callstack of all modules, which are called
    including this module.
    Note: This module will be the first entry in the list.

    :return: Full callstack with full pathnames to the modules.
    :rtype:  list[string]
    """
    if stack is None:
        stack = []

    if frame is None:
        frame = inspect.currentframe()

    newframe = frame.f_back.f_back

    if newframe is None:
        return stack

    code = newframe.f_code
    stack.append(code.co_filename)
    return get_callstack(stack, newframe)


def get_first_call_outside_stk(stack):
    """
    This method scans the callstack for the first module, which is ouside stk.
    Note: Works only, when stk is stored on the disk within a stk folder.

    :return: full path of first found module outide stk if not found, None.
    :rtype: string or None
    """
    for item in stack:
        # Check if item is outside stk
        if "stk" not in item:
            return item

    return None


"""
CHANGE LOG:
-----------
$Log: callstack.py  $
Revision 1.1 2015/04/23 19:05:28CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/util/project.pj
Revision 1.1 2014/09/17 11:21:33CEST Hecker, Robert (heckerr) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/util/project.pj
"""
