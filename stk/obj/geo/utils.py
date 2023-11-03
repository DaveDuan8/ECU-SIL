"""
stk/obj/utils.py
-------------------

Geometric utility functions

:org:           Continental AG
:author:        Miklos Sandor

:version:       $Revision: 1.2 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2015/12/07 11:07:51CET $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
# import matplotlib.pyplot as plt
# from matplotlib.path import Path
# import matplotlib.patches as patches
from math import sin, cos, pi, hypot, acos
# import numpy as np


# - utility functions -------------------------------------------------------------------------------------------------
def calc_angle(p1, p2):
    """
    calculates the angle between two lines: (0,0)-p1 and (0,0)-p2
    with Law of cosines, vector formulation

           /p1
          /  ----->angle
   (0,0) /____p2

    :param: p1: point1 (x1,y1)
    :param: p2: point1 (x2,y2)
    :return angle: angle in radian: arc cosine in the range [0 ; pi]
    """
    x1, y1 = p1
    x2, y2 = p2
    inner_product = x1 * x2 + y1 * y2
    len1 = hypot(x1, y1)
    len2 = hypot(x2, y2)
    return acos(inner_product / (len1 * len2))


def rotate_point(point, angle):
    """
    rotates point (x,y) counter-clockwise around (0,0)

    :param point: 2D point as tuple (x,y)
    :param angle: angle in radian
    :return point: point (x_rot, y_rot)
    """
    x = point[0] * cos(angle) - point[1] * sin(angle)
    y = point[0] * sin(angle) + point[1] * cos(angle)
    return x, y


def move_point(p, p_mov):
    """
    moves point p with p_mov
    """
    return p[0] + p_mov[0], p[1] + p_mov[1]


def adma_rectangle(width, length):
    """
    ADMA rear middle reference point
    y
    ^
    |
    1 ______2
    |       |
    * refl--|----> x
    |       |
    0/4-----3

    :param width: width
    :param length: length
    :param polygon_point_list: polygon point list as [(x,y),...]
    """
    rect = [
        (0.0, -width / 2),  # left, bottom
        (0.0, width / 2),  # left, top
        (length, width / 2),  # right, top
        (length, -width / 2),  # right, bottom
        (0.0, -width / 2),  # left, bottom
    ]
    return rect


def calc_reflection_point(point_list):  # , is_adma=True):
    """ Calculate the reflexion point of a polygon, e.g. rectangle

        1--------------2
        |              |
        |              |
        0/4------------3

    :param point_list: List ox point tuples
    #:param is_adma: in case of adma the edge p0-p1 (0/4 and 1) is the rear
    :return: reflection point tuple
    """
    # get number of points (should be 5)
    # point_list = self.__point_list
    len_points = len(point_list)

    # find the closest point
    dist_vec = [hypot(p[0], p[1]) for p in point_list]
    # dist_vec = [p[0] for p in point_list]
    closest_index = dist_vec.index(min(dist_vec))
    closest_point = point_list[closest_index]

    next_point_index = (closest_index + 1) % (len_points - 1)
    prev_point_index = (closest_index - 1) % (len_points - 1)

    # find neighbor vertices of closest point
    point_next = point_list[next_point_index]
    point_prev = point_list[prev_point_index]

    # first approach
    # vertex with orientation < 45 deg (i.e. deltaX < deltaY) wins
    # reflection point is in the middle of the winner vertex
    # if (abs(point_next[0] - point[0]) < abs(point_next[1] - closest_point[1])):
    #    xpos = (closest_point[0] + point_next[0]) / 2
    #    ypos = (closest_point[1] + point_next[1]) / 2
    # else:
    #    xpos = (closest_point[0] + point_prev[0]) / 2
    #    ypos = (closest_point[1] + point_prev[1]) / 2

    # second approach
    # vertex with the greater angle to the closest point vector wins
    # reflection point is in the middle of the winner vertex
    # TODO comment in if necessary
    # pref_next = 0.0
    # pref_prev = 0.0

    # TODO comment in if necessary
    # if is_adma:
    #     PREFERENCE_ANGLE = pi / 45.0
    #     if next_point_index == 1:
    #         pref_next = PREFERENCE_ANGLE
    #     elif prev_point_index in [0, 4]:
    #         pref_prev = PREFERENCE_ANGLE
    #     else:
    #         pass

    next_angle = calc_angle(closest_point, point_next)
    prev_angle = calc_angle(closest_point, point_prev)
    # print "point_next: " + str(point_next) + " next_angle: " + str(np.degrees(next_angle))
    # print "next_point_index: " + str(next_point_index) + " pref_next: " + str(np.degrees(pref_next))
    # print "point_prev: " + str(point_prev) + "prev_angle: " + str(np.degrees(prev_angle))
    # print "prev_point_index: " + str(prev_point_index) + " pref_prev: " + str(np.degrees(pref_prev))
    # TODO comment in if necessary
    # next_angle += pref_next
    # prev_angle += pref_prev
    if next_angle > prev_angle:
        xpos = (closest_point[0] + point_next[0]) / 2
        ypos = (closest_point[1] + point_next[1]) / 2
    else:
        xpos = (closest_point[0] + point_prev[0]) / 2
        ypos = (closest_point[1] + point_prev[1]) / 2

    return xpos, ypos


def adjust_distance_adma(distx, disty, length, width, orient):
    """
    :param distx: distx
    :param disty: disty
    :param length: length
    :param width: width
    :param orient: angle in radian
    :return point: reflection point (x_refl, y_refl)
    """
    rect = adma_rectangle(width, length)
    move_to_point = (distx, disty)
    trans_rect = [move_point(rotate_point(rp, orient), move_to_point) for rp in rect]
    refl = calc_reflection_point(trans_rect)
    return refl

# ----------------------------- NOT USED YET START -----------------------------------

# def contains_point(polygon_point_list, point):
#     """
#     :param polygon_point_list: polygon point list as [(x,y),...]
#     """
#     return Path(polygon_point_list).contains_point(point)
#
# def intersection(p11, p12, p21, p22):
#     """
#     gives the intersection point of two line segments
#
#
#     :param: p11: point 1 of line segment 1
#     :type: p11: (x1,y1) float
#     :param: p12: point 2 of line segment 1
#     :type: p12: (x2,y2) float
#     :param: p22: point 2 of line segment 2
#     :type: p22: (x3,y3) float
#     :param: p22: point 2 of line segment 2
#     :type: p22: (x4,y4) float
#     :return: (x,y) intersection of two segments or None
#     """
#     def line(p1, p2):
#         """
#         creates standard equation coefficients for a line from two points p1, p2:
#         Ax + By = C
#
#         :param: p1: point 1 of line segment 1
#         :type: p1: (x,y) float
#         :param: p2: point 2 of line segment 1
#         :type: p2: (x,y) float
#         """
#         x1 = p1[0]
#         y1 = p1[1]
#         x2 = p2[0]
#         y2 = p2[1]
#         a = y2 - y1
#         b = x1 - x2
#         c = a * x1 + b * y1
#         return a, b, c
#     def is_in_segment(x, y, p1, p2):
#         x1 = p1[0]
#         y1 = p1[1]
#         x2 = p2[0]
#         y2 = p2[1]
#         if min(x1, x2) <= x and x <= max(x1, x2) and min(y1, y2) <= y and y <= max(y1, y2):
#             return True
#         else:
#             return False
#
#     a1, b1, c1 = line(p11, p12)
#     a2, b2, c2 = line(p21, p22)
#     # Solve the equations:
#     # A1x + B1y = C1
#     # A2x + B2y = C2
#     # Multiply the top equation by B2, and the bottom equation by B1:
#     # A1B2x + B1B2y = B2C1
#     # A2B1x + B1B2y = B1C2
#     # Subtract the bottom equation from the top equation:
#     # A1B2x - A2B1x = B2C1 - B1C2
#     # Divide both sides by A1B2 - A2B1, and you get the equation for x as below.
#     det = a1 * b2 - a2 * b1
#     if det == 0:
#         # Lines are parallel
#         return None
#     else:
#         # there is an intersection x, y
#         x = (b2 * c1 - b1 * c2) / det
#         y = (a1 * c2 - a2 * c1) / det
#         # check if x, y is in the first and second line segment
#         if is_in_segment(x, y, p11, p12) and is_in_segment(x, y, p21, p22):
#             return (x, y)
#         else:
#             return None
#
# def intersections_of_polygon(polygon_point_list, line_points):
#     """
#     calculates the intersection between a line and the edges of a polygon
#
#
#     :param polygon_point_list: polygon point list as [(x,y),...]
#     :param line_points: segment [(x1,y1), (x2,y2)]
#     :return intersecs: list of point pairs [(x,y),...]
#     """
#     intersecs = []
#     len_poly = len(polygon_point_list)
#     # print "beam: " + str(line_points[0]) + ',' + str(line_points[1])
#     for vertex_count in range(len_poly - 1):
#         intersec = intersection(line_points[0], line_points[1], polygon_point_list[vertex_count],
#                                 polygon_point_list[vertex_count + 1])
#         if intersec is not None:
#             intersecs.append(intersec)
#         # if intersec is None:
#         #    res = "NOT OK"
#         # else:
#         #    res = "OK"
#         # print ("beam [" + str(vertex_count) + "]: " + str(polygon_point_list[vertex_count]) + ',' +
#         # str(polygon_point_list[vertex_count + 1]) + ' is ' + res
#         vertex_count += 1
#     return intersecs
#
# def plot_path(rect, line, point, name):
#     """
#     debug function to draw a rectangle a line and a point
#
#
#     :param rect: rectangle point list as [(x,y),...]
#     :param line: line point list as [(x,y),...]
#     :param point: point (x,y)
#     """
#     SAVE_PATH = r'd:/tmp/'
#     fig = plt.figure()
#     ax = fig.add_subplot(111)
#     rect_path = Path(rect)
#     line_path = Path(line)
#     ax.add_patch(patches.PathPatch(rect_path, facecolor='green', edgecolor='black', alpha=0.5, lw=1))
#     ax.add_patch(patches.PathPatch(line_path, facecolor='yellow', edgecolor='orange', alpha=0.5, lw=1))
#     ax.add_patch(patches.Circle((point[0], point[1]), radius=0.07, color='red'))
#     ax.set_xlim(-1, 19)
#     ax.set_ylim(-10, 10)
#     plt.savefig(SAVE_PATH + name + '.jpg', dpi=100)
#     # plt.show()

#  ----------------------------- NOT USED YET END -----------------------------------


"""
$Log: utils.py  $
Revision 1.2 2015/12/07 11:07:51CET Mertens, Sven (uidv7805) 
fix for some pep8 errors
Revision 1.1 2015/04/23 19:04:54CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/
    04_Engineering/01_Source_Code/stk/obj/geo/project.pj
Revision 1.1 2014/09/26 13:01:42CEST Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/04_Engineering/
    stk/obj/geo/project.pj
"""
