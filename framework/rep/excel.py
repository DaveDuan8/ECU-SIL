"""
stk/rep/excel
-------------

Module to Create Excel Based Reports.

:org:           Continental AG
:author:        Leidenberger, Ralf

:version:       $Revision: 1.1 $
:contact:       $Author: Leidenberger, Ralf (uidq7596) $ (last change)
:date:          $Date: 2020/03/25 21:22:09CET $
"""
# - imports Python modules --------------------------------------------------------------------------------------------
from win32com.client import DispatchEx
from win32gui import PostMessage
from win32con import WM_QUIT, PROCESS_TERMINATE
from win32process import GetWindowThreadProcessId
from win32api import OpenProcess, TerminateProcess, CloseHandle
from time import sleep
import six

# - import STK modules ------------------------------------------------------------------------------------------------

# ===================================================================================
# Constant declarations
# ===================================================================================
COLOR_MAP = {'Black': 1,
             'White': 2,
             'Red': 3,
             'Bright Green': 4,
             'Blue': 5, 'Yellow': 6,
             'Pink': 7,
             'Turqoise': 8,
             'Dark Red': 9,
             'Green': 10,
             'Dark Blue': 11,
             'Dark Yellow': 12,
             'Violet': 13,
             'Teal': 14,
             'Gray-25%': 15,
             'Gray-50%': 16,
             'Sky Blue': 33,
             'Light Turqoise': 34,
             'Light Green': 35,
             'Light Yellow': 36,
             'Pale Blue': 37,
             'Rose': 38,
             'Lavendar': 39,
             'Tan': 40,
             'Light Blue': 41,
             'Aqua': 42,
             'Lime': 43,
             'Gold': 44,
             'Light Orange': 45,
             'Orange': 46,
             'Blue-Gray': 47,
             'Gray-40%': 48,
             'Dark Teal': 49,
             'Sea Green': 50,
             'Dark Green': 51,
             'Olive Green': 52,
             'Brown': 53,
             'Plum': 54,
             'Indigo': 55,
             'Gray-80%': 56}
# The codes for the specified alignments in excel
VERTICAL_ALIGNMENT_TOP = -4160
VERTICAL_ALIGNMENT_CENTER = -4108
VERTICAL_ALIGNMENT_BOTOM = -4107

HORIZONTAL_ALIGNMENT_LEFT = -4131
HORIZONTAL_ALIGNMENT_CENTER = -4108
HORIZONTAL_ALIGNMENT_RIGHT = -4152

# The codes for the borders in excel:
# 7 - the left border of the cell
# 8 - the top border of the cell
# 9 - the bottom border of the cell
# 10 - the right border of the cell
# 11 - the inside vertical border of the cell
# 12 - the inside horizontal border of the cell
BORDERS_MAP = [7, 8, 9, 10, 11, 12]
# the excel code for the continuous type of border
# this constant can take values in [1,13] interval
CONTINUOUS_BORDER = 1

XL_CALCULATION_AUTOMATIC = -4105
XL_CALCULATION_MANUAL = -4135
XL_CALCULATION_SEMIAUTOMATIC = 2


