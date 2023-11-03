"""
stk/db/hpc/__init__.py
----------------------

This Subpackage provides a complete Interface for HPC database.

**user-API**

    - `HpcErrorDB`

**See also relevant Classes:**

  - `db_common`

**To get more information about the usage of the Object database interface, you can also check following Links:**

ADAS Database API Documentation.
    * This Document

Enterprise Architecture design and document linked at
     * http://connext.conti.de/wikis/home?lang=en#!/wiki/ADAS%20Algo%20Validation/page/RQ%20Engineering%20for%20Tools

Wiki Server with FAQ's
     * https://connext.conti.de/wikis/home?lang=en#!/wiki/ADAS%20Algo%20Validation


**To use the hpc package from your code do following:**

  .. python::

    # Import db interface
    from stk.db.hpc import HpcErrorDB

    # Get a instance of HPC DB interface for job 0815 on server luss021.
    hpcdb = HpcErrorDB("luss021", 0815)

    # Get list of all events of 42 (might be long...):
    errlist = hpcdb.get_list_of_incidents(task_id=42)

    # Terminate HPC database
    hpcdb.close()

    ...

:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 12:26:34CEST $
"""


"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.2 2016/08/16 12:26:34CEST Hospes, Gerd-Joachim (uidv8815) 
update module and class docu
Revision 1.1 2015/04/23 19:04:06CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/db/hpc/project.pj
Revision 1.2 2015/01/20 16:54:32CET Mertens, Sven (uidv7805)
removing the only pep8 error
--- Added comments ---  uidv7805 [Jan 20, 2015 4:54:33 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.1 2015/01/20 08:13:45CET Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/db/hpc/project.pj
"""
