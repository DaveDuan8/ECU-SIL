"""
stk/rep/excel
-------------

Module to Create Excel Based Reports.

:org:           Continental AG
:author:        Robert Hecker,
                David Kubera,
                Maria Nicoara

:version:       $Revision: 1.6 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2015/09/08 09:00:11CEST $
"""
# - imports Python modules --------------------------------------------------------------------------------------------
from win32com.client import constants, DispatchEx
from win32gui import PostMessage
from win32con import WM_QUIT, PROCESS_TERMINATE
from win32process import GetWindowThreadProcessId
from win32api import OpenProcess, TerminateProcess, CloseHandle
from time import sleep
from pythoncom import com_error
import six

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.util.helper import deprecated

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

    .. python::

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
            except:  # pylint: disable=W0702
                self.__workbook = self.__app.Workbooks.Add()
                self._workfile = workfile

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
            try:
                hdl = OpenProcess(PROCESS_TERMINATE, 0, proc)
                if hdl:
                    TerminateProcess(hdl, 0)
                    CloseHandle(hdl)
            except:  # pylint: disable=W0702
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
        except:  # pylint: disable=W0702
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
            except com_error:  # pylint:disable=E0611
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

    def merge_cells2(self, tbl_idx):
        """TODO

        :param tbl_idx:
        :type tbl_idx:
        :return:
        :rtype:
        """
        tbl_obj = self.__internal_get_table(tbl_idx)
        cell = self.__internal_get_table_cell(tbl_obj, 1, 1)
        cell.Merge(self.__internal_get_table_cell(tbl_obj, 2, 1))

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
            except com_error:  # pylint:disable=E0611
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
                    if data[i][v] is None:
                        data[i][v] = empty_value
                    elif data[i][v] == []:
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
            self.__workbook.Save()

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
            except com_error:  # pylint:disable=E0611
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
                    if values[i][v] is None:
                        values[i][v] = empty_value
                    elif values[i][v] == []:
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
        try:
            self.select_worksheet(sheet_name)
        except:  # pylint: disable=W0702
            # sheet doesn't exist so create it
            self.create_worksheet(sheet_name)
        try:
            self.__workbook.Sheets(sheet_name).ChartObjects(num).Activate  # already exists
        except:  # pylint: disable=W0702
            # TODO: unknown to __init__ !!!
            self.xlchart = self.__workbook.Sheets(sheet_name).ChartObjects().Add(Left=left, Width=width,
                                                                                 Top=top, Height=height)
            self.xlchart.Chart.ChartType = chart_type

    def add_xy_chart_series(self, sheet, toprow, bottomrow, xcol, ycol,  # pylint: disable=R0913,R0914
                            series_name="", chart_sheet="", chart_num=1,
                            color=1, style='line', title="", xlabel="", ylabel="",
                            errorbars=None):
        """TODO

        :param sheet:
        :type sheet:
        :param toprow:
        :type toprow:
        :param bottomrow:
        :type bottomrow:
        :param xcol:
        :type xcol:
        :param ycol:
        :type ycol:
        :param series_name:
        :type series_name:
        :param chart_sheet:
        :type chart_sheet:
        :param chart_num:
        :type chart_num:
        :param color:
        :type color:
        :param style:
        :type style:
        :param title:
        :type title:
        :param xlabel:
        :type xlabel:
        :param ylabel:
        :type ylabel:
        :param errorbars:
        :type errorbars:
        :return:
        :rtype:
        """
        if not chart_sheet:
            chart_sheet = sheet

        # series properties
        sht = self.__workbook.Worksheets(sheet)
        see = self.xlChart.Chart.SeriesCollection().NewSeries()
        see.Values = sht.Range(sht.Cells(toprow, ycol), sht.Cells(bottomrow, ycol))
        see.XValues = sht.Range(sht.Cells(toprow, xcol), sht.Cells(bottomrow, xcol))
        if series_name:
            see.Name = series_name
        if style == 'line':
            # line style
            see.MarkerStyle = constants.xlNone
            see.Border.ColorIndex = color
            see.Border.Weight = constants.xlHairline
            see.Border.LineStyle = constants.xlContinuous
            see.Border.Weight = constants.xlMedium
        if style == 'point':
            # point style
            # se.MarkerBackgroundColorIndex = constants.xlNone
            # se.MarkerForegroundColorIndex = color
            see.MarkerBackgroundColorIndex = color
            see.MarkerForegroundColorIndex = 1  # black
            # se.MarkerStyle = constants.xlMarkerStyleCircle
            see.MarkerStyle = constants.xlMarkerStyleSquare
            see.MarkerSize = 5
        # Chart properties
        cht = self.xlBook.Sheets(chart_sheet).ChartObjects(chart_num).Chart
        # Chart Title
        if title:
            cht.HasTitle = True
            cht.ChartTitle.Caption = title
            cht.ChartTitle.Font.Name = 'Arial'
            cht.ChartTitle.Font.Size = 10
            cht.ChartTitle.Font.Bold = False
        # X axis labels
        if xlabel:
            cht.Axes(constants.xlCategory).HasTitle = True
            cht.Axes(constants.xlCategory).AxisTitle.Caption = xlabel
            cht.Axes(constants.xlCategory).AxisTitle.Font.Name = 'Arial'
            cht.Axes(constants.xlCategory).AxisTitle.Font.Size = 10
            cht.Axes(constants.xlCategory).AxisTitle.Font.Bold = False
            cht.Axes(constants.xlCategory).MinimumScale = 0
            cht.Axes(constants.xlCategory).MaximumScaleIsAuto = True
        # Y axis labels
        if ylabel:
            cht.Axes(constants.xlValue).HasTitle = True
            cht.Axes(constants.xlValue).AxisTitle.Caption = ylabel
            cht.Axes(constants.xlValue).AxisTitle.Font.Name = 'Arial'
            cht.Axes(constants.xlValue).AxisTitle.Font.Size = 10
            cht.Axes(constants.xlValue).AxisTitle.Font.Bold = False
            cht.Axes(constants.xlValue).MinimumScale = 0
            cht.Axes(constants.xlValue).MaximumScaleIsAuto = True

        if errorbars is not None:
            amount = "".join(["=", chart_sheet, "!",
                              "R",
                              str(errorbars['amount'][0]),
                              "C",
                              str(errorbars['amount'][2]),
                              ":",
                              "R",
                              str(errorbars['amount'][1]),
                              "C",
                              str(errorbars['amount'][2])])

            see.ErrorBar(Direction=constants.xlY,
                         Include=constants.xlErrorBarIncludeBoth,
                         Type=constants.xlErrorBarTypeCustom,
                         Amount=amount, MinusValues=amount)

            see.ErrorBars.EndStyle = constants.xlNoCap
            see.ErrorBars.Border.LineStyle = constants.xlContinuous
            see.ErrorBars.Border.ColorIndex = color
            see.ErrorBars.Border.Weight = constants.xlHairline

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

    @deprecated('close')
    def Close(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "Close" is deprecated use "close" instead', stacklevel=2)
        return self.close()

    @deprecated('open_workbook')
    def OpenWorkbook(self, file_path):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "OpenWorkbook" is deprecated use "open_workbook" instead', stacklevel=2)
        return self.open_workbook(file_path)

    @deprecated('create_workbook')
    def CreateWorkbook(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "CreateWorkbook" is deprecated use "create_workbook" instead', stacklevel=2)
        return self.create_workbook()

    @deprecated('close_workbook')
    def CloseWorkbook(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "CloseWorkbook" is deprecated use "close_workbook" instead', stacklevel=2)
        return self.close_workbook()

    @deprecated('save_workbook')
    def SaveWorkbook(self, name=None):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SaveWorkbook" is deprecated use "save_workbook" instead', stacklevel=2)
        return self.save_workbook(name)

    @deprecated('create_worksheet')
    def CreateWorksheet(self, name):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "CreateWorksheet" is deprecated use "create_worksheet" instead', stacklevel=2)
        return self.create_worksheet(name)

    @deprecated('select_worksheet')
    def SelectWorksheet(self, name):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SelectWorksheet" is deprecated use "select_worksheet" instead', stacklevel=2)
        return self.select_worksheet(name)

    @deprecated('delete_worksheet')
    def DeleteWorksheet(self, name):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "DeleteWorksheet" is deprecated use "delete_worksheet" instead', stacklevel=2)
        return self.delete_worksheet(name)

    @deprecated('count_worksheets')
    def CountWorksheets(self):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "CountWorksheets" is deprecated use "count_worksheets" instead', stacklevel=2)
        return self.count_worksheets()

    @deprecated('visible')
    def Visible(self, bVisible):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "Visible" is deprecated use "visible" instead', stacklevel=2)
        return self.visible(bVisible)

    @deprecated('set_cell_value')
    def SetCellValue(self, row, col, value):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetCellValue" is deprecated use "set_cell_value" instead', stacklevel=2)
        return self.set_cell_value(row, col, value)

    @deprecated('get_cell_value')
    def GetCellValue(self, row, col):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "GetCellValue" is deprecated use "get_cell_value" instead', stacklevel=2)
        return self.get_cell_value(row, col)

    @deprecated('set_range_values')
    def SetRangeValues(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetRangeValues" is deprecated use "set_range_values" instead', stacklevel=2)
        return self.set_range_values(*args, **kw)

    @deprecated('get_range_values')
    def GetRangeValues(self, worksheet_name, range_address):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "GetRangeValues" is deprecated use "get_range_values" instead', stacklevel=2)
        return self.get_range_values(worksheet_name, range_address)

    @deprecated('delete_cell_content')
    def DeleteCellContent(self, row, col):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "DeleteCellContent" is deprecated use "delete_cell_content" instead', stacklevel=2)
        return self.delete_cell_content(row, col)

    @deprecated('delete_range_content')
    def DeleteRangeContent(self, row_from, col_from, row_to, col_to):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "DeleteRangeContent" is deprecated use "delete_range_content" instead', stacklevel=2)
        return self.delete_range_content(row_from, col_from, row_to, col_to)

    @deprecated('set_cell_font_style')
    def SetCellFontStyle(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetCellFontStyle" is deprecated use "set_cell_font_style" instead', stacklevel=2)
        return self.set_cell_font_style(*args, **kw)

    @deprecated('set_cell_category')
    def SetCellCategory(self, row, col, category):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetCellCategory" is deprecated use "set_cell_category" instead', stacklevel=2)
        return self.set_cell_category(row, col, category)

    @deprecated('set_cell_font_name')
    def SetCellFontName(self, row, col, font_name):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetCellFontName" is deprecated use "set_cell_font_name" instead', stacklevel=2)
        return self.set_cell_font_name(row, col, font_name)

    @deprecated('set_cell_font_color')
    def SetCellFontColor(self, row, col, font_color):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetCellFontColor" is deprecated use "set_cell_font_color" instead', stacklevel=2)
        return self.set_cell_font_color(row, col, font_color)

    @deprecated('set_characters_color')
    def SetCharactersColor(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetCharactersColor" is deprecated use "set_characters_color" instead', stacklevel=2)
        return self.set_characters_color(*args, **kw)

    @deprecated('set_cell_font_size')
    def SetCellFontSize(self, row, col, font_size):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetCellFontSize" is deprecated use "set_cell_font_size" instead', stacklevel=2)
        return self.set_cell_font_size(row, col, font_size)

    @deprecated('set_cell_text_orientation')
    def SetCellTextOrientation(self, row, col, degrees):  # pylint: disable=C0103
        """deprecated"""
        return self.set_cell_text_orientation(row, col, degrees)

    @deprecated('merge_cells')
    def MergeCells(self, row_from, column_from, row_to, colum_to):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "MergeCells" is deprecated use "merge_cells" instead', stacklevel=2)
        return self.merge_cells(row_from, column_from, row_to, colum_to)

    @deprecated('set_vertical_cell_align')
    def SetVerticalCellAlign(self, row, col, alignment):  # pylint: disable=C0103
        """deprecated"""
        return self.set_vertical_cell_align(row, col, alignment)

    @deprecated('set_horizontal_cell_align')
    def SetHorizontalCellAlign(self, row, col, alignment):  # pylint: disable=C0103
        """deprecated"""
        return self.set_horizontal_cell_align(row, col, alignment)

    @deprecated('set_auto_fit_columns')
    def SetAutoFitColumns(self, column):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetAutoFitColumns" is deprecated use "set_auto_fit_columns" instead', stacklevel=2)
        return self.set_auto_fit_columns(column)

    @deprecated('insert_hyperlink')
    def InsertHyperlink(self, row, col, hyperlink, text):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "InsertHyperlink" is deprecated use "insert_hyperlink" instead', stacklevel=2)
        return self.insert_hyperlink(row, col, hyperlink, text)

    @deprecated('set_cell_color')
    def SetCellColor(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "Close" is deprecated use "close" instead', stacklevel=2)
        return self.set_cell_color(*args, **kw)

    @deprecated('set_cell_wrap_text')
    def SetCellWrapText(self, row, col):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetCellWrapText" is deprecated use "set_cell_wrap_text" instead', stacklevel=2)
        return self.set_cell_wrap_text(row, col)

    @deprecated('set_column_width')
    def SetColumnWidth(self, row, col, new_width):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetColumnWidth" is deprecated use "set_column_width" instead', stacklevel=2)
        return self.set_column_width(row, col, new_width)

    @deprecated('set_cells_borders')
    def SetCellsBorders(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetCellsBorders" is deprecated use "set_cells_borders" instead', stacklevel=2)
        return self.set_cells_borders(*args, **kw)

    @deprecated('set_data_autofilter')
    def SetDataAutofilter(self, col):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "SetDataAutofilter" is deprecated use "set_data_autofilter" instead', stacklevel=2)
        return self.set_data_autofilter(col)

    @deprecated('insert_chart')
    def InsertChart(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "InsertChart" is deprecated use "insert_chart" instead', stacklevel=2)
        return self.insert_chart(*args, **kw)

    @deprecated('add_xy_chart_series')
    def AddXYChartSeries(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        # warnings.warn('Method "AddXYChartSeries" is deprecated use "add_xy_chart_series" instead', stacklevel=2)
        return self.add_xy_chart_series(*args, **kw)

    @deprecated('insert_picture_from_file')
    def InsertPictureFromFile(self, *args, **kw):  # pylint: disable=C0103
        """deprecated"""
        return self.insert_picture_from_file(*args, **kw)


"""
CHANGE LOG:
-----------
$Log: excel.py  $
Revision 1.6 2015/09/08 09:00:11CEST Hospes, Gerd-Joachim (uidv8815) 
set comment to autosize
- Added comments -  uidv8815 [Sep 8, 2015 9:00:12 AM CEST]
Change Package : 373679:2 http://mks-psad:7002/im/viewissue?selection=373679
Revision 1.5 2015/09/03 17:04:29CEST Hospes, Gerd-Joachim (uidv8815) 
AddComment for cells, test in test_WriteCell
Revision 1.4 2015/06/30 11:13:23CEST Mertens, Sven (uidv7805) 
fix for exception handling
--- Added comments ---  uidv7805 [Jun 30, 2015 11:13:24 AM CEST]
Change Package : 350659:3 http://mks-psad:7002/im/viewissue?selection=350659
Revision 1.3 2015/05/18 14:10:04CEST Mertens, Sven (uidv7805)
rewinding empty list error
--- Added comments ---  uidv7805 [May 18, 2015 2:10:05 PM CEST]
Change Package : 338361:1 http://mks-psad:7002/im/viewissue?selection=338361
Revision 1.2 2015/05/18 13:27:58CEST Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [May 18, 2015 1:27:58 PM CEST]
Change Package : 338361:1 http://mks-psad:7002/im/viewissue?selection=338361
Revision 1.1 2015/04/23 19:04:59CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/rep/project.pj
Revision 1.28 2015/04/10 13:55:09CEST Mertens, Sven (uidv7805)
- fix for deprecated methods,
- adding posibility to open worksheet on open
--- Added comments ---  uidv7805 [Apr 10, 2015 1:55:09 PM CEST]
Change Package : 318014:3 http://mks-psad:7002/im/viewissue?selection=318014
Revision 1.27 2015/04/01 13:48:26CEST Hospes, Gerd-Joachim (uidv8815)
docu update
--- Added comments ---  uidv8815 [Apr 1, 2015 1:48:27 PM CEST]
Change Package : 324228:1 http://mks-psad:7002/im/viewissue?selection=324228
Revision 1.26 2015/03/17 16:26:55CET Ellero, Stefano (uidw8660)
Implemented new method to set the calculation mode of excel cells.
--- Added comments ---  uidw8660 [Mar 17, 2015 4:26:56 PM CET]
Change Package : 317750:1 http://mks-psad:7002/im/viewissue?selection=317750
Revision 1.24 2015/01/27 16:16:42CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 27, 2015 4:16:42 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.23 2015/01/26 20:20:18CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
Revision 1.22 2014/03/28 11:32:46CET Hecker, Robert (heckerr)
commented out warnings.
--- Added comments ---  heckerr [Mar 28, 2014 11:32:46 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.21 2014/03/28 10:25:49CET Hecker, Robert (heckerr)
Adapted to new coding guiedlines incl. backwardcompatibility.
--- Added comments ---  heckerr [Mar 28, 2014 10:25:49 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.20 2014/03/27 12:21:45CET Hecker, Robert (heckerr)
added one more backwardcompatibility.
--- Added comments ---  heckerr [Mar 27, 2014 12:21:46 PM CET]
Change Package : 227240:2 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.19 2014/03/27 12:19:37CET Hecker, Robert (heckerr)
Added backwordsupport for long types.
--- Added comments ---  heckerr [Mar 27, 2014 12:19:37 PM CET]
Change Package : 227240:2 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.18 2014/03/25 08:59:32CET Hecker, Robert (heckerr)
Adaption to python 3.
--- Added comments ---  heckerr [Mar 25, 2014 8:59:32 AM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.17 2013/11/25 10:04:36CET Mertens, Sven (uidv7805)
removing some pylints and pep8 finally
--- Added comments ---  uidv7805 [Nov 25, 2013 10:04:37 AM CET]
Change Package : 207693:3 http://mks-psad:7002/im/viewissue?selection=207693
Revision 1.16 2013/11/25 09:36:39CET Mertens, Sven (uidv7805)
prevent del being called when close method was used
--- Added comments ---  uidv7805 [Nov 25, 2013 9:36:39 AM CET]
Change Package : 207693:2 http://mks-psad:7002/im/viewissue?selection=207693
Revision 1.15 2013/11/22 13:18:56CET Mertens, Sven (uidv7805)
adding with statement support,
removing Excel app shutdown problem
--- Added comments ---  uidv7805 [Nov 22, 2013 1:18:56 PM CET]
Change Package : 207693:1 http://mks-psad:7002/im/viewissue?selection=207693
Revision 1.14 2013/09/06 10:52:39CEST Mertens, Sven (uidv7805)
removing my own changes as agreeded
--- Added comments ---  uidv7805 [Sep 6, 2013 10:52:40 AM CEST]
Change Package : 196367:2 http://mks-psad:7002/im/viewissue?selection=196367
Revision 1.13 2013/08/02 14:36:55CEST Mertens, Sven (uidv7805)
when using integer, start index is 0,
when using strings it aligns with Excel's own
--- Added comments ---  uidv7805 [Aug 2, 2013 2:36:55 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.12 2013/07/17 09:29:35CEST Mertens, Sven (uidv7805)
replacing isinstance as of stepping over while bugfixing
--- Added comments ---  uidv7805 [Jul 17, 2013 9:29:36 AM CEST]
Change Package : 185933:2 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.11 2013/06/26 09:34:23CEST Mertens, Sven (uidv7805)
fix: colorizing index wrong, counting one more was wrong
--- Added comments ---  uidv7805 [Jun 26, 2013 9:34:23 AM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.10 2013/06/24 13:31:43CEST Mertens, Sven (uidv7805)
worksheet methods don't take over integers as column index by default, therefore
there is a need to transfer those into base26. Adaptation of all realted methdos needed.
--- Added comments ---  uidv7805 [Jun 24, 2013 1:31:43 PM CEST]
Change Package : 185933:1 http://mks-psad:7002/im/viewissue?selection=185933
Revision 1.9 2013/04/03 08:17:14CEST Mertens, Sven (uidv7805)
pep8: removing format errors
--- Added comments ---  uidv7805 [Apr 3, 2013 8:17:14 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.8 2013/04/03 08:02:12CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:13 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.7 2013/02/28 17:07:23CET Hecker, Robert (heckerr)
Updates regarding Pep8 Styleguides.
--- Added comments ---  heckerr [Feb 28, 2013 5:07:23 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.6 2013/02/28 08:12:12CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:13 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.5 2013/02/27 17:55:10CET Hecker, Robert (heckerr)
Removed all E000 - E200 Errors regarding Pep8.
--- Added comments ---  heckerr [Feb 27, 2013 5:55:10 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/26 18:05:54CET Hecker, Robert (heckerr)
Some modifications to get current Unittest working.
--- Added comments ---  heckerr [Feb 26, 2013 6:05:55 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/20 08:21:52CET Hecker, Robert (heckerr)
Adapted to Pep8 Coding Style.
--- Added comments ---  heckerr [Feb 20, 2013 8:21:52 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/18 10:30:55CET Paulig, Ralf (uidt3509)
Merged fix for open excel.exe from old STK.
--- Added comments ---  uidt3509 [Feb 18, 2013 10:30:57 AM CET]
Change Package : 175382:1 http://mks-psad:7002/im/viewissue?selection=175382
Revision 1.1 2013/02/12 16:13:28CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm
/STK_ScriptingToolKit/04_Engineering/stk/rep/project.pj
Revision 1.12 2012/05/02 09:02:00CEST Mogos, Sorin (mogoss)
* update: added merge_cells method
--- Added comments ---  mogoss [May 2, 2012 9:02:05 AM CEST]
Change Package : 104217:1 http://mks-psad:7002/im/viewissue?selection=104217
Revision 1.11 2012/02/22 10:26:04CET Mogos, Sorin (mogoss)
* small bug-fix
--- Added comments ---  mogoss [Feb 22, 2012 10:26:13 AM CET]
Change Package : 89706:1 http://mks-psad:7002/im/viewissue?selection=89706
Revision 1.10 2010/05/17 15:00:03CEST dkubera
generic read get_data added
get_last_cell extended with optional worksheet parameter
--- Added comments ---  dkubera [2010/05/17 13:00:03Z]
Change Package : 39727:3 http://LISS014:6001/im/viewissue?selection=39727
Revision 1.9 2010/05/07 12:20:33CEST dkubera
interface change for set_data and set_format
- set_format: optional worksheet name, default current
- set_data: optional worksheet name, default current, when given write into existing or create new sheet
--- Added comments ---  dkubera [2010/05/07 10:20:34Z]
Change Package : 32862:6 http://LISS014:6001/im/viewissue?selection=32862
Revision 1.8 2010/05/07 11:18:43CEST dkubera
reworked:
- set_data and set_format functions added for robust and comfortable writing and formatting
- get_work_sheet_names added
- get_last_cell added
- documentation updated regarding guideline
--- Added comments ---  dkubera [2010/05/07 09:18:44Z]
Change Package : 32862:6 http://LISS014:6001/im/viewissue?selection=32862
Revision 1.7 2010/04/08 17:08:25CEST dkubera
Fix for inconsitent data : SetRangeValues fills empty cells instead of doing nothing
header and footer update
--- Added comments ---  dkubera [2010/04/08 15:08:25Z]
Change Package : 33974:4 http://LISS014:6001/im/viewissue?selection=33974
Revision 1.6 2009/11/11 13:54:02CET Sorin Mogos (smogos)
* added new functions
--- Added comments ---  smogos [2009/11/11 12:54:03Z]
Change Package : 33973:1 http://LISS014:6001/im/viewissue?selection=33973
$Add methods $ Nicoara Maria
"""