############################################################################
# # Class for Excel File Read/Write access
#
#  Class which hase Base Methods for Reading and Writing Excel Files
############################################################################
class Excel(object):
    """
    **main class for MS Excel I/O**

    - You can use this class to read and write XLS files.

    **example usage:**

    .. code-block:: python

        # import excel:
        from stk.rep.excel import Excel

        # create instance and open an excel file:
        myXls = Excel(myExcelFile, myExcelWorkbook)
        # write some data:
        myXls.set_cell_value(5, 6, "1st value as string")
        myXls.set_cell_value(6, 6, 4711)
        # ok, cleanup:
        myXls.save_workbook()
        myXls.close()

        # now, let's read out these values:
        with Excel(myExcelFile) as myXls:
            # print the values:
            print("1: %s" % myXls.get_cell_value(5, 6))
            print("2: %d" % myXls.get_cell_value(6, 6))
        # on close, Excel automagically saves the workbook and closes gracefully

    """
    NUMBER_FORMAT_TEXT = "@"
    NUMBER_FORMAT_NUMBER = "0.00"
    NUMBER_FORMAT_DATE = "m/d/yyyy"
    NUMBER_FORMAT_TIME = "[$-F400]h:mm:ss AM/PM"
    NUMBER_FORMAT_PERCENTAGE = "0.00%"
    NUMBER_FORMAT_GENERAL = "General"

    FONT_NAME_ARIAL = "Arial"
    FONT_NAME_TIMES_NEW_ROMAN = "Times New Roman"
    FONT_NAME_COMIC = "Comic Sans MS"
    FONT_NAME_LUCIDA_CONSOLE = "Lucida Console"

    FONT_COLOR_RED = "Red"
    FONT_COLOR_YELLOW = "Yellow"
    FONT_COLOR_BLUE = "Blue"
    FONT_COLOR_GREEN = "Green"
    FONT_COLOR_GREY = "Gray-25%"
    FONT_COLOR_VIOLET = "Violet"

    ALIGNMENT_HORIZAONTAL_LEFT = "Left"
    ALIGNMENT_HORIZAONTAL_CENTER = "Center"
    ALIGNMENT_HORIZAONTAL_RIGHT = "Right"

    ALIGNMENT_VERTICAL_TOP = "Top"
    ALIGNMENT_VERTICAL_CENTER = "Center"
    ALIGNMENT_VERTICAL_BOTOM = "Botom"

    BORDER_DASHED = 1
    BORDER_THIN = 2
    BORDER_THICK1 = 3
    BORDER_THICK2 = 4

    CHART_TYPE_LINE_MARKERS = 65
    CHART_TYPE_COLUMNCLUSTERED = 51
    CHART_TYPE_BARCLUSTERED = 57
    CHART_TYPE_PIE = 5
    CHART_TYPE_XYSCATTER = -4169
    CHART_TYPE_AREA = 1
    CHART_TYPE_DOUGHNUT = -4120
    CHART_TYPE_SURFACE = 83

    CHART_PLOT_BY_COLUMNS = 2
    CHART_PLOT_BY_ROWS = 1

    CHART_LOCATION_OBJECT_CUR_SHEET = 2
    CHART_LOCATION_NEW_SHEET = 1

    def __init__(self, workfile=None, worksheet=None):
        """start connection with MS Excel

        :param workfile: excel file name
        :param worksheet: sheet name to work with right away
        """
        self.__workbook = None
        self.__worksheet = None
        self.__app = DispatchEx("Excel.Application")
        self.__app.DisplayAlerts = False

        self._close_called = False

        if workfile is not None:
            try:
                self.open_workbook(workfile, worksheet)
                self._workfile = None
            except IOError:  # pylint: disable=W0702
                self.__workbook = self.__app.Workbooks.Add()
                self._workfile = workfile
        self.xlchart = None

    def __del__(self):
        """in case someone forgot to close our Excel instance
        """
        self.close()

    def close(self):
        """
        close excel application,
        WM_CLOSE won't work with embedded startup option
        """
        if self._close_called:
            return

        self._close_called = True

        self.close_workbook()

        hdl = self.__app.Hwnd
        proc = proc2 = GetWindowThreadProcessId(hdl)[1]
        PostMessage(hdl, WM_QUIT, 0, 0)
        # Allow some time for app to close
        for i in range(15):
            _, proc2 = GetWindowThreadProcessId(hdl)
            if proc2 != proc:
                break
            sleep(float(i) / 3)
        # If the application didn't close within 5 secs, force it!
        if proc == proc2:
            # noinspection PyBroadException
            try:
                hdl = OpenProcess(PROCESS_TERMINATE, 0, proc)
                if hdl:
                    TerminateProcess(hdl, 0)
                    CloseHandle(hdl)
            except:  # noinspection PyBroadException
                pass

        # delete all references in right order
        del self.__worksheet
        del self.__workbook
        del self.__app

    def __enter__(self):
        """support for with statement
        """
        return self

    def __exit__(self, *_):
        """exit with statement
        """
        try:
            self.save_workbook(self._workfile)
        except IOError:  # pylint: disable=W0702
            pass
        self.close()

    # Workbook Functions ----------------------------------------------------------
    def get_data(self, row_from, col_from, worksheet_name=None, row_to=None,  # pylint: disable=R0913
                 col_to=None, all_data=False):
        """
        Get data

        :param worksheet_name:  name of worksheet, default(Current Sheet)
        :param row_from:        Upper row   of a range or a single cell
        :param col_from:        Left column of a range or a single cell
        :param row_to:          Bottom row of range , optional (default)
                                for 1 cell
        :param col_to:          Right Column of range, optional (default)
                                for 1 cell
        :param all_data:        if True selection of all data in sheet

        :return:                Tupel of row-tupels
                                (('R1C1','R1C2',..),('R2C1','R2C2',..),..)

        :author:                kuberad
        """
        # check worksheet
        if worksheet_name is None:
            # use current
            pass
        else:
            try:
                self.__workbook.Worksheets(worksheet_name)
            except:  # pylint:disable=E0611
                raise Exception('Error: worksheet does not exist : %s !!' % str(worksheet_name))
        self.__worksheet = self.__workbook.Worksheets(worksheet_name)

        # adaption for single rows/cols
        if row_to is None:
            row_to = row_from
        if col_to is None:
            col_to = col_from

        if all_data:
            row_from, col_from = 1, 1
            row_to, col_to = self.get_last_cell()

        return self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                      self.__worksheet.Cells(row_to, col_to)).Value

    def set_format(self, row_from, col_from, worksheet_name=None, row_to=None,  # pylint: disable=R0912,R0913,R0914
                   col_to=None, regular=False, italic=False, bold=False,
                   underline=False, font_name=None, font_color=None,
                   cell_color=None, font_size=None, orientation=None,
                   h_align=None, v_align=None, category=None, col_width=None,
                   wrap_text=False, auto_filter=False):
        """
        Set format of a cell or a range. ROWs are given as numbers 1,2,...

        Columns can be either numbers or chars "A","B",...

        :param worksheet_name:  name of worksheet, default(Current Sheet)
        :param row_from:        Upper row   of a range or a single cell
        :param col_from:        Left column of a range or a single cell
        :param row_to:          Bottom row of range , False(default) for 1 cell
        :param col_to:          Right Column of range, False(default) for 1 cell
        :param regular:         True, False(default)
        :param italic:          True, False(default)
        :param bold:            True, False(default)
        :param underline:       True, False(default)
        :param font_name:       "Arial", "Times New Roman", ...
        :param font_color:      "Black", "Red", ... s.COLOR_MAP, "Standard"(default)
        :param cell_color:      see font_color
        :param font_size:       8,9,...
        :param orientation:     orientation in degree,   0(default)
        :param h_align:         "Left","Center","Right"
        :param v_align:         "Bottom","Center","Top"
        :param category:        "@" Text Format, "0.00" Number Format
        :param col_width:       column width or "AUTO_FIT"
        :param wrap_text:       True, False(default)
        :param auto_filter:     AutoFilter, False(default)  only use for 1 row!

        :author:                kuberad
        """
        if worksheet_name is None:
            # use current
            pass
        else:
            try:
                self.__workbook.Worksheets(worksheet_name)
            except:  # pylint:disable=E0611
                raise Exception('Error: worksheet does not exist : %s !!' % str(worksheet_name))

        d_alignment_vert = {"Bottom": VERTICAL_ALIGNMENT_BOTOM,
                            "Center": VERTICAL_ALIGNMENT_CENTER,
                            "Top": VERTICAL_ALIGNMENT_TOP}

        d_alignment_hor = {"Left": HORIZONTAL_ALIGNMENT_LEFT,
                           "Center": HORIZONTAL_ALIGNMENT_CENTER,
                           "Right": HORIZONTAL_ALIGNMENT_RIGHT}

        # check for valid input
        if font_color is not None and font_color not in COLOR_MAP:
            print(" %s is not in COLOR_MAP!" % str(font_color))

        if cell_color is not None and cell_color not in COLOR_MAP:
            print(" %s is not in COLOR_MAP!" % str(cell_color))

        if v_align is not None and v_align not in list(d_alignment_vert.keys()):
            print(" %s is invalid input for v_align!" % str(v_align))

        if h_align is not None and h_align not in list(d_alignment_hor.keys()):
            print(" %s is invalid input for h_align!" % str(h_align))

        # adaption for single rows/cols
        if row_to is None:
            row_to = row_from
        if col_to is None:
            col_to = col_from
        # formatting ...
        if v_align in list(d_alignment_vert.keys()):
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).VerticalAlignment = \
                d_alignment_vert[v_align]
        if h_align in list(d_alignment_hor.keys()):
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).HorizontalAlignment = \
                d_alignment_hor[h_align]
        if regular is True:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).Font.FontStyle = "Regular"
        if bold is True:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).Font.Bold = True
        if italic is True:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).Font.Italic = True
        if underline is True:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).Font.Underline = True
        if font_name is not None:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).Font.Name = font_name
        if font_color in COLOR_MAP:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).Font.ColorIndex = COLOR_MAP[font_color]
        if cell_color in COLOR_MAP:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).Interior.ColorIndex = COLOR_MAP[cell_color]
        if category is not None:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).NumberFormat = category
        if font_size is not None:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).Font.Size = font_size
        if orientation is not None:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).Orientation = orientation
        if col_width is not None and col_width == "AUTO_FIT":
            self.__worksheet.Range(self.__worksheet.Columns(col_from),
                                   self.__worksheet.Columns(col_to)).EntireColumn.AutoFit()

        if col_width is not None and (type(col_width) in [int, float] or isinstance(col_width, six.integer_types)):
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).ColumnWidth = col_width
        if wrap_text is True:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).WrapText = True
        if auto_filter is True:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).AutoFilter()

    def set_data(self, data, row_from, col_from, ws_name=None,  # pylint: disable=R0912,R0913,R0914
                 empty_value="'-", f_regular=False, f_italic=False,
                 f_bold=False, f_underline=False, f_font_name=None,
                 f_font_color=None, f_cell_color=None, f_font_size=None,
                 f_orientation=None, f_h_align=None, f_v_align=None,
                 f_category=None, f_col_width=None, f_wrap_text=False,
                 f_auto_filter=False):
        """
        Flexible Set Data Function.

        Sets data to 1 cell or a range regarding size of data.
        Data is either a single value or string or a list of lists of rows.

        Sets also format if specified.

        ROWs are given as numbers 1,2,... Columns can be either numbers or chars "A","B",...

        :param ws_name:         name of worksheet, default(Current Sheet)
        :param data:            data to write, list of rows ``[[r1col1,r1col2,...],[r2col1,r2col2,...]]``
        :param empty_value:     fills inconsistent matrices with this value, "-"(default)
        :param row_from:        Upper row   of a range or a single cell
        :param col_from:        Left column of a range or a single cell
        :param f_regular:       True, False(default)
        :param f_italic:        True, False(default)
        :param f_bold:          True, False(default)
        :param f_underline:     True, False(default)
        :param f_font_name:     "Arial", "Times New Roman", ...
        :param f_font_color:    "Black", "Red", ... s.COLOR_MAP, "Standard"(default)
        :param f_cell_color:    see font_color
        :param f_font_size:     8,9,...
        :param f_orientation:   orientation in degree,   0(default)
        :param f_h_align:       "Left","Center","Right"
        :param f_v_align:       "Bottom","Center","Top"
        :param f_category:      "@" Text Format, "0.00" Number Format
        :param f_col_width:     column width or "AUTO_FIT"
        :param f_wrap_text:     True, False(default)
        :param f_auto_filter:   AutoFilter, False(default)  only use for 1 row!

        :author:                kuberad
        """
        if ws_name is None:
            # use current
            pass
        elif ws_name in self.get_work_sheet_names():
            # select if already there
            self.__worksheet = self.__workbook.Worksheets(ws_name)
        else:
            # name not existent -> create new sheet
            self.__worksheet = self.__workbook.Worksheets.Add()
            self.__worksheet.Name = ws_name

        if row_from <= 0 or col_from <= 0:
            raise Exception('Error: wrong indexing (%s, %s)! start with 1!!' % (str(row_from), str(col_from)))
        if data is None:
            raise Exception('Error: data is None to write into excel!! ')
        elif type(data) in [int, float, bytes] or isinstance(data, six.integer_types):
            # single data
            data = [[data]]
        elif isinstance(data, list):
            # a list ... is it a list of lists?
            if len(data) > 0:
                if isinstance(data[0], list):
                    # list of rows --> everythings OK ... perhaps
                    pass
                else:
                    # 1 list ... 1 row
                    data = [data]
            else:
                # empty list
                raise Exception('Error: empty data !!')
        else:
            raise Exception('Error: unsupported data type: single value, 1 list for row or list of rows !!')

        if empty_value is not None:
            # check and fill empty cells
            # determine max row len
            max_row_len = 0
            for row in data:
                if row is not None:
                    max_row_len = max(max_row_len, len(row))
            # check for empty cells
            for i in range(len(data)):
                for v in range(len(data[i])):
                    if data[i][v] is None or data[i][v] == []:
                        data[i][v] = empty_value
                delta = max_row_len - len(data[i])
                while delta > 0:
                    data[i].append(empty_value)
                    delta -= 1
            col_to = col_from + max_row_len - 1
        else:
            col_to = col_from + len(data[0]) - 1
        row_to = row_from + len(data) - 1
        self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                               self.__worksheet.Cells(row_to, col_to)).Value = data

        if(f_regular is False and f_italic is False and f_bold is False and
           f_underline is False and f_font_name is None and
           f_font_color is None and f_cell_color is None and
           f_font_size is None and f_orientation is None and
           f_h_align is None and f_v_align is None and f_category is None and
           f_col_width is None and f_wrap_text is False and
           f_auto_filter is False):
            # nothing to format ...
            pass
        else:
            self.set_format(row_from, col_from, worksheet_name=ws_name,
                            row_to=row_to,
                            col_to=col_to,
                            regular=f_regular,
                            italic=f_italic,
                            bold=f_bold,
                            underline=f_underline,
                            font_name=f_font_name,
                            font_color=f_font_color,
                            cell_color=f_cell_color,
                            font_size=f_font_size,
                            orientation=f_orientation,
                            h_align=f_h_align,
                            v_align=f_v_align,
                            category=f_category,
                            col_width=f_col_width,
                            wrap_text=f_wrap_text,
                            auto_filter=f_auto_filter)

    def open_workbook(self, file_path, worksheet=None):
        """
        Open the specified excel file

        :param file_path: path/to/your/file
        :param worksheet: open worksheet on top
        :author:           Robert Hecker
        """
        self.close_workbook()
        self.__workbook = self.__app.Workbooks.Open(file_path)
        if self.__workbook is not None and worksheet is not None:
            return self.select_worksheet(worksheet)

        return self.__workbook is not None

    def create_workbook(self):
        """
        Create an excel file

        :author:           Robert Hecker
        """
        self.close_workbook()
        self.__workbook = self.__app.Workbooks.Add()

        if self.__workbook is not None:
            return True
        else:
            return False

    def close_workbook(self):
        """
        Close excel file
        :author:           Robert Hecker
        """
        if self.__workbook is not None:
            self.__worksheet = None
            self.__workbook.Close()
            del self.__workbook
            self.__workbook = None

    def save_workbook(self, name=None):
        """
        Save opened excel file

        :param name: - if no name given like parameter -> Save
                     - if name parameter -> SaveAs - save excel file with specified name

        :author:           Robert Hecker
        """
        if name is not None:
            self.__workbook.SaveAs(name)
        else:
            self.__workbook.save()

