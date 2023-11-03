"""
stk/obj/label_objects.py
-------------------

Python implementation of the Class ARS4D0_Object

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:46CEST $
"""

from stk.obj.ars_4xx_object import ARS4xxObject


class ARS4D0Object(ARS4xxObject):
    """
    ARS4D0Object
    """
    def __init__(self, obj, **kwargs):
        """Constructor taking the distx, disty and the vrelx as argument
        :param obj: Reference to object in the list of objects
        :param object_ext_if: Project
        (Observer) specific extension interface provider
        """
        ARS4xxObject.__init__()

    def __del__(self):
        """
          List of custom specific object signals.
          Loaded when object_ext_if is provided.
        """
        pass

    def __copy__(self):
        """
          Make a copy of the event object class
          The reference to the object is copied as
        well
        """
        pass
"""
$Log: ars_4d0_object.py  $
Revision 1.1 2015/04/23 19:04:46CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/obj/project.pj
Revision 1.3 2014/04/29 10:26:35CEST Hecker, Robert (heckerr) 
updated to new guidelines.
--- Added comments ---  heckerr [Apr 29, 2014 10:26:36 AM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.2 2013/12/16 14:18:44CET Sandor-EXT, Miklos (uidg3354)
file name change according to naming rules
--- Added comments ---  uidg3354 [Dec 16, 2013 2:18:45 PM CET]
Change Package : 208827:2 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.1 2013/12/16 13:16:17CET Sandor-EXT, Miklos (uidg3354)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development
/05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/obj/project.pj
Revision 1.1 2013/12/03 14:29:36CET Sandor-EXT, Miklos (uidg3354)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/obj/project.pj
"""
