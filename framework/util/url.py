"""
url
---

utility functions for url handling.

:org:           Continental AG
:author:        Robert Hecker

:version:       $Revision: 1.2 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/31 09:22:59CEST $
"""
# Import Python Modules -------------------------------------------------------

# Add PyLib Folder to System Paths --------------------------------------------

# Import framework Modules ----------------------------------------------------------

# Import Local Python Modules -------------------------------------------------

# local Functions -------------------------------------------------------------


def remove_fqn(input_url):
    """
    parses the input url and remove the Full Qualified URL Name if given.
    returns the modified url.

    :param input_url: UNC path to File
    :type input_url:  string
    :return:          Stripped UNC Path without FQN
    :rtype:           string
    """
    items = input_url.split('\\')

    items[2] = items[2].split('.')[0]

    items = items[1:]

    # Build new path
    result = ''
    for item in items:
        result += '\\'
        result += item

    return result

"""
CHANGE LOG:
-----------
$Log: url.py  $
Revision 1.2 2020/03/31 09:22:59CEST Leidenberger, Ralf (uidq7596) 
initial update
Revision 1.1 2020/03/25 21:33:26CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/util/project.pj
"""