# Worksheet Functions ------------------------------------------------------

    def create_worksheet(self, name):
        """
        Create sheet in the opened excel file

        :param name: the new worksheet name

        :author:           Robert Hecker
        """
        self.__worksheet = self.__workbook.Worksheets.Add()
        self.__worksheet.Name = name

        if self.__worksheet is not None:
            return True
        else:
            return False

    def select_worksheet(self, name):
        """
        Select a sheet for the next operations to be made in

        :param name: the name of the worksheet to work with

        :author:           Robert Hecker
        """
        self.__worksheet = self.__workbook.Worksheets(name)

        if self.__worksheet is not None:
            return True
        else:
            return False

    def delete_worksheet(self, name):
        """
        Delete the specified Worksheet

        :param name:

        :author:           Nicoara Maria
        """
        self.__app.DisplayAlerts = False
        self.__workbook.Worksheets(name).Delete()

    def count_worksheets(self):
        """
        Count the worksheets of the current excel file

        :return:           the number of worksheets

        :author:           Nicoara Maria
        """
        return self.__workbook.Worksheets.Count

    def get_work_sheet_names(self):
        """
        Get all worksheets names of the current excel file

        :return:        list with worksheed names

        :author:        Anne Skerl
        """
        worksheetnames = []
        worksheetcount = self.count_worksheets()
        for index in range(1, worksheetcount + 1):
            worksheetnames.append(self.__workbook.Worksheets(index).Name)
        return worksheetnames

