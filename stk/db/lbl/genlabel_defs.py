"""
stk/db/lbl/genlabel_defs.py
---------------------------

Definitions for the labels.


:org:           Continental AG
:author:        Nassim Ibrouchene

:version:       $Revision: 1.2 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2016/08/16 16:01:32CEST $
"""


class RoadType(object):  # pylint: disable-msg=W0232
    """
    Class Definition for Road Type label
    """
    # Road type label definitions as in the DB
    LABEL_TYPE_NAME = "roadtype"
    LABEL_VALUE_HIGHWAY = 3
    LABEL_VALUE_COUNTRY = 2
    LABEL_VALUE_CITY = 1
    LABEL_VALUE_UNDEFINED = 0
    LABEL_VALUE_UNLABELED = -1
    LABEL_NAME_HIGHWAY = "ROAD TYPE HIGHWAY"
    LABEL_NAME_COUNTRY = "ROAD TYPE COUNTRY"
    LABEL_NAME_CITY = "ROAD TYPE CITY"
    LABEL_NAME_UNDEFINED = "ROAD TYPE UNDEFINED"
    # Road type keywords
    HIGHWAY = "Highway"
    COUNTRY = "Country"
    CITY = "City"
    UNDEFINED = "Undefined"
    UNLABELED = "Unlabeled"
    RD_DICT = {}
    RD_DICT[HIGHWAY] = LABEL_VALUE_HIGHWAY
    RD_DICT[COUNTRY] = LABEL_VALUE_COUNTRY
    RD_DICT[CITY] = LABEL_VALUE_CITY
    RD_DICT[UNDEFINED] = LABEL_VALUE_UNDEFINED
    RD_DICT[UNLABELED] = LABEL_VALUE_UNLABELED
    TYPES = [HIGHWAY, COUNTRY, CITY, UNLABELED]
    # Road type attribute definition
    EVENT_ATTR_ROAD_TYPE = "roadtype"


"""
CHANGE LOG:
-----------
$Log: genlabel_defs.py  $
Revision 1.2 2016/08/16 16:01:32CEST Hospes, Gerd-Joachim (uidv8815) 
fix epydoc errors
Revision 1.1 2015/04/23 19:04:09CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/db/lbl/project.pj
Revision 1.5 2015/02/12 10:35:39CET Mertens, Sven (uidv7805)
newline
--- Added comments ---  uidv7805 [Feb 12, 2015 10:35:39 AM CET]
Change Package : 301806:1 http://mks-psad:7002/im/viewissue?selection=301806
Revision 1.4 2014/10/06 15:43:06CEST Ahmed, Zaheer (uidu7634)
epy doc improvement
--- Added comments ---  uidu7634 [Oct 6, 2014 3:43:07 PM CEST]
Change Package : 245347:1 http://mks-psad:7002/im/viewissue?selection=245347
Revision 1.3 2013/07/29 10:03:42CEST Ibrouchene, Nassim (uidt5589)
Added entry for unlabeled status for the road type.
--- Added comments ---  uidt5589 [Jul 29, 2013 10:03:43 AM CEST]
Change Package : 182606:3 http://mks-psad:7002/im/viewissue?selection=182606
Revision 1.2 2013/05/29 13:22:24CEST Mertens, Sven (uidv7805)
removing the only pylint error visible
--- Added comments ---  uidv7805 [May 29, 2013 1:22:24 PM CEST]
Change Package : 179495:7 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.1 2013/05/14 10:36:36CEST Ibrouchene-EXT, Nassim (uidt5589)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
stk/db/lbl/project.pj
"""
