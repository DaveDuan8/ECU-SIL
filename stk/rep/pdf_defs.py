"""
stk/rep/pdf_defs.py
-------------------

This class provides definitions for reporting functionality in pdf.py

:deprecated:    Please use `stk.rep.pdf` modules instead
:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.1 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/04/23 19:05:00CEST $
"""
# Import Python Modules -----------------------------------------------------------------------------------------------
from os import getcwd, path as oPath
from base64 import b64decode

# ReportLab imports for PDF report generation -------------------------------------------------------------------------
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.lib.pagesizes import A4

# Definitions follow --------------------------------------------------------------------------------------------------
DOC_STYLE_SHEET = getSampleStyleSheet()
TITLE_STYLE = DOC_STYLE_SHEET["Title"]
HEADING_STYLE1 = DOC_STYLE_SHEET["Heading1"]
HEADING_STYLE2 = DOC_STYLE_SHEET["Heading2"]
HEADING_STYLE3 = DOC_STYLE_SHEET["Heading3"]
HEADING_STYLE4 = DOC_STYLE_SHEET["Heading4"]
NORMAL_STYLE = DOC_STYLE_SHEET["Normal"]
CODE_STYLE = DOC_STYLE_SHEET["Code"]

# Column Widths
COL_WIDTH_05 = 0.5 * inch
COL_WIDTH_08 = 0.8 * inch
COL_WIDTH_10 = 1.0 * inch
COL_WIDTH_13 = 1.3 * inch
COL_WIDTH_15 = 1.5 * inch
COL_WIDTH_20 = 2.0 * inch
COL_WIDTH_25 = 2.5 * inch
COL_WIDTH_30 = 3.0 * inch
COL_WIDTH_35 = 3.5 * inch
COL_WIDTH_40 = 4.0 * inch
COL_WIDTH_45 = 4.5 * inch
COL_WRAP_10 = 15
COL_WRAP_20 = 30
COL_WRAP_30 = 45
COL_WRAP_35 = 52
COL_WRAP_40 = 58
COL_WRAP_45 = 62
SPACER_01 = 0.1 * inch
SPACER_02 = 0.2 * inch
SPACER_04 = 0.4 * inch

# Page definitions
PAGE_LEFT_MARGIN = 1.8 * cm
PAGE_RIGHT_MARGIN = 1.8 * cm
PAGE_BOTTOM_MARGIN = 1.8 * cm
PAGE_WIDTH = A4[0]
PAGE_HEIGHT = A4[1]

FIRST_PAGE_LEFT_MARGIN = 3.15 * cm

GLOB_PAGE_HEIGHT = 25 * cm
GLOB_PAGE_WIDTH = 15 * cm
GLOB_PAGE_LEFT_MARGIN = 1.8 * cm
GLOB_PAGE_RIGHT_MARGIN = 1.8 * cm
GLOB_PAGE_TOP_MARGIN = 1.8 * cm
GLOB_PAGE_BOTTOM_MARGIN = 1.8 * cm

# standard string defs
STR_PASSED = '<font color=green>PASSED</font>'
STR_FAILED = '<font color=red>FAILED</font>'
STR_NA = '<font color=blue>N/A</font>'
STR_SUSPECT = '<font color=orange>TO BE VERIFIED</font>'

# Report types
REP_MANAGEMENT = 0
REP_DETAILED = 1
REP_DEVELOPMENT = 2

# Test statistics definitions
TEST_STAT_RESULT_TYPES = "Type"
TEST_STAT_RESULT_STATES = "States"
TEST_STAT_VALUE = "Value"
TEST_STAT_DISTANCE = "Distance"
TEST_STAT_VELOCITY = "Velocity"
TEST_STAT_EXPECTED = "Expected"
TEST_STAT_UNIT = "Unit"

TEST_STAT_RESULTS = "Results"
TEST_STAT_RESULTS_DIST = "Total distance"
TEST_STAT_RESULTS_TIME = "Total time"
TEST_STAT_RESULTS_MEANVELO = "Total mean velocity"
TEST_STAT_RESULTS_FRAMES = "Total no frames"
TEST_STAT_RESULTS_FILES = "Files Processed"
TEST_STAT_ROAD_TYPE = "Road Type"
TEST_STAT_LIGHT_COND = "Light Conditions"
TEST_STAT_WEATHER_COND = "Weather Conditions"
TEST_STAT_COUNTRIES = "Countries"
TEST_STAT_ROAD_COND = "Road Conditions"
TEST_STAT_SPEED = "Speed"
TEST_STAT_NO_PED = "No Pedestrian"
TEST_STAT_DB_TYPE_STREET = "street"
TEST_STAT_DB_TYPE_LIGHT = "light"
TEST_STAT_DB_TYPE_ROADTYPE = "roadtype"
TEST_STAT_DB_TYPE_WEATHER = "weather"
TEST_STAT_DB_TYPE_NOPED = "noped"
TEST_STAT_DB_TYPE_COUNTRY = "country"
TEST_STAT_DB_TYPE_NO_PED = "noped"