# Attributes ---------------------------------------------------------------
    def visible(self, bvisible):
        """
        Make excel visible

        :param bvisible:

        :author:        Robert Hecker
        """
        self.__app.visible = bvisible

# Data I/O -----------------------------------------------------------------
    def get_last_cell(self, ws_name=None):
        """
        Get row and column index of last Cell

        :param ws_name: (otional) work sheet name
        :return:        lastrow, lastcol

        :author:        Anne Skerl
        """
        # check worksheet
        if ws_name is None:
            # use current
            pass
        else:
            try:
                self.__workbook.Worksheets(ws_name)
            except:  # pylint:disable=E0611
                raise Exception('Error: worksheet does not exist : %s !!' % str(ws_name))
            self.__worksheet = self.__workbook.Worksheets(ws_name)
        lastrow = self.__worksheet.UsedRange.Rows.Count
        lastcol = self.__worksheet.UsedRange.Columns.Count
        return lastrow, lastcol

    def set_cell_value(self, row, col, value):
        """
        Set the specified Cell with an Value

        row and col could be integer or string for example "A", 'A' or 1

        excel rows and columns start with index 1!!

        :param row:    cell row in excel notation (starting at 1:1 resp. A1)
        :type  row:    str, int
        :param col:    cell column in excel notation like 1 or 'A' (starting at 1:1 resp. A1)
        :type  col:    str, int
        :param value:  whatever to store in that cell
        :return:       -

        :author:        Robert Hecker
        """
        self.__worksheet.Cells(row, col).Value = value

    def set_cell_formula(self, row, col, formula, use_local=False):
        """
        Inserts a formula in the specified cell.

        :param row:        row number
        :type row:         int
        :param col:        column number
        :type col:         int
        :param formula:    Excel formula
        :type formula:     str
        :param use_local:  - if True, the formula must be expressed using the localized version of the Excel functions
                             (the language depends on the local installation of the Microsoft Office suite).
                           - if False, the formula must be expressed using the English version of the Excel functions.
        :type use_local:   str
        :return:           -
        """
        if use_local is False:
            self.__worksheet.Cells(row, col).Formula = formula
        else:
            self.__worksheet.Cells(row, col).FormulaLocal = formula

    def set_cell_comment(self, row, col, value):
        """
        Add a comment to the specified Cell

        row and col could be integer or string for example "A", 'A' or 1

        the comment is sized automatically by Excel, so also long lines and many columns are visible

        reading a comment is not implemented as a comment is not directly stored to a cell,
        so finding a comment is more complicated and not needed yet

        :param row: cell row in excel notation (starting at 1:1 resp. A1)
        :type  row: str, int
        :param col: cell column in excel notation like 1 or 'A' (starting at 1:1 resp. A1)
        :type  col: str, int
        :param value: comment to add to cell
        :type  value: str
        :return:      -

        :author:        Joachim Hospes
        """
        self.__worksheet.Cells(row, col).AddComment(value)
        self.__worksheet.Cells(row, col).Comment.Shape.TextFrame.AutoSize = True

    def change_calculation_mode(self, mode=XL_CALCULATION_AUTOMATIC):
        """
        Specifies the calculation mode.

        The mode must be one of the following constant values:

        - ``XL_CALCULATION_AUTOMATIC`` (Excel controls recalculation);
        - ``XL_CALCULATION_MANUAL`` (Calculation is done when the user requests it);
        - ``XL_CALCULATION_SEMIAUTOMATIC`` (Excel controls recalculation but ignores changes in tables).

        If a different or no value is specified, ``XL_CALCULATION_AUTOMATIC`` is assumed and used.

        :param mode:  calculation mode (see above), default: ``XL_CALCULATION_AUTOMATIC``
        :type mode:   int
        :return:      -
        """
        calculation_modes = (XL_CALCULATION_AUTOMATIC, XL_CALCULATION_MANUAL, XL_CALCULATION_SEMIAUTOMATIC)
        if mode in calculation_modes:
            self.__app.Calculation = mode
        else:
            self.__app.Calculation = XL_CALCULATION_AUTOMATIC

    def get_cell_value(self, row, col):
        """
        Get the specified Cell value. Row and col could be integer
        or string for example "A", 'A' or 1

        :param row:
        :param col:
        :return:        value

        :author:        Robert Hecker
        """
        return self.__worksheet.Cells(row, col).Value

    def set_range_values(self, worksheet_name, row_from, col_from, values, empty_value="'-"):  # pylint: disable=R0913
        """
        Set the specified cells range values.
        row_from and col_from could be integer or string, for example "A", 'A' or 1

        :param worksheet_name:   name of the excel worksheet
        :param row_from:         row number (integer data type)
        :param col_from:         column number (integer data type)
        :param empty_value:      when None no consistency check, otherwise fill empty cell with this value
        :param values:           is a tuple of tuples, each tuple corresponds to a row in excel sheet

        :author:                 Nicoara Maria
        """
        if empty_value is not None:
            # check and fill empty cells
            # determine max row len
            max_row_len = 0
            for row in values:
                if row is not None:
                    max_row_len = max(max_row_len, len(row))
            # check for empty cells
            for i in range(len(values)):
                for v in range(len(values[i])):
                    if values[i][v] is None or values[i][v] == []:
                        values[i][v] = empty_value
                delta = max_row_len - len(values[i])
                while delta > 0:
                    values[i].append(empty_value)
                    delta -= 1
            col_to = col_from + max_row_len - 1
        else:
            col_to = col_from + len(values[0]) - 1
        row_to = row_from + len(values) - 1
        self.__worksheet = self.__workbook.Worksheets(worksheet_name)
        self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                               self.__worksheet.Cells(row_to, col_to)).Value = values

    def get_range_values(self, worksheet_name, range_address):
        """
        Return the specified cells range values

        :param worksheet_name:   name of the excel worksheet
        :param range_address:    rangeAddress,
                                 tuple of integers (row1,col1,row2,col2) or "cell1Address:cell2Address",
                                 row1,col1 refers to first cell(left upper corner),
                                 row2,col2 refers to second cell(right botom corner),
                                 e.g. (1,2,5,7) or "B1:G5"

        :author:                 Nicoara Maria
        """
        self.__worksheet = self.__workbook.Worksheets(worksheet_name)
        if isinstance(range_address, str):
            return self.__worksheet.Range(range_address).Value
        elif isinstance(range_address, tuple):
            row1 = range_address[0]
            col1 = range_address[1]
            row2 = range_address[2]
            col2 = range_address[3]
            return self.__worksheet.Range(self.__worksheet.Cells(row1, col1), self.__worksheet.Cells(row2, col2)).Value

    def delete_cell_content(self, row, col):
        """
        Delete the specified cell content -> empty cell

        row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :author:                 Nicoara Maria
        """
        self.__worksheet.Cells(row, col).ClearContents()

    def delete_range_content(self, row_from, col_from, row_to, col_to):
        """
        Delete the specified range content  -> empty range cell

        row and col could be integer or string, for example "A", 'A' or 1

        :param row_from:
        :param col_from:
        :param row_to:
        :param col_to:
        :author:                 Nicoara Maria
        """
        self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                               self.__worksheet.Cells(row_to, col_to)).ClearContents()

