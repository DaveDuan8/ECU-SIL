"""
stk/obj/geo/rect.py
-------------------

 Rectangular Class supporting
    - Rotate
    - Shift
    - Reflection Point Calculation (for Radar objects)

:org:           Continental AG
:author:        Guenther Raedler

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:04:54CEST $
"""
# Import Python Modules -------------------------------------------------------
from math import sin, cos

# Import STK Modules ----------------------------------------------------------
from stk.util.helper import deprecated
from .point import split_pair_list

# Defines ---------------------------------------------------------------------

# Functions -------------------------------------------------------------------


# Functions --------------------------------------------------------------------
def point_inside_polygon(xpos, ypos, poly):
    """
    Check if a given point is inside a polygon.

    :param xpos: x-coordinate of point
    :type xpos: float
    :param ypos: y-coordinate of polygon
    :type ypos: float
    :param poly: given polygon array of points [x,y]-values
    :type poly: list[[float, float], ....]
    """

    size = len(poly)
    inside = False

    p1x, p1y = poly[0]
    for i in range(size + 1):
        p2x, p2y = poly[i % size]
        if ypos > min(p1y, p2y):
            if ypos <= max(p1y, p2y):
                if xpos <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (ypos - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or xpos <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def rotate(point, angle, xorigin=0, yorigin=0):
    """
    rotate a point in a x,y based coordiante system counter-clockwise
    around an given origin.

    :param point:
    :type point:
    :param angle:
    :type angle:
    :param origin:
    :type origin:
    """

    # precompute value
    sin_phi = sin(angle)
    cos_phi = cos(angle)

    xpos = (point[0] - xorigin) * cos_phi - \
           (point[1] - yorigin) * sin_phi + xorigin
    ypos = (point[0] - xorigin) * sin_phi + \
           (point[1] - yorigin) * cos_phi + yorigin

    return [xpos, ypos]


# Classes ----------------------------------------------------------------------
class Rect(object):
    """
    This class contains some basic functions for Rectangle objects.
    The Rectangle is in following format defined:

                 top (positive)
                  ^ y
                  |              1 _____________ 2
                  |               |             |
                  |               |             |
                  |               |             |
                  |               |             |
                  |               |_____________|
                  |              0              3
                  |
     left  <------+-------------------------------------------> right (positive)
     (negative)   |                                             x
                  |
               bottom (negative)
    """
    def __init__(self, left, top, right, bottom):

        self.__points = []
        self.__points.append([left, bottom])
        self.__points.append([left, top])
        self.__points.append([right, top])
        self.__points.append([right, bottom])

    @property
    def points(self):
        return self.__points

    def rotate(self, angle, xorigin=0, yorigin=0):
        """
        Rotates the internal rectangle around a additional origin.
        The rotation is counterclockwise when angle is > zero.

        :param angle: orientation angle in radians
        :type angle: float [radians]
        :param origin: Coordinate of rotation point
        :type origin: `Point`
        :return: rotated rect
        :rtype: list[Point]
        """
        result = []
        for point in self.__points:
            result.append(rotate(point, angle, xorigin, yorigin))

        self.__points = result

    def shift(self, xshift, yshift):
        """
        Shift the internal rect to a new position.

        :param xshift: value to shift box
        :type xshift: float
        :param yshift: amount to shift box
        :type yshift: float
        :return: List of shifted points
        :rtype: list of points
        """
        result = []

        for point in self.__points:
            result.append([point[0] + xshift, point[1] + yshift])

        self.__points = result

    def inside(self, xpos, ypos):
        """
        Is the point inside the rect ?

        :param xpos: x value of the point to be tested
        :type xpos:  float
        :param ypos: y value of the point to be tested
        :type ypos:  float
        :return   True if point in rectangle
        :rtype:   boolean

        assume a semidefinite horizontal ray (x increasing, y = const)
        out from the test point and count how many edges of the polygon
        it crosses. At each crossing, the ray switches between inside and
        outside. This is called the Jordan curve theorem. The point lies
        outside the polygon if the number of crossings is even. This functions
        counts only edges which are to the right of the test point (x_edge > x)
        """
        return point_inside_polygon(xpos, ypos, self.__points)


class Rectangle(object):
    '''
    classdocs
    '''
    def __init__(self, left, right, top, bottom):
        '''
        Constructor
        '''
        point_list = []
        point_list.append([-bottom, left])
        point_list.append([top, left])
        point_list.append([top, -right])
        point_list.append([-bottom, -right])
        point_list.append([-bottom, left])

        self.__point_list = point_list
        # print point_list

    @property
    def points(self):
        return self.__point_list

    def rotate(self, orientation):
        """ Rotates the box around the origin [0,0]
        @param point_list: List of Points
        @param orientation: orientation angle in radians
        @return: List of rotated points
        """
        # precompute trig functions
        sin_phi = sin(orientation)
        cos_phi = cos(orientation)

        # rotate points around origin [0,0]
        ret_point_list = []
        for point in self.__point_list:
            xpos = point[0] * cos_phi - point[1] * sin_phi
            ypos = point[0] * sin_phi + point[1] * cos_phi
            ret_point_list.append([xpos, ypos])

        self.__point_list = ret_point_list

    def shift(self, x_shift, y_shift):
        """ Rotates the box around the origin [0,0]
        @param x_shift: amount to shift box
        @param y_shift: amount to shift box
        @return: List of shifted points
        """

        # shift points
        ret_point_list = []
        for point in self.__point_list:
            ret_point_list.append([point[0] + x_shift, point[1] + y_shift])

        self.__point_list = ret_point_list

    def calc_reflection_point(self, orientation=None):
        """ Calculate the reflexion point of the Box

            1--------2
            |        |
            |        |
            |        |
            |        |
            0/4------3

        @param point_list: List ox Pointpairs describing the Box
        @return: The reflection point pair
        """
        # get number of points (should be 5)
        point_list = self.__point_list
        npoints = len(point_list)

        # find the nearest point
        x_vec, _ = split_pair_list(point_list)
        index = x_vec.index(min(x_vec))
        point = point_list[index]

        # find neighbouring left and right points connected by vertices to closest point
        if index == 0:
            point_left = point_list[npoints - 2]
        else:
            point_left = point_list[index - 1]

        if index == npoints - 1:
            point_right = point_list[1]
        else:
            point_right = point_list[index + 1]

        # assuming that we have a rectangular box:
        if (abs(point_left[0] - point[0]) < abs(point_left[1] - point[1])):
            # if orientation of left vertex < 45deg (i.e. deltaX < deltaY)
            # then reflection point is in the middle of this vertex
            xpos = (point[0] + point_left[0]) / 2
            ypos = (point[1] + point_left[1]) / 2
        else:
            # else orientation is the midlle of the other vertex
            xpos = (point[0] + point_right[0]) / 2
            ypos = (point[1] + point_right[1]) / 2

        return [xpos, ypos]

    def inside(self, xpos, ypos):
        """ Is the point in the given polygon (box) ?
        @param  point_list: list of points decribing the polygon (last point == first point)
        @param x: x value of the point to be tested
        @param y: y value of the point to be tested
        @return True if point in the polygon (box)

        assume a semidefinite horizontal ray (x increasing, y = const)
        out from the test point and count how many edges of the polygon
        it crosses. At each crossing, the ray switches between inside and outside.
        This is called the Jordan curve theorem. The point lies outside the polygon
        if the number of crossings is even. This functions counts only edges which
        are to the right of the test point (x_edge > x)
        """

        inside = False
        npoints = len(self.__point_list)

        j = 0
        for i in range(1, npoints):
            if (((self.__point_list[i][1] > ypos) != (self.__point_list[j][1] > ypos)) and
                (xpos < (self.__point_list[j][0] - self.__point_list[i][0]) * (ypos - self.__point_list[i][1]) /
                 (self.__point_list[j][1] - self.__point_list[i][1]) + self.__point_list[i][0])):
                inside = not inside
            j = i

        return inside

    @deprecated('rotate')
    def Rotate(self, orientation):  # pylint: disable=C0103
        """deprecated"""
        return self.rotate(orientation)

    @deprecated('shift')
    def Shift(self, x_shift, y_shift):  # pylint: disable=C0103
        """deprecated"""
        return self.shift(x_shift, y_shift)

    @deprecated('calc_reflection_point')
    def CalcReflectionsPoint(self, orientation=None):  # pylint: disable=C0103
        """deprecated"""
        return self.calc_reflection_point(orientation)

    @deprecated('inside')
    def PolygonContainsPoint(self, x, y):  # pylint: disable=C0103
        """deprecated"""
        return self.inside(x, y)

"""
CHANGE LOG:
-----------
$Log: rect.py  $
Revision 1.1 2015/04/23 19:04:54CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/obj/geo/project.pj
Revision 1.11 2015/02/06 16:46:28CET Ellero, Stefano (uidw8660) 
No deprecated functions/methods of package obj must be used inside all STK and its module tests.
--- Added comments ---  uidw8660 [Feb 6, 2015 4:46:29 PM CET]
Change Package : 301801:1 http://mks-psad:7002/im/viewissue?selection=301801
Revision 1.10 2014/04/29 10:26:34CEST Hecker, Robert (heckerr) 
updated to new guidelines.
--- Added comments ---  heckerr [Apr 29, 2014 10:26:34 AM CEST]
Change Package : 233703:1 http://mks-psad:7002/im/viewissue?selection=233703
Revision 1.9 2014/04/25 08:40:26CEST Hecker, Robert (heckerr)
Added additional rect class with new wanted functionality.
--- Added comments ---  heckerr [Apr 25, 2014 8:40:26 AM CEST]
Change Package : 224330:1 http://mks-psad:7002/im/viewissue?selection=224330
Revision 1.8 2014/03/26 15:05:09CET Hecker, Robert (heckerr)
Updates for python 3 support.
--- Added comments ---  heckerr [Mar 26, 2014 3:05:09 PM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.7 2013/12/03 17:33:06CET Sandor-EXT, Miklos (uidg3354)
pylint fix
--- Added comments ---  uidg3354 [Dec 3, 2013 5:33:06 PM CET]
Change Package : 208827:1 http://mks-psad:7002/im/viewissue?selection=208827
Revision 1.6 2013/05/16 07:31:03CEST Raedler, Guenther (uidt9430)
- moved method PolygonContainsPoint(self, x, y) from old vpc into stk
--- Added comments ---  uidt9430 [May 16, 2013 7:31:03 AM CEST]
Change Package : 175136:1 http://mks-psad:7002/im/viewissue?selection=175136
Revision 1.5 2013/03/28 09:33:19CET Mertens, Sven (uidv7805)
pylint: removing unused imports
--- Added comments ---  uidv7805 [Mar 28, 2013 9:33:20 AM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.4 2013/03/01 15:47:40CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Mar 1, 2013 3:47:40 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/28 08:12:29CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:29 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/27 16:20:01CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:20:02 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/11 10:50:01CET Raedler, Guenther (uidt9430)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/obj/geo/project.pj
"""