# The draft statement to be written on the title page
DRAFT_STATEMENT = "DRAFT"

# The return values
RET_OK = 1
RET_NOK = -1

# The confidential levels and statements to be written on the title page
CONF_STATEMENT = ["- Unclassified -", "- Confidential -", "- Strictly Confidential -"]
CONF_LEVEL_UNCLASSIFIED = 0
CONF_LEVEL_CONFIDENTIAL = 1
CONF_LEVEL_STRICTLY = 2

DEFAULT_OUTPUT_DIR_PATH = getcwd()

# Section types:
SECTION_TYPE_NONE = -1  # no section
SECTION_TYPE_SECTION = 0  # main section
SECTION_TYPE_SUBSECTION = 1  # sub section
SECTION_TYPE_SUBSUBSECTION = 2  # sub sub section
# last section type
SECTION_TYPE_LAST_TYPE = SECTION_TYPE_SUBSUBSECTION

# Table caption
TABLE_CAPTION = "Table"
FIGURE_CAPTION = "Fig."

# official colors found here:
# http://c-inside.conti.de/intranet/c-inside/Surf_Regions/en_US/Divisions/contitech/communications/praesentationen/
# download/CI_Charts_GB.pdf
PDF_CHART_COLORS = ["#ff9900", "#5f5f5f", "#969696", "#ffce6a", "#ffefbb", "#c0c0c0", "#57718d", "#a6b6c8",
                    "#e6e9f0", "#000000", "#a00000", "#ff0000", "#00d000", "#ffffff"]
# PDF_CHART_COLORS: [conti-yellow, conti-gray, conti-gray, yellow2, light-yellow, light-gray, conti-blue, blue,
#                    light-blue, black, conti-red, red, conti-green, white]

PDF_LINE_MARKERS = ['Cross', 'Circle', 'Square', 'Triangle', 'Diamond', 'StarSix', 'Pentagon', 'Hexagon',
                    'Heptagon', 'Octagon', 'StarFive', 'FilledSquare', 'FilledCircle', 'FilledDiamond', 'FilledCross',
                    'FilledTriangle', 'FilledStarSix', 'FilledPentagon', 'FilledHexagon', 'FilledHeptagon',
                    'FilledOctagon', 'FilledStarFive', 'Smiley', 'ArrowHead', 'FilledArrowHead']

# Helper list of upper-case ASCII letters
ASCII_UPPER_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                       'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']

CONTI_LOGO_SIZE_OLD = (591, 105)
with open(oPath.dirname(__file__) + r"\image\Continental.JPG", "rb") as imgFile:
    CONTI_CORP_LOGO_OLD = imgFile.read()