# Format -----------------------------------------------------------------
    def set_cell_font_style(self, row, col, regular=True, bold=False,  # pylint: disable=R0913
                            italic=False, underline=False):
        """
        Set the Font style of the specified Cell to Bold, Italic, Underline or Regular

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param regular:   the font style will be regular by default
        :param bold:      False, by default
        :param italic:    False, by default
        :param underline: False, by default

        :author:           Nicoara Maria
        """
        if regular is True:
            self.__worksheet.Cells(row, col).Font.FontStyle = "Regular"

        if bold is True:
            self.__worksheet.Cells(row, col).Font.Bold = True

        if italic is True:
            self.__worksheet.Cells(row, col).Font.Italic = True

        if underline is True:
            self.__worksheet.Cells(row, col).Font.Underline = True

    def set_cell_category(self, row, col, category):
        """
        Set the cell category of the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param category: can be for example "@" for Text Format or "0.00" for Number Format

        :author:           Nicoara Maria
        """
        self.__worksheet.Cells(row, col).NumberFormat = category

    def set_cell_font_name(self, row, col, font_name):
        """
        Set the Font name of the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param font_name: can be for example "Arial" or "Times New Roman"

        :author:       Nicoara Maria
        """
        self.__worksheet.Cells(row, col).Font.Name = font_name

    def set_cell_font_color(self, row, col, font_color):
        """
        Set the Font name of the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param font_color: can be for example 'Red' or  self.FONT_COLOR_RED

        :author:           Nicoara Maria
        """
        # For choosing the right color see the COLOR_MAP
        if font_color in COLOR_MAP:
            self.__worksheet.Cells(row, col).Font.ColorIndex = COLOR_MAP[font_color]
        else:
            print((" %s is not a valid color, for more details see the COLOR_MAP defined in stk_excel module" %
                   str(font_color)))

    def set_characters_color(self, row, col, char_idx_start, char_idx_stop, font_color):  # pylint: disable=R0913
        """
        Set the color of specified charactersfrom the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param char_idx_start: the starting position of the string you want to change the color of
        :param char_idx_stop: the end position of the string you want to change the color of
        :param font_color: can be for example 'Red' or self.FONT_COLOR_RED

        :author:           Nicoara Maria
        """
        self.__worksheet.Cells(row, col).GetCharacters(char_idx_start, char_idx_stop).Font.ColorIndex = font_color

    def set_cell_font_size(self, row, col, font_size):
        """
        Set the Font size of the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param font_size: can be a number

        :author:           Nicoara Maria
        """

        self.__worksheet.Cells(row, col).Font.Size = font_size

    def set_cell_text_orientation(self, row, col, degrees):
        """
        Set the text orientation of the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param degrees: can be a number, for example 90 -> text will be written vertical

        :author:           Nicoara Maria
        """
        self.__worksheet.Cells(row, col).Orientation = degrees

    def merge_cells(self, row_from, column_from, row_to, colum_to):
        """
        Merge the range of the specified cells

        The row_from, column_from, row_to, colum_to could be integer or string, for example "A", 'A' or 1

        :param row_from:
        :param column_from: The first cell from the selection
        :param row_to:
        :param colum_to: The last cell from the selection

        :author:           Nicoara Maria
        """
        self.__worksheet.Range(self.__worksheet.Cells(row_from, column_from),
                               self.__worksheet.Cells(row_to, colum_to)).merge_cells = True

    def set_vertical_cell_align(self, row, col, alignment):
        """
        Set the vertical alignment of the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param alignment: can take the following values: "Botom", "Center" or "Top"

        :author:           Nicoara Maria
        """
        if alignment == "Botom":
            self.__worksheet.Cells(row, col).VerticalAlignment = VERTICAL_ALIGNMENT_BOTOM
        elif alignment == "Center":
            self.__worksheet.Cells(row, col).VerticalAlignment = VERTICAL_ALIGNMENT_CENTER
        elif alignment == "Top":
            self.__worksheet.Cells(row, col).VerticalAlignment = VERTICAL_ALIGNMENT_TOP

    def set_horizontal_cell_align(self, row, col, alignment):
        """
        Set the horizontal alignment of the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param alignment: can take the fallowing values: "Left", "Center" or "Right"

        :author:           Nicoara Maria
        """
        if alignment == "Left":
            self.__worksheet.Cells(row, col).Horizontal_Alignment = HORIZONTAL_ALIGNMENT_LEFT
        elif alignment == "Center":
            self.__worksheet.Cells(row, col).HorizontalAlignment = HORIZONTAL_ALIGNMENT_CENTER
        elif alignment == "Right":
            self.__worksheet.Cells(row, col).HorizontalAlignment = HORIZONTAL_ALIGNMENT_RIGHT

    def set_auto_fit_columns(self, column):
        """
        Set autofit of the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param column:

        :author:           Nicoara Maria
        """
        self.__worksheet.Columns(column).EntireColumn.AutoFit()

    def insert_hyperlink(self, row, col, hyperlink, text):
        r"""
        Insert a hyperlink in the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param hyperlink: the link, for e.g. "www.google.ro" or "O:\\Li\\"
        :param text: the text that will be displayed in the cell, e.g. "google link"

        :author:           Nicoara Maria
        """
        self.__worksheet.Cells(row, col).Hyperlinks.Add(self.__worksheet.Cells(row, col), hyperlink, "", text, text)

    def set_cell_color(self, row_from, col_from, row_to, col_to, color):  # pylint: disable=R0913
        """
        Set the color of the specified Cell

        The row_from/row_to and col_from/row_to could be integer or string, for example "A", 'A' or 1

        :param row_from:
        :param col_from:
        :param row_to:
        :param col_to:
        :param color:  can be a string that represents a color,
                       for example 'Red' or 'Yellow' or self.FONT_COLOR_RED

        :author:           Nicoara Maria
        """
        # For choosing the right color see the COLOR_MAP
        if color in COLOR_MAP:
            self.__worksheet.Range(self.__worksheet.Cells(row_from, col_from),
                                   self.__worksheet.Cells(row_to, col_to)).Interior.ColorIndex = COLOR_MAP[color]
        else:
            print("%s is not a valid color, for more details see the COLOR_MAP defined in stk_excel module" % color)

    def set_cell_wrap_text(self, row, col):
        """
        Wrap text in the specified Cell

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:


        :author:           Nicoara Maria
        """
        self.__worksheet.Cells(row, col).WrapText = True

    def set_column_width(self, row, col, new_width):
        """
        Set the width of the column that the specified cell is a part of

        The row and col could be integer or string, for example "A", 'A' or 1

        :param row:
        :param col:
        :param new_width: is a number that specifies the width of the column

        :author:           Nicoara Maria
        """
        self.__worksheet.Cells(row, col).ColumnWidth = new_width

    def set_cells_borders(self, row_from, column_from, row_to, colum_to, line_width):  # pylint: disable=R0913
        """
        Set the borders of the specified range(selection) of cells

        The row_from, column_from, row_to, colum_to could be integer or string,
        for example "A", 'A' or 1

        :param row_from:
        :param column_from: The first cell from the selection
        :param row_to:
        :param colum_to: The last cell from the selection
        :param line_width: takes values in [1,4]interval, 2 - continuous line

        :author:           Nicoara Maria
        """
        # if there are no inside horizontal borders to set
        if row_from == row_to:
            for cnt in BORDERS_MAP[:-1]:
                self.__worksheet.Range(self.__worksheet.Cells(row_from, column_from),
                                       self.__worksheet.Cells(row_to, colum_to)). \
                    Borders(cnt).LineStyle = CONTINUOUS_BORDER
                self.__worksheet.Range(self.__worksheet.Cells(row_from, column_from),
                                       self.__worksheet.Cells(row_to, colum_to)). \
                    Borders(cnt).Weight = line_width
        # if there are no inside vertical borders to set
        elif column_from == colum_to:
            for cnt in BORDERS_MAP[:4] + [BORDERS_MAP[-1]]:
                self.__worksheet.Range(self.__worksheet.Cells(row_from, column_from),
                                       self.__worksheet.Cells(row_to, colum_to)). \
                    Borders(cnt).LineStyle = CONTINUOUS_BORDER
                self.__worksheet.Range(self.__worksheet.Cells(row_from, column_from),
                                       self.__worksheet.Cells(row_to, colum_to)). \
                    Borders(cnt).Weight = line_width

        else:
            for cnt in BORDERS_MAP:
                self.__worksheet.Range(self.__worksheet.Cells(row_from, column_from),
                                       self.__worksheet.Cells(row_to, colum_to)).Borders(cnt). \
                    LineStyle = CONTINUOUS_BORDER
                self.__worksheet.Range(self.__worksheet.Cells(row_from, column_from),
                                       self.__worksheet.Cells(row_to, colum_to)). \
                    Borders(cnt).Weight = line_width

    def set_data_autofilter(self, col):
        """
        Insert filter in the specified Cell

        The col could be integer or string, for example "A", 'A' or 1

        :param col:

        :author:           Nicoara Maria
        """
        self.__worksheet.Cells(col).AutoFilter()

    def insert_chart(self, sheet_name, num=1, left=10, width=600, top=50, height=450,  # pylint: disable=R0913
                     chart_type=-4169):
        """
        Insert a chart

        :param sheet_name:
        :param num:
        :param left: object
        :param width:
        :param top:
        :param height:
        :param chart_type:
        :author:           Nicoara Maria
        """
        # noinspection PyBroadException
        try:
            self.select_worksheet(sheet_name)
        # noinspection PyBroadException
        except:  # pylint: disable=W0702
            # sheet doesn't exist so create it
            self.create_worksheet(sheet_name)
        # noinspection PyBroadException
        try:
            self.__workbook.Sheets(sheet_name).ChartObjects(num).Activate  # already exists
        except:  # pylint: disable=W0702
            self.xlchart = self.__workbook.Sheets(sheet_name).ChartObjects().Add(Left=left, Width=width,
                                                                                 Top=top, Height=height)
            self.xlchart.Chart.ChartType = chart_type

    def insert_picture_from_file(self, file_path, left=0, top=0, width=350, height=300):  # pylint: disable=R0913
        """
        Insert a picture from the specified file

        :param file_path:
        :param left: how far from the left of the window
        :param top: how far from the top of the window
        :param width: image width
        :param height: image height

        :author:           Nicoara Maria
        """
        self.__worksheet.Shapes.AddPicture(file_path, 1, 1, left, top, width, height)

"""
CHANGE LOG:
-----------
$Log: excel.py  $
Revision 1.1 2020/03/25 21:22:09CET Leidenberger, Ralf (uidq7596) 
Initial revision
Member added to project /ADAS/SW/Integration/06_Simulation_Components/SVT_SILValidationTools/05_Test_Environment/Dynamic_Tests/SVT/ecu_sil_tool/framework/rep/project.pj
"""
