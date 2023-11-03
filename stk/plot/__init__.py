"""
stk/plot/__init__.py
--------------------

Subpackage for plotting graphs with matplotlib.

This Subpackage provides a complete Interface to the Matplotlib from python.

For not directly supported functions, you can use the original commands from
matplotlib, and mix them with this API.

**Following Classes are available for the User-API:**

  - `Plot`

**To get more information about the usage of the plot API, you can also check following Links:**

    * This Document
    * http://matplotlib.org/api/pyplot_api.html


**To use the plot package from your code do following:**

  .. python::

    # Import stk.plot
    from stk import plot

    # Create a instance of the Plot class.
    plt = plot.Plot()

    plt.plot([1, 2, 3, 4], [1, 4, 9, 16], 'ro')
    plt.axis([0, 5, 0, 20])
    plt.savefig('plot_xydata.png')

    ...


:org:           Continental AG
:author:        Robert Hecker
:date:          08.07.2014

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:56CEST $
"""
# Import Python Modules -------------------------------------------------------

# Add PyLib Folder to System Paths --------------------------------------------

# Import STK Modules ----------------------------------------------------------

# Import Local Python Modules -------------------------------------------------
from .plot import Plot

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.1 2015/04/23 19:04:56CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/plot/project.pj
Revision 1.1 2014/07/14 12:00:23CEST Hecker, Robert (heckerr) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/plot/project.pj
"""