CONTI_LOGO_SIZE = (482, 90)
CONTI_CORP_LOGO = b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/4QBoRXhpZgAATU0AKgAAAAgABAEaAAUAAAABAAAAPgEbAAUAAAABAAAARgEoAAMAAAABAAIAAAExAAIAAAARA"
    "AAATgAAAAAAAABgAAAAAQAAAGAAAAABUGFpbnQuTkVUIHYzLjUuNQAA/9sAQwACAgICAgECAgICAwICAwMGBAMDAwMHBQUEBggHCQgIBwgICQoNCw"
    "kKDAoICAsPCwwNDg4PDgkLEBEQDhENDg4O/9sAQwECAwMDAwMHBAQHDgkICQ4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4ODg4"
    "ODg4ODg4ODg4O/8AAEQgAWgHiAwEiAAIRAQMRAf/EAB8AAAEFAQEBAQEBAAAAAAAAAAABAgMEBQYHCAkKC//EALUQAAIBAwMCBAMFBQQEAAABfQEC"
    "AwAEEQUSITFBBhNRYQcicRQygZGhCCNCscEVUtHwJDNicoIJChYXGBkaJSYnKCkqNDU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3e"
    "Hl6g4SFhoeIiYqSk5SVlpeYmZqio6Slpqeoqaqys7S1tre4ubrCw8TFxsfIycrS09TV1tfY2drh4uPk5ebn6Onq8fLz9PX29/j5+v/EAB8BAAMBAQ"
    "EBAQEBAQEAAAAAAAABAgMEBQYHCAkKC//EALURAAIBAgQEAwQHBQQEAAECdwABAgMRBAUhMQYSQVEHYXETIjKBCBRCkaGxwQkjM1LwFWJy0QoWJDT"
    "hJfEXGBkaJicoKSo1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoKDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5"
    "usLDxMXGx8jJytLT1NXW19jZ2uLj5OXm5+jp6vLz9PX29/j5+v/aAAwDAQACEQMRAD8A/fyiimu6RxNJIwRFGWZjgAeppNpK7AdWRrGv6J4f0s3uu"
    "ara6VajOJLqZUDEDOBnqfYc18v/ABI/aMFvNPo/gDbJKpKS6xKgZQQcfulOQ3+83HoD1r5L1XV9U1zWZdR1jULjU76T709zKXbHYZPQDsBwK/nziX"
    "xXyrKqksNl0PrFRbu9oJ+u8vlp5n6tk3A2Px8FWxcvZQfS15P5dPnr5H3tq/7RPw20yZo7a6vtbZThjY2ZxnJBwZCgPTORxyMZrmT+1F4S/tZUHh7"
    "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"
    "D/9k="
)


"""
CHANGE LOG:
-----------
$Log: pdf_defs.py  $
Revision 1.1 2015/04/23 19:05:00CEST Hospes, Gerd-Joachim (uidv8815) 
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/project.pj
Revision 1.12 2014/11/06 14:42:33CET Mertens, Sven (uidv7805) 
object update
--- Added comments ---  uidv7805 [Nov 6, 2014 2:42:33 PM CET]
Change Package : 278229:1 http://mks-psad:7002/im/viewissue?selection=278229
Revision 1.11 2014/05/12 09:47:59CEST Hecker, Robert (heckerr)
Added new JobSimFeature.
--- Added comments ---  heckerr [May 12, 2014 9:47:59 AM CEST]
Change Package : 236158:1 http://mks-psad:7002/im/viewissue?selection=236158
Revision 1.10 2014/03/19 13:53:39CET Hospes, Gerd-Joachim (uidv8815)
add heading level Heading4
--- Added comments ---  uidv8815 [Mar 19, 2014 1:53:40 PM CET]
Change Package : 224320:1 http://mks-psad:7002/im/viewissue?selection=224320
Revision 1.9 2013/09/16 14:41:49CEST Bratoi, Bogdan-Horia (uidu8192)
- pylint and pep8 cleanup
--- Added comments ---  uidu8192 [Sep 16, 2013 2:41:49 PM CEST]
Change Package : 190325:1 http://mks-psad:7002/im/viewissue?selection=190325
Revision 1.8 2013/09/13 13:00:53CEST Bratoi, Bogdan-Horia (uidu8192)
- small updates and extensions for the template implementation
--- Added comments ---  uidu8192 [Sep 13, 2013 1:00:53 PM CEST]
Change Package : 190325:1 http://mks-psad:7002/im/viewissue?selection=190325
Revision 1.7 2013/06/13 13:59:45CEST Mertens, Sven (uidv7805)
added new features for pie, bar, line and scatter drawings based on reportlab
--- Added comments ---  uidv7805 [Jun 13, 2013 1:59:45 PM CEST]
Change Package : 185933:2 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.6 2013/06/03 11:28:44CEST Mertens, Sven (uidv7805)
abs path working better than relative
--- Added comments ---  uidv7805 [Jun 3, 2013 11:28:44 AM CEST]
Change Package : 179495:9 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.5 2013/05/29 13:19:37CEST Mertens, Sven (uidv7805)
including old logo as well
--- Added comments ---  uidv7805 [May 29, 2013 1:19:37 PM CEST]
Change Package : 179495:6 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.4 2013/05/29 09:16:29CEST Mertens, Sven (uidv7805)
using better logo
Revision 1.3 2013/05/27 16:14:03CEST Mertens, Sven (uidv7805)
moving front page to right a bit using new definition
--- Added comments ---  uidv7805 [May 27, 2013 4:14:03 PM CEST]
Change Package : 179495:6 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.2 2013/05/03 13:36:51CEST Hecker, Robert (heckerr)
Added Log Keword at the end of file.
--- Added comments ---  heckerr [May 3, 2013 1:36:51 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
"""
