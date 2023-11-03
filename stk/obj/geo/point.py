"""
stk/obj/geo/point.py
-------------------

Functions to generate and split point pair lists

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:53CEST $
"""
# Import Python Modules -------------------------------------------------------

# Import STK Modules ----------------------------------------------------------
from stk.util.helper import deprecated

# Defines ---------------------------------------------------------------------

# Functions -------------------------------------------------------------------


def split_pair_list(pp_list):
    """ converts a point pair list into two arrays
    @param pp_list: Pointer Pair List
    @return : Two array representing column 0 and 1 in the point pairs
    """
    x_vec = [0] * len(pp_list)
    y_vec = [0] * len(pp_list)

    for pp in range(len(pp_list)):
        x_vec[pp] = pp_list[pp][0]
        y_vec[pp] = pp_list[pp][1]

    return x_vec, y_vec


def get_point_pair_list(x_vec, y_vec):
    """ converts two arrays into a point pair list
    @param x_vec:
    @param y_vec:
    @return: list of point pairs
    """
    if len(x_vec) != len(y_vec):
        # print "Length of x:{0} y:{1}".format(len(x_vec),len(y_vec))
        return None

    line_data = []
    for pp in range(len(x_vec)):
        line_data.append((x_vec[pp], y_vec[pp]))
    return line_data


def shift_timeline_of_point_pair_list(pp_list):
    """ Resets the time to start from zero.
    @param pp_list: Pointpair list describing a signal.
    @return point pair list with update timeline
    """
    new_pp_list = []
    if pp_list is not None:
        start_time = pp_list[0][0]
        for data in pp_list:
            a_point = (data[0] - start_time, data[1])
            new_pp_list.append(a_point)
    return new_pp_list


@deprecated('shift_timeline_of_point_pair_list')
def ShiftTimelineOfPointPairList(pp_list):  # pylint: disable=C0103
    """deprecated"""
    return shift_timeline_of_point_pair_list(pp_list)


@deprecated('get_point_pair_list')
def GetPointPairList(x_vec, y_vec):  # pylint: disable=C0103
    """deprecated"""
    return get_point_pair_list(x_vec, y_vec)


@deprecated('split_pair_list')
def SplitPairList(pp_list):  # pylint: disable=C0103
    """deprecated"""
    return split_pair_list(pp_list)

"""
CHANGE LOG:
-----------
$Log: point.py  $
Revision 1.1 2015/04/23 19:04:53CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/obj/geo/project.pj
Revision 1.9 2015/02/06 17:03:59CET Ellero, Stefano (uidw8660) 
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 6, 2015 5:04:00 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.8 2015/02/06 16:45:37CET Ellero, Stefano (uidw8660) 
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 6, 2015 4:45:37 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.7 2014/04/29 10:26:30CEST Hecker, Robert (heckerr) 
updated to new guidelines.
--- Added comments ---  heckerr [Apr 29, 2014 10:26:31 AM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.6 2013/12/03 17:33:06CET Sandor-EXT, Miklos (uidg3354)
pylint fix
--- Added comments ---  uidg3354 [Dec 3, 2013 5:33:07 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.5 2013/05/17 13:17:51CEST Raedler, Guenther (uidt9430)
- added ShiftTimelineOfPointPairList()
--- Added comments ---  uidt9430 [May 17, 2013 1:18:32 PM CEST]
Change Package : 183278:1 http://mks-psad:7002/im/viewissue?selection=183278
Revision 1.4 2013/04/03 08:02:14CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:14 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.3 2013/03/01 15:49:03CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguide.
--- Added comments ---  heckerr [Mar 1, 2013 3:49:03 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/28 08:12:15CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:16 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/11 10:50:01CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/obj/geo/project.pj
"""
