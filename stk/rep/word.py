"""
stk/rep/word
------------

Module to create Reports as Microsoft Word Document.
Library to write and read word Files

:org:           Continental AG
:author:        Ovidiu Raicu,
                Robert Hecker,
                Sorin Mogos

:version:       $Revision: 1.2 $
:date:          $Date: 2015/12/07 08:50:01CET $
"""
# Imports ----------------------------------------------------------------------
import win32com.client as wc
import os.path
from os.path import exists
from pythoncom import CoInitializeEx, CoUninitialize, COINIT_APARTMENTTHREADED  # pylint: disable-msg=E0611

# - import STK modules ---------------------------------------------------------
from stk.util.helper import deprecated

# try:
#     from exceptions import StandardError as _BaseException
# except ImportError:
#     _BaseException = Exception

# ===================================================================================
# Constant declarations
# ===================================================================================
# FONT color constants used for changing the font color for all font functions
FONT_COLOR = {'Black': 0, 'White': 16777215, 'Red': 255, 'Bright Green': 65280,
              'Blue': 16711680, 'Yellow': 65535, 'Pink': 16711935,
              'Turqoise': 16776960, 'Dark Red': 128, 'Green': 32768,
              'Dark Blue': 8388608, 'Dark Yellow': 32896, 'Violet': 8388736,
              'Teal': 8421376, 'Gray-25%': 12632256, 'Gray-50%': 16,
              'Sky Blue': 16763904, 'Light Turqoise': 16777164,
              'Light Green': 13434828, 'Light Yellow': 10092543,
              'Pale Blue': 16764057, 'Rose': 13408767, 'Lavendar': 16751052,
              'Tan': 10079487, 'Light Blue': 16737843, 'Aqua': 13421619,
              'Lime': 52377, 'Gold': 52479, 'Light Orange': 39423,
              'Orange': 26367, 'Blue-Gray': 10053222, 'Gray-40%': 10066329,
              'Dark Teal': 6697728, 'Sea Green': 6723891, 'Dark Green': 13056,
              'Olive Green': 13107, 'Brown': 13209, 'Plum': 6697881,
              'Indigo': 10040115, 'Gray-80%': 3355443}
# Backround color uses the same constants as font color
BACKROUND_COLOR = FONT_COLOR
# Table autofit behavior
AUTOFIT_BEHAVIOR = {'AutoFitFixed': 0, 'AutoFitContent': 1, 'AutoFitWindow': 2}
# Paragraph alignment
PARAGRAPH_ALINGMENT = {'Left': 0, 'Center': 1, 'Right': 2, 'JustifyHigh': 7,
                       'JustifyLow': 8, 'JustifyMedium': 5}
# Used for shapes and pictures
TEXT_ORIENTATION = {'Downward': 3, 'Horizontal': 1,
                    'HorizontalRotatedFarEast': 6, 'Mixed': -2, 'Upward': 2,
                    'Vertical': 5, 'VerticalFarEast': 4}
# Used for diagrams
DIAGRAM_TYPE = {'Cycle': 2, 'Mixed': -2, 'OrganizationalChart': 1,
                'Pyramid': 4, 'Radial': 3, 'Target': 6, 'Venn': 5}


class WordException(Exception):
    """
    Exception class for stkWord.
    """
    def __init__(self, description):
        self._description = str(description)

    def __str__(self):
        errror_description = "\n=====================================================\n"
        errror_description += "ERROR: " + self._description
        errror_description += "\n=====================================================\n"
        return str(errror_description)

    @property
    def description(self):
        return self._description

    @deprecated('description (property)')
    def Description(self):
        """deprecated"""
        return self._description


# ==============================================================================
# Class declaration
# ==============================================================================
class Word(object):
    """Header / Footer contstans used by Word API"""
    HEADER_FOOTER_EVEN_PAGES = 0
    HEADER_FOOTER_FIRST_PAGE = 1
    HEADER_FOOTER_PRIMARY = 2

    # Page Number constants used by Word API
    PAGE_NUMBER_ALIGN_LEFT = 0
    PAGE_NUMBER_ALIGN_CENTER = 1
    PAGE_NUMBER_ALIGN_RIGHT = 2

    # stkWord class definition.
    def __init__(self, create_new_word_instance=False, visible=False):
        """Constructor"""
        self._create_new_word_instance = create_new_word_instance

        if self._create_new_word_instance:
            CoInitializeEx(COINIT_APARTMENTTHREADED)
            self._app = wc.DispatchEx('Word.Application')
        else:
            # self._app = wc.dynamic.Dispatch('Word.Application')
            self._app = wc.gencache.EnsureDispatch("Word.Application")

        if visible:
            self._app.Visible = True
        else:
            self._app.Visible = False

        self._document = None
        self.NUMBER_FORMAT_TEXT = "@"
        self.NUMBER_FORMAT_NUMBER = "0.00"
        self.NUMBER_FORMAT_DATE = "m/d/yyyy"
        self.NUMBER_FORMAT_TIME = "[$-F400]h:mm:ss AM/PM"
        self.NUMBER_FORMAT_PERCENTAGE = "0.00%"
        self.NUMBER_FORMAT_GENERAL = "General"

        self.FONT_NAME_ARIAL = "Arial"
        self.FONT_NAME_TIMES_NEW_ROMAN = "Times New Roman"
        self.FONT_NAME_COMIC = "Comic Sans MS"
        self.FONT_NAME_LUCIDA_CONSOLE = "Lucida Console"

        self.FONT_COLOR_RED = "Red"
        self.FONT_COLOR_YELLOW = "Yellow"
        self.FONT_COLOR_BLUE = "Blue"
        self.FONT_COLOR_GREEN = "Green"
        self.FONT_COLOR_GREY = "Gray-25%"
        self.FONT_COLOR_VIOLET = "Violet"

        self.FONT_STYLE_NORMAL = "Normal"

        self.ALIGNMENT_HORIZAONTAL_LEFT = "Left"
        self.ALIGNMENT_HORIZAONTAL_CENTER = "Center"
        self.ALIGNMENT_HORIZAONTAL_RIGHT = "Right"

        self.ALIGNMENT_VERTICAL_TOP = "Top"
        self.ALIGNMENT_VERTICAL_CENTER = "Center"
        self.ALIGNMENT_VERTICAL_BOTOM = "Botom"

        self.BORDER_DASHED = 1
        self.BORDER_THIN = 2
        self.BORDER_THICK1 = 3
        self.BORDER_THICK2 = 4

    def __del__(self):
        """ Destructor. """
        try:
            self._app.Quit()
        except Exception as errmsg:
            raise WordException("Error while closing MSWord App due to '%s'." % errmsg)

        del self._document
        del self._app

        if self._create_new_word_instance:
            CoUninitialize()

    def create_document(self):
        """Creates a new empty document in word."""
        try:
            self._document = self._app.Documents.Add()

        except Exception as errmsg:
            raise WordException("Error while creating document due to '%s'." % errmsg)

    def open_document(self, file_pathname):
        """Opens a new document.

         :param file_pathname: The file_pathname to the document.
        """
        if self.is_document_opened() is True:
            raise WordException("A document is already opened.")

        try:
            self._document = self._app.Documents.Open(file_pathname, False, False, False)
            self._document.ShowGrammaticalErrors = False
            self._document.ShowRevisions = False
            self._document.ShowSpellingErrors = False
        except Exception as errmsg:
            raise WordException("Error while opening document due to '%s'." % errmsg)

    def get_current_document_path(self):
        """Returns the path to the document currently opened.

        :return:  The path to the document currently opened.

        """
        if self.is_document_opened():
            raise WordException("No document currently opened.")
        else:
            try:
                return self._document.Path
            except Exception as errmsg:
                raise WordException("Failed to get the current document path due to '%s'." % errmsg)

    def is_document_opened(self):
        """Returns True or False whether there is a document currently opened.

        :return: True or False whether there is a document currently opened.

        """
        if self._document is None:
            return False
        else:
            return True

    def _internal_get_toc(self, tbl_toc_idx):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        else:
            try:
                tbl_toc_obj = self._document.TablesOfContents.Item(tbl_toc_idx)
            except:
                tmp = "The table of contents with the specified index does not "
                tmp += "exist or error occured while accessing it."
                raise WordException(tmp)
        return tbl_toc_obj

    def _internal_get_table(self, table_idx):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        if isinstance(table_idx, str):
            return self._internal_get_table_by_id(table_idx)
        else:
            return self._internal_get_table_by_idx(table_idx)

    def _internal_get_table_by_idx(self, table_idx):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        else:
            try:
                table = self._document.Tables.Item(table_idx)
            except Exception as errmsg:
                raise WordException("Error while getting table with %d index due to '%s'." % (table_idx, errmsg))

        return table

    def _internal_get_table_by_id(self, table_id_str):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        else:
            tbl_cnt = self.get_tables_count()
            tbl_cnt += 1
            try:
                for tbl_idx in range(1, tbl_cnt + 1):
                    tbl_obj = self._internal_get_table_by_idx(tbl_idx)
                    if tbl_obj.ID == table_id_str:
                        return tbl_obj
                # else:
                raise WordException("The specified ID does not exist.")
            except:
                tmp = "The specified ID does not exist or an error occured "
                tmp += "while attempting to access table with ID %(table_id)s." % {'table_id': table_id_str}
                raise WordException(tmp)

    def _internal_get_table_cell(self, table_obj, row_idx, col_idx):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        else:
            try:
                return table_obj.Cell(row_idx, col_idx)
            except:
                tmp = "An error occured while attempting to access cell "
                tmp += "[%(col)d X %(row)d]." % {'col': col_idx, 'row': row_idx}
                raise WordException(tmp)

    def _internal_get_table_cell_value(self, table_obj, row_idx, col_idx):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        tbl_cell_obj = self._internal_get_table_cell(table_obj, row_idx, col_idx)
        try:
            tbl_cell_value = tbl_cell_obj.Range.Text
        except:
            tmp = "The specified index does not exist or an error occured "
            tmp += "while attempting to access the table cell [%(col)d X %(row)d]." % {'col': col_idx, 'row': row_idx}
            raise WordException(tmp)
        return str(tbl_cell_value).rstrip("\r\007")

    def _internal_get_table_row(self, tbl_obj, row_idx):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        else:
            try:
                tbl_row_obj = tbl_obj.Rows(row_idx)
            except:
                tmp = "The specified index does not exist or an error occured "
                tmp += "while attempting to access the table row %(row)d ." % {'row': row_idx}
                raise WordException(tmp)
            return tbl_row_obj

    def _internal_get_table_column(self, tbl_obj, col_idx):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        else:
            try:
                tbl_col_obj = tbl_obj.Columns(col_idx)
            except:
                tmp = "The specified index does not exist or an error occured "
                tmp += "while attempting to access the table column %(row)d ." % {'row': col_idx}
                raise WordException(tmp)
            return tbl_col_obj

    def _internal_set_table_cell_value(self, tbl_obj, col_idx, row_idx, value):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        else:
            try:
                cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
                if cell is None:
                    return False
                else:
                    cell.Range.Text = value
            except:
                tmp = "The specified index does not exist or an error occured "
                tmp += "while attempting to access the table cell "
                tmp += "[%(col)d X %(row)d]." % {'col': col_idx, 'row': row_idx}
                raise WordException(tmp)
            return True

    def _internal_set_table_data(self, tbl_obj, col_cnt, row_cnt, data):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        else:
            for row in range(row_cnt):
                for col in range(col_cnt):
                    if self._internal_set_table_cell_value(tbl_obj, col + 1, row + 1, data[row][col]) is False:
                        return False
            return True

    def _internal_get_hyperlink(self, hyperlink_idx):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        else:
            try:
                hyperlink_obj = self._document.Hyperlinks.Item(hyperlink_idx)
            except:
                tmp = "The hyperlink with the specified index does not exist or error occured while accesing it."
                raise WordException(tmp)
        return hyperlink_obj

    def _internal_resize_table(self, tbl_idx, new_col_cnt, new_row_cnt):
        """TODO
        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_dim = self.get_table_dimensions(tbl_idx)
        tbl_row_cnt = tbl_dim[0]
        tbl_col_cnt = tbl_dim[1]
        try:
            if tbl_row_cnt < new_row_cnt:
                for _ in range(new_row_cnt - tbl_row_cnt):
                    tbl_obj.Rows.Add()
            if tbl_col_cnt < new_col_cnt:
                for _ in range(new_col_cnt - tbl_col_cnt):
                    tbl_obj.Columns.Add()
        except:
            raise WordException("Failed to resize table.")

    @staticmethod
    def _internal_alignment_to_string(alignment_idx):
        """TODO
        """
        idx = 0
        for alignment_id in list(PARAGRAPH_ALINGMENT.values()):
            if alignment_id == alignment_idx:
                return list(PARAGRAPH_ALINGMENT.keys())[idx]
            else:
                idx += 1
        return "Unknown"

    def _internal_get_shape_by_id(self, shape_id):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        shape_cnt = self.get_shapes_count()
        shape_cnt += 1
        try:
            for shape_idx in range(1, shape_cnt + 1):
                shape_obj = self._document.Shapes.Item(shape_idx)
                if shape_obj.ID == shape_id:
                    return shape_obj
            # else:
            return None
        except:
            tmp = "An error occured while searching document for shape with ID %(id_str)s" % {'id_str': shape_id}
            raise WordException(tmp)

    def _internal_get_shape_by_idx(self, shape_idx):
        """TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        try:
            return self._document.Shapes.Item(shape_idx)
        except:
            tmp = "An error occured while searching document for shape with index %(idx)d ." % {'idx': shape_idx}
            raise WordException(tmp)

    def _internal_get_shape(self, shape_idx):
        """TODO
        """
        if isinstance(shape_idx, str):
            return self._internal_get_shape_by_id(shape_idx)
        else:
            return self._internal_get_shape_by_idx(shape_idx)

    @staticmethod
    def _internal_font_color_to_string(font_color):
        """TODO
        """
        idx = 0
        for color in list(FONT_COLOR.values()):
            if color == font_color:
                return list(FONT_COLOR.keys())[idx]
            else:
                idx += 1
        return "Unknown"

    @staticmethod
    def _internal_bkrnd_color_to_string(bkrnd_color):
        """TODO
        """
        idx = 0
        for color in list(BACKROUND_COLOR.values()):
            if color == bkrnd_color:
                return list(BACKROUND_COLOR.keys())[idx]
            else:
                idx += 1
        return "Unknown"

    def _internal_get_paragraph(self, paragraph_idx):
        """TODO
        """
        if self._document is None:
            raise WordException("No document currently opened.")
        if isinstance(paragraph_idx, str):
            return self._internal_get_paragraph_by_id(paragraph_idx)
        else:
            return self._internal_get_paragraph_by_idx(paragraph_idx)

    def _internal_get_paragraph_by_idx(self, paragraph_idx):
        """TODO
        """
        if self._document is None:
            raise WordException("No document currently opened.")
        else:
            try:
                paragraph = self._document.Paragraphs.Item(paragraph_idx)
            except:
                tmp = "The specified index does not exist or an error occured "
                tmp += "while attempting to access paragraph "
                tmp += "%(paragraph_index)d." % {'paragraph_index': paragraph_idx}
                raise WordException(tmp)
        return paragraph

    def _internal_get_paragraph_by_id(self, paragraph_id):
        """TODO
        """
        if self._document is None:
            raise WordException("No document currently opened.")
        else:
            try:
                paragraph_cnt = self.get_paragraphs_count()
                paragraph_cnt += 1
                for paragraph_idx in range(1, paragraph_cnt + 1):
                    paragraph_obj = self._internal_get_paragraph(paragraph_idx)
                    if paragraph_obj.ID == paragraph_id:
                        return paragraph_obj
                # else:
                raise WordException("A paragraph with the specified ID does not exist.")
            except:
                tmp = "The specified ID does not exist or an error occured "
                tmp += "while attempting to access paragraph with ID "
                tmp += "%(paragraph_id)s." % {'paragraph_id': paragraph_id}
                raise WordException(tmp)

#   def _internal_get_shape_by_id(self,shape_id):
#       if self._document is None:
#           raise WordException("No document currently opened.")
#       else:
#           try:
#               shapes_cnt = self.get_shapes_count()
#               for idx in range(1,shapes_cnt+1):
#                   if self._document.Shapes.Item(idx).ID==shape_id:
#                       return self._document.Shapes.Item(idx)
#
#           except:
#                raise WordException("An error occured while getting shape.")
#       return None

    def set_table_cell_font_size(self, tbl_idx, col_idx, row_idx, font_size):
        """Function sets the size font for a table cell.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param row_idx: The index of the row .
        :param font_size: The size of the font.

        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            tbl_cell.Range.Font.Size = font_size
        except:
            raise WordException("Failed to set cell font.")

    def get_table_cell_font_size(self, tbl_idx, col_idx, row_idx):
        """Function returns the size font for a table cell.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param row_idx: The index of the row .

        :return: The size of the font for the specified table cell.
       """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            return tbl_cell.Range.Font.Size
        except:
            raise WordException("Failed to get cell font.")

    def set_table_cell_font(self, tbl_idx, col_idx, row_idx, font):
        """Function sets the font for a table cell.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param row_idx: The index of the row .
        :param font:    The new font for the cell.

        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            tbl_cell.Range.Font.Name = font
        except:
            raise WordException("Failed to set table cell font.")

    def get_table_cell_font(self, tbl_idx, col_idx, row_idx):
        """Function returns the font for a table cell.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param row_idx: The index of the row .
        :return:        The name of the font for the specified table cell.
        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            return tbl_cell.Range.Font.Name
        except:
            raise WordException("Failed to get table cell font.")

    def set_table_cell_color(self, tbl_idx, col_idx, row_idx, color):
        """Function sets the backround color for a table cell.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param row_idx: The index of the row .
        :param color:   The new backround color for the table cell as string.

        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            tbl_cell.Range.Shading.BackgroundPatternColor = BACKROUND_COLOR[color]
        except:
            raise WordException("Failed to set cell font color.")

    def get_table_cell_color(self, tbl_idx, col_idx, row_idx):
        """Function returns the backround color for a table cell.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param row_idx: The index of the row .
        :return:   The  backround color for the table cell as string.
        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            return self._internal_bkrnd_color_to_string(tbl_cell.Range.Shading.BackgroundPatternColor)
        except:
            raise WordException("Failed to get cell font color.")

    def set_table_cell_font_color(self, tbl_idx, col_idx, row_idx, font_color):
        """
        Function sets the font color for a table cell.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param row_idx: The index of the row .
        :param font_color:   The new font color for the table cell as string.
        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            tbl_cell.Range.Font.Color = FONT_COLOR[font_color]
        except:
            raise WordException("Failed to set cell font color.")

    def get_table_cell_font_color(self, tbl_idx, col_idx, row_idx):
        """
        Function returns the font color for a table cell.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param row_idx: The index of the row .
        :return:        The font color for the table cell as string.
        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            return self._internal_font_color_to_string(tbl_cell.Range.Font.Color)
        except:
            raise WordException("Failed to get cell font color.")

    def set_table_row_style(self, tbl_idx, row_idx, bold=False, italic=False, underline=False, alignment='Left'):
        """
        Function sets the style for all the cells on the specified row.

        :param tbl_idx: Table index or table id.
        :param row_idx: The index of the row .
        :param bold:    Specifies if the text in the table cell will be bold or not. By default set to False.
        :param italic:  Specifies if the text in the table cell will be italic or not.By default set to False.
        :param underline: Specifies if the text in the table cell will be underlined or not.By default set to False.
        :param alignment: TODO
        """
        tbl_obj = self._internal_get_table(tbl_idx)
        row_cnt, col_cnt = self.get_table_dimensions(tbl_idx)
        try:
            for col_idx in range(1, col_cnt + 1):
                tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
                if bold is True:
                    tbl_cell.Range.Font.Bold = True
                else:
                    tbl_cell.Range.Font.Bold = False
                if italic is True:
                    tbl_cell.Range.Font.Italic = True
                else:
                    tbl_cell.Range.Font.Italic = False
                if underline is True:
                    tbl_cell.Range.Font.Underline = True
                else:
                    tbl_cell.Range.Font.Underline = False
                tbl_cell.Range.ParagraphFormat.Alignment = PARAGRAPH_ALINGMENT[alignment]
        except:
            raise WordException("Failed to set row style.")

    def set_table_column_style(self, tbl_idx, col_idx, alignment='Left', bold=False, italic=False, underline=False):
        """
        Function sets the style for all the cells on the specified row.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param alignment: The alignment of the text in the cells on the specified column.
        :param bold:    Specifies if the text in the table cell will be bold or not. By default set to False.
        :param italic:  Specifies if the text in the table cell will be italic or not.By default set to False.
        :param underline: Specifies if the text in the table cell will be underlined or not.By default set to False.

        """
        tbl_obj = self._internal_get_table(tbl_idx)
        row_cnt, col_cnt = self.get_table_dimensions(tbl_idx)
        try:
            for row_idx in range(1, row_cnt + 1):
                tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
                if bold is True:
                    tbl_cell.Range.Font.Bold = True
                else:
                    tbl_cell.Range.Font.Bold = False
                if italic is True:
                    tbl_cell.Range.Font.Italic = True
                else:
                    tbl_cell.Range.Font.Italic = False
                if underline is True:
                    tbl_cell.Range.Font.Underline = True
                else:
                    tbl_cell.Range.Font.Underline = False
                tbl_cell.Range.ParagraphFormat.Alignment = PARAGRAPH_ALINGMENT[alignment]
        except:
            raise WordException("Failed to set column style.")

    def set_table_cell_style(self, tbl_idx, col_idx, row_idx, bold=False,
                             italic=False, underline=False, alignment='Left'):
        """Function sets the style for  the specified cell.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param row_idx: The index of the row.
        :param bold:    Specifies if the text in the table cell will be bold or not. By default set to False.
        :param italic:  Specifies if the text in the table cell will be italic or not.By default set to False.
        :param underline: Specifies if the text in the table cell will be underlined or not.By default set to False.
        :param alignment: The alignment of the text in the cells on the
                          specified column.By default set to ALIGNMENT_HORIZAONTAL_LEFT.

        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            if bold is True:
                tbl_cell.Range.Font.Bold = True
            else:
                tbl_cell.Range.Font.Bold = False
            if italic is True:
                tbl_cell.Range.Font.Italic = True
            else:
                tbl_cell.Range.Font.Italic = False
            if underline is True:
                tbl_cell.Range.Font.Underline = True
            else:
                tbl_cell.Range.Font.Underline = False
            tbl_cell.Range.ParagraphFormat.Alignment = PARAGRAPH_ALINGMENT[alignment]
        except:
            raise WordException("Failed to set cell font style.")

    def get_table_cell_style(self, tbl_idx, col_idx, row_idx):
        """Function returns the style for  the specified cell.

        :param tbl_idx: Table index or table id.
        :param col_idx: The index of the column .
        :param row_idx: The index of the row.
        :return:  A tuple with the style of the table cell.

        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            if tbl_cell.Range.Font.Italic != 0:
                bitalic = True
            else:
                bitalic = False
            if tbl_cell.Range.Font.Bold != 0:
                bbold = True
            else:
                bbold = False
            if tbl_cell.Range.Font.Underline != 0:
                bunderline = True
            else:
                bunderline = False
            salignment = self._internal_alignment_to_string(tbl_cell.Range.ParagraphFormat.Alignment)
            return bbold, bitalic, bunderline, salignment
        except:
            raise WordException("Failed to get cell font style.")

    def remove_table(self, tbl_idx):
        """Function removes the specified table from the document.

        :param tbl_idx: Table index or table id.
        """
        if self._document is None:
            raise WordException("No document currently opened.")
        try:
            tbl_obj = self._internal_get_table(tbl_idx)
            tbl_obj.Delete()
        except:
            raise WordException("An error occured while removing table.")

    def get_table_dimensions(self, tbl_idx):
        """Function returns the size of the specified table.

        :param tbl_idx: Table index or table id.
        :return:  A list with the number of rows and number of columns.
                  If the table has a different number of cells or a row the maximum number will be returned.

        """
        tbl_obj = self._internal_get_table(tbl_idx)
        try:
            return [tbl_obj.Rows.Count, tbl_obj.Columns.Count]
        except:
            WordException("Failed to get table dimensions.")

    def resize_table(self, tbl_idx, new_col_cnt, new_row_cnt):
        """Function resizes the specified table to the new dimension.The table can only grow.

        :param tbl_idx: Table index or table id.
        :param new_col_cnt: The new number of columns for the table.
        :param new_row_cnt: The new number of rows for the table.

        """
        return self._internal_resize_table(tbl_idx, new_col_cnt, new_row_cnt)

    def set_table_cell_data(self, tbl_idx, row_idx, col_idx, tbl_data, Force=False):
        """Function sets the text for the specified table cell.

        :param tbl_idx: Table index or table id.
        :param row_idx: The index of the row that contains the cell.
        :param col_idx: The index of the column that contains the cell.
        :param tbl_data: The new cell text.
        :param Force:    Makes it posible to access tables that have rows with different number of cells.
                         By default set to False(assuming all the rows have the same number of cells.)
                         By setting to True disables check of the row and column indexes vs dimensions of the table.
        :return:  A list with the number of rows and number of columns.
                  If the table has a different number of cells or a row the maximum number will be returned.

        """
        tbl_obj = self._internal_get_table(tbl_idx)
        # Check if the specified cell is in the table dimensions(Default).
        # Word returns a cell can return a cell even is the index is out of bound.
        # It is also posible that the table does not have the same number of columns for each row.
        if Force is False:
            tbl_dim = self.get_table_dimensions(tbl_idx)
            if row_idx not in range(1, tbl_dim[0] + 1) or col_idx not in range(1, tbl_dim[1] + 1):
                raise WordException("The specified table cell is not within table bounds.")
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            tbl_cell.Range.Text = tbl_data
        except:
            raise WordException("Failed to set table cell data.")

    def get_table_cell_data(self, tbl_idx, row_idx, col_idx):
        """Function returns the text for the specified table cell.

        :param tbl_idx: Table index or table id.
        :param row_idx: The index of the row that contains the cell.
        :param col_idx: The index of the column that contains the cell.
        :return:   The text contained in the specified table cell as a str.

        """
        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            return str(tbl_cell.Range.Text).rstrip('\r\007')
        except:
            raise WordException("Failed to set table cell data.")

    def set_table_data(self, tbl_idx, tbl_data):
        """Function sets the data for the entire table.

        :param tbl_idx: Table index or table id.
        :param tbl_data: The new data for the entire table.
                         The size of the data must match the size of the table
                         if not the table will be automatically resized.

        """
        if len(tbl_data) == 0:
            pass

        tbl_obj = self._internal_get_table(tbl_idx)
        tbl_dim = self.get_table_dimensions(tbl_idx)
        tbl_row_cnt = tbl_dim[0]
        tbl_col_cnt = tbl_dim[1]

        data_row_cnt = len(tbl_data)
        data_col_cnt = len(tbl_data[0])

        if tbl_row_cnt == 0 or tbl_col_cnt == 0 or len(tbl_data) == 0:
            self._internal_resize_table(tbl_idx, data_col_cnt, data_row_cnt)
            self._internal_set_table_data(tbl_obj, data_col_cnt, data_row_cnt, tbl_data)
        else:
            data_row_cnt = len(tbl_data)
            data_col_cnt = len(tbl_data[0])
            if tbl_row_cnt != data_row_cnt or tbl_col_cnt != data_col_cnt:
                # Resize the table and set the data or not
                self._internal_resize_table(tbl_idx, data_col_cnt, data_row_cnt)
                self._internal_set_table_data(tbl_obj, data_col_cnt, data_row_cnt, tbl_data)
            else:
                self._internal_set_table_data(tbl_obj, data_col_cnt, data_row_cnt, tbl_data)

    def get_table_data(self, table_idx):
        """Function returns the data for the entire table.

        :param table_idx: Table index or table id.
        :return: A list containing aditional lists for each row.
                 Each value in the list represents a different cell.
        """
        cells = []
        tbl_obj = self._internal_get_table(table_idx)
        try:
            row_cnt = tbl_obj.Rows.Count
        except:
            raise WordException("Failed to get table rows count.")
        for row in range(1, row_cnt + 1):
            row_cells = []
            tbl_row_obj = self._internal_get_table_row(tbl_obj, row)
            try:
                col_cnt = tbl_row_obj.Cells.Count
            except:
                raise WordException("Failed to get number of cells for the table row %(row_id)%" % {'row_id': row})
            for col in range(1, col_cnt + 1):
                row_cells.append(self._internal_get_table_cell_value(tbl_obj, row, col))
            cells.append(row_cells)
        return cells

    def set_paragraph_font_size(self, paragraph_idx, font_size):
        """Function sets the font size for the specified paragraph.

        :param paragraph_idx: Paragraph index or Paragraph id.
        :param font_size:     The new size for the font in the paragraph.
        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            paragraph_obj.Range.Font.Size = font_size
        except:
            raise WordException("Failed to set paragraph font size.")

    def get_paragraph_font_size(self, paragraph_idx):
        """
        Function returns the font size for the specified paragraph.

        :param paragraph_idx: Paragraph index or Paragraph id.
        :return: The font size for the specified paragraph.
        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            return paragraph_obj.Range.Font.Size
        except:
            raise WordException("Failed to get paragraph font size.")

    def set_paragraph_font_color(self, paragraph_idx, font_color):
        """
        Function sets the font color for the specified paragraph.

        :param paragraph_idx: Paragraph index or Paragraph id.
        :param font_color: The new font color for the specified paragraph.
        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            paragraph_obj.Range.Font.Color = FONT_COLOR[font_color]
        except:
            raise WordException("Failed to set paragraph font color.")

    def get_paragraph_font_color(self, paragraph_idx):
        """Function returns the font color for the specified paragraph.

        :param paragraph_idx: Paragraph index or Paragraph id.
        :return: The font color for the specified paragraph.

       """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            return self._internal_font_color_to_string(paragraph_obj.Range.Font.Color)
        except:
            raise WordException("Failed to get paragraph font color.")

    def remove_paragraph(self, paragraph_idx):
        """Function removes the speicified paragraph.

         :param paragraph_idx: Paragraph index or Paragraph id.

        """
        if self._document is None:
            raise WordException("No document currently opened.")
        try:
            self._document.Paragraphs.Remove(paragraph_idx)
        except:
            raise WordException("An error occured while removing table.")

    def set_paragraph_ident(self, paragraph_idx, ident_size):
        """Function sets the identation for the specified paragraph.

         :param paragraph_idx: Paragraph index or Paragraph id.
         :param ident_size:    Identation size.

        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            paragraph_obj.IndentFirstLineCharWidth(ident_size)
        except:
            raise WordException("An error occured while setting paragraph identation.")

    def get_paragraph_ident(self, paragraph_idx):
        """Function returns the identation for the speicified paragraph.

         :param paragraph_idx: Paragraph index or Paragraph id.
         :return:    Identation size.

        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            return paragraph_obj.IndentFirstLine
        except:
            raise WordException("An error occured while getting paragraph identation.")

    def set_paragraph_font(self, paragraph_idx, font_name):
        """Function sets the font for the specified paragraph.

         :param paragraph_idx: Paragraph index or Paragraph id.
         :param font_name: The name of the font for the paragraph.

        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            paragraph_obj.Range.Font.Name = font_name
        except:
            raise WordException("Failed to set paragraph font.")

    def set_paragraph_heading_style(self, paragraph_idx, level):
        """
        Function sets the level of the specified paragraph to a heading .

        :param paragraph_idx: The paragraph index or the ID string.
        :param level: The new text for the paragraph.
        """

        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            paragraph_obj.Range.Select()
            sel = self._app.Selection

            if level == 1:
                sel.Style = wc.constants.wdStyleHeading1
            elif level == 2:
                sel.Style = wc.constants.wdStyleHeading2
            elif level == 3:
                sel.Style = wc.constants.wdStyleHeading3
            elif level == 4:
                sel.Style = wc.constants.wdStyleHeading4
            elif level == 5:
                sel.Style = wc.constants.wdStyleHeading5
        except:
            raise WordException("Failed to set paragraph to header style.")

    def set_paragraph_style(self, paragraph_idx, bold=False, italic=False, underline=False, alignment='Left'):
        """Function sets the style for the specified paragraph.

        :param paragraph_idx: Paragraph index or Paragraph id.
        :param bold:  Flag to specify if the text should be set to bold. By default set to False.
        :param italic: Flag to specify if the text should be italic. By default set to False.
        :param underline: Flag to specify if the text should be underline. By default set to False.
        :param alignment: The alignment for the paragraph as a string. By default set to ALIGNMENT_HORIZAONTAL_LEFT.
        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            if bold is True:
                paragraph_obj.Range.Font.Bold = True
            else:
                paragraph_obj.Range.Font.Bold = False
            if italic is True:
                paragraph_obj.Range.Font.Italic = True
            else:
                paragraph_obj.Range.Font.Italic = False
            if underline is True:
                paragraph_obj.Range.Font.Underline = True
            else:
                paragraph_obj.Range.Font.Underline = False
            paragraph_obj.Alignment = PARAGRAPH_ALINGMENT[alignment]
        except:
            raise WordException("Failed to set paragraph style.")

    def get_paragraph_style(self, paragraph_idx):
        """Function returns the style for the specified paragraph.

        :param paragraph_idx: TODO
        :return: A list with the style. The order is the same as for SetParagraphStyle.
        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            salignment = self._internal_alignment_to_string(paragraph_obj.Alignment)
            if paragraph_obj.Range.Font.Bold != 0:
                bbold = True
            else:
                bbold = False
            if paragraph_obj.Range.Font.Italic != 0:
                bitalic = True
            else:
                bitalic = False
            if paragraph_obj.Range.Font.Underline != 0:
                bunderline = True
            else:
                bunderline = False
            return [bbold, bitalic, bunderline, salignment]
        except:
            raise WordException("Failed to get paragraph style.")

    def get_tables_count(self):
        """Function returns the number of tables in the document.

        :return: The number of tables in the document currently opened.
        """
        if self._document is None:
            raise WordException("No document currently opened.")
        try:
            tbl_count = self._document.Tables.Count
        except:
            raise WordException("Failed to get the tables count.")
        return tbl_count

    def get_paragraphs_count(self):
        """Function returns the number of paragraphs in the document.

        :return: The number of paragraphs in the document currently opened.
        """
        if self._document is None:
            raise WordException("No document currently opened.")
        else:
            try:
                paragraphs_count = self._document.Paragraphs.Count
            except:
                raise WordException("Failed to get the number of paragraphs in the document.")
        return paragraphs_count

    def set_paragraph_id(self, paragraph_idx, id_str):
        """Function sets an aditional string ID which can be used to identify a paragraph.

        :param paragraph_idx: The index of the paragraph.
        :param id_str: A string which will be used to identify the paragraph.
        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            paragraph_obj.ID = id_str
        except:
            raise WordException("Failed to set paragraph ID.")

    def get_paragraph_id(self, paragraph_idx):
        """Function returns the string ID.

        :param paragraph_idx: The index of the paragraph.
        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            paragraph_id = paragraph_obj.ID
        except:
            raise WordException("Failed to get paragraph ID.")
        return paragraph_id

    def set_paragraph_text(self, paragraph_idx, text):
        """
        Function sets the text in the specified paragraph.

        :param paragraph_idx: The paragraph index or the ID string.
        :param text: The new text for the paragraph.
        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            paragraph_obj.Range.Text = text
        except:
            raise WordException("Failed to set paragraph text.")

    def get_paragraph_text(self, paragraph_idx):
        """Function returns the text in the specified paragraph.

        :param paragraph_idx: The paragraph index or the ID string.
        :return: The text in the paragraph.
        """
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            return paragraph_obj.Range.Text
        except:
            raise WordException("Failed to get paragraph text.")

    def set_paragraph_hyperlink(self, paragraph_idx, hyperlink_text="", hyperlink_address="", hyperlink_screen_tip=""):
        """
        Function inserts a hyperlink in the specified paragraph.

        :param paragraph_idx:  The paragraph index or the ID string.
        :param hyperlink_text: The text for the hyperlink.
        :param hyperlink_address: The address for the hyperlink.
        :param hyperlink_screen_tip: The tooptip text displayed over the hyperlink.
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            self._document.Hyperlinks.Add(paragraph_obj.Range,
                                          hyperlink_address,
                                          "",
                                          hyperlink_screen_tip,
                                          hyperlink_text)
        except:
            raise WordException("Failed to add hyperlink to paragraph.")

    def set_table_cell_hyperlink(self, table_idx, row_idx, col_idx,
                                 hyperlink_text, hyperlink_address, hyperlink_screen_tip):
        """Function inserts a hyperlink in the specified table cell.

        :param table_idx:  The table index or the ID string.
        :param row_idx:  The index of the row on which the cell is situated.
        :param col_idx:  The index of the column on which the cell is situated.
        :param hyperlink_text: The text for the hyperlink.
        :param hyperlink_address: The address for the hyperlink.
        :param hyperlink_screen_tip: The tooptip text displayed over the hyperlink.
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        tbl_obj = self._internal_get_table(table_idx)
        cell = self._internal_get_table_cell(tbl_obj, row_idx, col_idx)
        try:
            self._document.Hyperlinks.Add(cell.Range, hyperlink_address, "", hyperlink_screen_tip, hyperlink_text)
        except:
            raise WordException("Failed to add hyperlink to paragraph.")

    def get_hyperlinks_count(self):
        """
        Function returns the number of hyperlinks in the document.

         :return: The number of hyperlinks in the document.
        """
        if self._document is None:
            raise WordException("Failed to get hyperlinks count.No document is opened.")
        else:
            try:
                hyperlinks_count = self._document.Hyperlinks.Count
            except:
                raise WordException("Failed to get the hyperlinks count in the current document.")
        return hyperlinks_count

    def set_hyperlink_display_text(self, hyperlink_idx, hyperlink_text):
        """Function sets the display text for the specified hyperlink.

         :param hyperlink_idx: The index of the hyperlink.
         :param hyperlink_text: The new text for the hyperlink.
        """
        hyperlink_obj = self._internal_get_hyperlink(hyperlink_idx)
        try:
            hyperlink_obj.TextToDisplay = hyperlink_text
        except:
            raise WordException("Failed to set hyperlink text.")

    def get_hyperlink_display_text(self, hyperlink_idx):
        """Function returns the display text for the specified hyperlink.

         :param hyperlink_idx: The index of the hyperlink.
         :return: The display text for the hyperlink.
        """
        hyperlink_obj = self._internal_get_hyperlink(hyperlink_idx)
        try:
            hyperlink_text = hyperlink_obj.TextToDisplay
        except:
            raise WordException("Failed to get hyperlink text.")
        return hyperlink_text

    def set_hyperlink_address_text(self, hyperlink_idx, hyperlink_address):
        """Function sets the address for the specified hyperlink.

         :param hyperlink_idx: The index of the hyperlink.
         :param hyperlink_address: The new address for the hyperlink.
        """
        hyperlink_obj = self._internal_get_hyperlink(hyperlink_idx)
        try:
            hyperlink_obj.Address = hyperlink_address
        except:
            raise WordException("Failed to set hyperlink address.")

    def get_hyperlink_address_text(self, hyperlink_idx):
        """Function returns the address for the specified hyperlink.

         :param hyperlink_idx: The index of the hyperlink.
         :return :The address for the specified hyperlink.
        """
        hyperlink_obj = self._internal_get_hyperlink(hyperlink_idx)
        try:
            hyperlink_address = hyperlink_obj.Address
        except:
            raise WordException("Failed to get hyperlink address.")
        return hyperlink_address

    def set_hyperlink_screen_tip(self, hyperlink_idx, hyperlink_screen_tip):
        """Function sets the screen for the specified hyperlink.

         :param hyperlink_idx: The index of the hyperlink.
         :param hyperlink_screen_tip: The new screen tip for the hyperlink.
        """
        hyperlink_obj = self._internal_get_hyperlink(hyperlink_idx)
        try:
            hyperlink_obj.ScreenTip = hyperlink_screen_tip
        except:
            raise WordException("Failed to set hyperlink screent tip.")

    def get_hyperlink_screen_tip(self, hyperlink_idx):
        """Function returns the screen for the specified hyperlink.

         :param hyperlink_idx: The index of the hyperlink.
         :return: The screen tip for the hyperlink.
        """
        hyperlink_obj = self._internal_get_hyperlink(hyperlink_idx)
        try:
            hyperlink_screen_tip = hyperlink_obj.ScreenTip
        except:
            raise WordException("Failed to get hyperlink screen tip.")
        return hyperlink_screen_tip

    def update_table_of_contents(self, tbl_toc_idx):
        """Function updates the specified table of contents.

        :param tbl_toc_idx:
        """
        tbl_toc_obj = self._internal_get_toc(tbl_toc_idx)
        try:
            tbl_toc_obj.Update()
        except:
            raise WordException("Failed to update table of contents.")

    def get_table_of_contents_count(self):
        """Function returns the number of tables of contents.

         :return: The number of tables of contents.
        """
        if self._document is None:
            raise WordException("No document is currently opened.")
        else:
            try:
                toc_count = self._document.TablesOfContents.Count
            except:
                raise WordException("Failed to get tables of contents count for the current document.")
        return toc_count

    def hide_word_application(self):
        """Function hides the WinWord application."""
        if self._app is None:
            raise WordException("Initialization error.")
        try:
            self._app.Visible = False
        except:
            raise WordException("Failed to hide Word window.")

    def show_word_application(self):
        """Function shows the WinWord application."""
        if self._app is None:
            raise WordException("Initialization error.")
        try:
            self._app.Visible = True
        except:
            raise WordException("Failed to show Word window.")

    def hide_current_document(self):
        """Function hides the document currenltly opened."""
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        try:
            self._document.Visible = False
        except:
            raise WordException("Failed to hide the current document.")

    def show_current_document(self):
        """Function shows the current document."""
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        try:
            self._document.Visible = True
        except:
            raise WordException("Failed to show the current document.")

    def table_id_to_index(self, id_str):
        """Function returns the index of the table which has the specified ID string.

         :param id_str: The ID string that indetifies a table.
         :return: The index of the table with the ID string.
        """
        tbl_count = self.get_tables_count()
        for tbl_idx in range(1, tbl_count + 1):
            if self._internal_get_table(tbl_idx).ID == id_str:
                return tbl_idx
        # else:
        return -1

    def insert_table(self, paragraph_idx, row_count, col_count, tbl_id_str='', autofit_behavior='AutoFitContent'):
        """Function inserts a new table in the document.

         :param paragraph_idx: The index or ID string of a paragraph. The new table will be inserted in the paragraph.
         :param row_count:  The number of rows for the new table.
         :param col_count:  The number of columns for the new table.
         :param tbl_id_str: An string which can be used to identify the table. By default set to ''
         :param autofit_behavior: The autofit behavior of the table as a string.
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            tbl_obj = self._document.Tables.Add(paragraph_obj.Range, row_count, col_count,
                                                1, AUTOFIT_BEHAVIOR[autofit_behavior])
            tbl_obj.ID = tbl_id_str
            return self.get_tables_count()
        except:
            raise WordException("Failed to add new paragraph in the document.")

    def insert_paragraph_at_end(self):
        """Function inserts a new paragraph at the end of the document.

         :return: The number of paragraphs in the document.
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        try:
            self._document.Paragraphs.Add()
        except:
            raise WordException("Failed to add new paragraph in the document.")
        return self.get_paragraphs_count()

    def insert_paragraph(self, paragraph_idx):
        """Function inserts a new paragraph before the specified paragraph.

         :param paragraph_idx: TODO
         :return: The number of paragraphs in the document.
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        paragraph_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            self._document.Paragraphs.Add(paragraph_obj.Range)
        except:
            raise WordException("Failed to add new paragraph in the document.")
        return self.get_paragraphs_count()

    def add_picture_shape(self, file_name, paragraph_idx=None, orientation='Horizontal'):
        """
        Function inserts a new paragraph at the end of the document.

        :param file_name: The file path to picture to be inserted.
        :param paragraph_idx: The paragraph which is used as an anchor.
                              The picture shape will be inserted at the begining of the paragraph.
        :param orientation: TODO
        :return: The new shape ID.
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        if len(file_name) == 0:
            raise WordException("No picture document specified.")
        else:
            if exists(file_name) is False:
                raise WordException("The specified path does not exist.(%(path)s)" % {'path': file_name})

        anchor_obj = None
        if paragraph_idx is not None:
            anchor_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            if anchor_obj is None:
                shape_obj = self._document.Shapes.AddPicture(file_name, False, True)
            else:
                shape_obj = self._document.Shapes.AddPicture(file_name, False, True, anchor_obj)
            if shape_obj is not None:
                return shape_obj.ID
        except:
            raise WordException("Failed to add picture to the document.")

    def get_shape_size(self, pic_shape_id):
        """Function returns the size of the specified shape.

          :param pic_shape_id: The id of the shape for which the dimensions are needed.
          :return: A list with the dimensions of the picture shape. The list members are heigh,width,left,top.
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        try:
            shape = self._internal_get_shape_by_id(pic_shape_id)
            if shape is None:
                raise WordException("A shape with the specified ID does not exist.")
            else:
                return {'Height': shape.Height, 'Width': shape.Width, 'Left': shape.Left, 'Top': shape.Top}
        except:
            raise WordException("The picture with the specified id does not exist.")

    @staticmethod
    def add_diagram_shape():
        """Function returns the size of the specified shape.
        """
        raise WordException("Not implemented.")

    @staticmethod
    def add_polyline_shape(x_values, y_values, paragraph_idx=None, orientation='Horizontal'):
        raise WordException("Not implemented.")

#         if self.is_document_opened() is False:
#             raise WordException("No document currently opened.")
#         # if not isinstance(x_value,list) or not isinstance(y_values,list):
#         #   raise WordException("Expecting type list for x_values or y_values parameters.")
#         if len(x_values) != len(y_values):
#             raise WordException("The number of values for x_values must be equal to y_values.")
#         anchor_obj = None
#         if paragraph_idx is not None:
#             anchor_obj = self._internal_get_paragraph(paragraph_idx)
#         # try:
#         shape_obj = None
#         x_values += y_values
#
#         if anchor_obj is None:
#             shape_obj = self._document.Shapes.AddPolyline(x_values)
#         else:
#             shape_obj = self._document.Shapes.AddPolyline(x_values + y_values, anchor_obj)
#             if shape_obj is not None:
#                 return shape_obj.ID
#         # except:
#         #    raise WordException("Failed to add polyline to the document.")

    def add_label_shape(self, left, top, width, height, label_text="", paragraph_idx=None, orientation='Horizontal'):
        """
        Function adds a new label shape.

        :param left: The distance from the left side of the containing paragraph.
        :param top:  The distance from the top side of the containing paragraph.
        :param width: The width of the label shape.
        :param height: The height of the label shape.
        :param label_text: The text in the label shape.
        :param paragraph_idx: The index or ID of a paragraph which will be used as an anchor.
        :param orientation: The orientation of the label shape.
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        if left < 0 or top < 0 or width < 0 or height < 0:
            raise WordException("Coordinates and dimensions must be positive numbers.")
        anchor_obj = None
        if paragraph_idx is not None:
            anchor_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            if anchor_obj is None:
                shape_obj = self._document.Shapes.AddLabel(TEXT_ORIENTATION[orientation], left, top, width, height)
            else:
                shape_obj = self._document.Shapes.AddLabel(TEXT_ORIENTATION[orientation],
                                                           left, top, width, height, anchor_obj.Range)
            if shape_obj is not None:
                shape_obj.TextFrame.TextRange.Text = label_text
            return shape_obj.ID
        except:
            raise WordException("Failed to add label to the document.")

    def add_textbox_shape(self, left, top, width, height, textbox_text="",
                          paragraph_idx=None, orientation='Horizontal'):
        """
        Function adds a new text box shape.

        :param left: The distance from the left side of the containing paragraph.
        :param top:   The distance from the top side of the containing paragraph.
        :param width:  The width of the text box shape.
        :param height: The height of the text box shape.
        :param textbox_text: The text inside of the text box shape.
        :param paragraph_idx: An index or ID of a paragraph which will be used as an anchor for the text box shape.
        :param orientation: The orientation of the text box shape.
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        if left < 0 or top < 0 or height < 0 or height < 0:
            raise WordException("Coordinates and dimensions must be positive numbers.")
        anchor_obj = None
        if paragraph_idx is not None:
            anchor_obj = self._internal_get_paragraph(paragraph_idx)
        try:
            if anchor_obj is None:
                shape_obj = self._document.Shapes.AddTextbox(TEXT_ORIENTATION[orientation], left, top, width, height)
            else:
                shape_obj = self._document.Shapes.AddLabel(TEXT_ORIENTATION[orientation],
                                                           left, top, width, height, anchor_obj.Range)
            if shape_obj is not None:
                shape_obj.TextFrame.TextRange.Text = textbox_text
            return shape_obj.ID
        except:
            raise WordException("Failed to add textbox to the document.")

    def add_line_shape(self, x_start, y_start, x_end, y_end, paragraph_idx=None):
        """
        Function adds a new line shape.

        :param x_start: The start X coordinate for the line within the containing paragraph.
        :param y_start: The start Y coordinate for the line within the containing paragraph.
        :param x_end: The end X coordinate for the line within the containing paragraph.
        :param y_end: The end Y coordinate for the line within the containing paragraph.
        :param paragraph_idx: An index or ID of a paragraph which will be used as an anchor for the text box shape.
         """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        anchor_obj = None
        if paragraph_idx is not None:
            anchor_obj = self._internal_get_paragraph(paragraph_idx)
        if x_start < 0 or y_start < 0 or x_end < 0 or y_end < 0:
            raise WordException("Coordinates must be positive numbers.")
        try:
            if anchor_obj is None:
                shape_obj = self._document.Shapes.AddLine(x_start, y_start, x_end, y_end)
            else:
                shape_obj = self._document.Shapes.AddLine(x_start, y_start, x_end, y_end, anchor_obj.Range)
            if shape_obj is not None:
                return shape_obj.ID
        except:
            raise WordException("Failed to add label to the document.")

    def get_shapes_count(self):
        """
        Function returns the number of shapes in the document.

        :return: The number of shapes in the document.
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        try:
            return self._document.Shapes.Count
        except:
            raise WordException("Failed to get the number of shapes present in the document.")

    def close(self):
        """Function closes the document currently opened."""
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        del self._document
        self._document = None

    def save(self):
        """Function saves the document currently opened."""
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        try:
            self._document.Save()
        except:
            raise WordException("An exception occured while closing the document.")

    def save_as(self, filename):
        """Function saves the document currently opened to the specified path.

        :param filename: TODO
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        try:
            self._document.SaveAs(filename)
        except:
            raise WordException("An error occured while saving the document as %(doc_path)s" % {'doc_path': filename})

    def _check_hf_param(self, hf_param):
        """ Auxiliary function to perform some basic checks before dispatching the task to COM Word object
        :author: Alin Danciu
        """
        if self.is_document_opened() is False:
            raise WordException("No document currently opened.")
        if not (hf_param in [self.HEADER_FOOTER_EVEN_PAGES,
                             self.HEADER_FOOTER_FIRST_PAGE,
                             self.HEADER_FOOTER_PRIMARY]):
            raise WordException("Invalid header / footer type argument.")

    def get_section_header_text(self, section_idx, header_type):
        """ Gets the section header text
        :param section_idx: Index of the section to set the text for
        :param header_type: One of the constants stkWord.HEADER_FOOTER_EVEN_PAGES, stkWord.HEADER_FOOTER_FIRST_PAGE,
            stkWord.HEADER_FOOTER_PRIMARY
        :return: The text of header type of the specified section.
        :author: Alin Danciu
        """
        self._check_hf_param(header_type)
        try:
            return self._document.Sections[section_idx].Headers[header_type].Range.Text
        except IndexError:
            print ("Section index parameter out of range. Document contains " +
                   str(len(self._document.Sections)) + " sections.")
            raise IndexError("Invalid section index")
        except:
            raise WordException("An unknown error occurred while trying to get header info.")

    def get_section_footer_text(self, section_idx, footer_type):
        self._check_hf_param(footer_type)
        """ Gets the section footer text
        :param section_index: Index of the section to set the text for
        :param footer_type: One of the constants stkWord.HEADER_FOOTER_EVEN_PAGES, stkWord.HEADER_FOOTER_FIRST_PAGE,
            stkWord.HEADER_FOOTER_PRIMARY
        :return: The text of footer type of the specified section.
        :author: Alin Danciu
        """
        try:
            return self._document.Sections[section_idx].Footers[footer_type].Range.Text
        except IndexError:
            print ("Section index parameter out of range. Document contains " +
                   str(len(self._document.Sections)) + " sections.")
            raise IndexError("Invalid section index")
        except:
            raise WordException("An unknown error occurred while trying to get footer info.")

    def set_section_header_text(self, section_idx, header_type, text):
        """ Sets the section header text
        :param section_idx: Index of the section to set the text for
        :param header_type: One of the constants stkWord.HEADER_FOOTER_EVEN_PAGES, stkWord.HEADER_FOOTER_FIRST_PAGE,
            stkWord.HEADER_FOOTER_PRIMARY
        :param text: String that represents the text to be set.
        :author: Alin Danciu
        """
        self._check_hf_param(header_type)
        try:
            self._document.Sections[section_idx].Headers[header_type].Range.Text = text
        except IndexError:
            print ("Section index parameter out of range. Document contains " +
                   str(len(self._document.Sections)) + " sections.")
            raise IndexError("Invalid section index")
        except:
            raise WordException("An unknown error occurred while trying to set header info.")

    def set_section_footer_text(self, section_idx, footer_type, text):
        """ Sets the section footer text
        :param section_idx: Index of the section to set the text for
        :param footer_type: One of the constants stkWord.HEADER_FOOTER_EVEN_PAGES, stkWord.HEADER_FOOTER_FIRST_PAGE,
            stkWord.HEADER_FOOTER_PRIMARY
        :param text: String that represents the text to be set.
        :author: Alin Danciu
        """
        self._check_hf_param(footer_type)
        try:
            self._document.Sections[section_idx].Footers[footer_type].Range.Text = text
        except IndexError:
            print ("Section index parameter out of range. Document contains " +
                   str(len(self._document.Sections)) + " sections.")
            raise IndexError("Invalid section index")
        except:
            raise WordException("An unknown error occurred while trying to set footer info.")

    def add_section_page_number(self, section_idx, footer_type, page_number_alignment):
        """ Adds the page number to a section.
        :param section_idx: Index of the section to add the page number to
        :param footer_type: One of the constants stkWord.HEADER_FOOTER_EVEN_PAGES, stkWord.HEADER_FOOTER_FIRST_PAGE,
            stkWord.HEADER_FOOTER_PRIMARY
        :param page_number_alignment: One of the constants stkWord.PAGE_NUMBER_ALIGN_LEFT,
                                      stkWord.PAGE_NUMBER_ALIGN_CENTER, stkWord.PAGE_NUMBER_ALIGN_RIGHT
        :note: The parameters are checked and an exception is thrown in case of invalud parameters.
        :author: Alin Danciu
        """
        self._check_hf_param(footer_type)
        if not (page_number_alignment in [self.PAGE_NUMBER_ALIGN_LEFT,
                                          self.PAGE_NUMBER_ALIGN_CENTER,
                                          self.PAGE_NUMBER_ALIGN_RIGHT]):
            raise WordException("Invalid page number alignment argument.")
        try:
            self._document.Sections[section_idx].Footers[footer_type].PageNumbers.Add()
            self._document.Sections[section_idx].Footers[footer_type].PageNumbers[0].Alignment = page_number_alignment
        except IndexError:
            print ("Section index parameter out of range. Document contains " +
                   str(len(self._document.Sections)) + " sections.")
        except:
            raise WordException("An unknown error occurred while trying to add section page number.")

    def add_object_from_file(self, file_name, link_to_file, display_as_icon, icon_file_name,
                             icon_index, icon_label, range):
        """ Adds an object from a file to the current document
        :param file_name: The path of the file to store
        :param link_to_file: True in order to add just a link to the file,
                             False in order to add the contents of the file
        :param display_as_icon: True in order to display an icon in place of file
                                (that must be supplied as parameter), False
                                to embed the file into the document
        :param icon_file_name: The name of the file that supplies the icon,
                               can be ommited in case display_as_icon is set to False
        :param icon_index: The index of the icon to be used to display the added file, from the icon_file_name
        :param icon_label: Label of the icon used for the file
        :param range: Range object to add the file into
        :author: Alin Danciu
        """
        file_path = os.path.normpath(os.path.abspath(file_name))
        icon_file_path = os.path.normpath(os.path.abspath(icon_file_name))
        if os.path.exists(file_name):
            if display_as_icon:
                if os.path.exists(icon_file_name) and icon_index >= 0:
                    self._document.InlineShapes.AddOLEObject(ClassType="Package",
                                                             FileName=file_path,
                                                             LinkToFile=link_to_file,
                                                             DisplayAsIcon=display_as_icon,
                                                             IconFileName=icon_file_path,
                                                             IconIndex=icon_index,
                                                             IconLabel=icon_label,
                                                             Range=range)
                else:
                    raise WordException("Display as icon option selected but no icon file found.")
            else:
                self._document.InlineShapes.AddOLEObject(FileName=file_path,
                                                         LinkToFile=link_to_file,
                                                         DisplayAsIcon=display_as_icon,
                                                         Range=range)
        else:
            raise WordException("File not found.")

    def delete_inline_shape(self, shape_index):
        """
        Deletes the shape with the given index and returns its empty range index
        :param shape_index: index of the shape to be deleted
        :return: the range of the shape or None in case the delete operation was unsuccessful
        :author: Alin Danciu
        """
        try:
            result = self._document.InlineShapes[shape_index].Range
            result.Delete()
            return result
        except IndexError:
            print ("Shape index parameter out of range. Document contains " +
                   str(self._document.InlineShapes.Count) + " inline shapes.")
            return None
        except Exception, errmsg:
            raise WordException("Unable to delete Inline shape due to %s." % errmsg)

    def get_inline_shape_index(self, start_index, stype):
        """ Returns the first inline shape of the given type

        :param start_index: the start index to begin search from
        :param stype: type of the object as integer (@synonim WdInlineShapeType Enumeration)
        :return: the index of the first object that is of the type or -1 if no such object is found
        :author: Alin Danciu
        """
        index = start_index
        found = False
        while (not found) and (index < self._document.InlineShapes.Count):
            obj = self._document.InlineShapes[index]
            result = index
            if obj.Type == stype:
                found = True
            index += 1
        if not found:
            result = -1
        return result

    def find_range(self, text):
        """ Returns the first range that correponds to the give text

        :param text: The text (single word) to search for
        :return: The range object that corresponds to the first occurence of
        the search string or None in case the string is not found in the current
        opened document.
        :author: Alin Danciu
        """
        result = None
        words = self._document.Words
        for word in words:
            if word is None:
                continue
            if word.Text == text:
                result = word
                break
        return result

    def select_range(self, idx=-1, text="", rtype=-1):
        """ Returns a range based on a given criteria.
        :param idx: The index of the paragraph's range
        :param text: The first range that contains the text (by exact match, unformatted)
        :param rtype: type of the object as integer (@synonym WdInlineShapeType Enumeration)
        :return: The range in case of success, None otherwise
        :author: Alin Danciu
        """
        if idx > 0:
            return self._internal_get_paragraph(idx).Range
        elif text != "":
            return self.find_range(text)
        elif rtype > 0:
            result = self.get_inline_shape_index(0, rtype)
            if result > 0:
                return self._document.InlineShapes[result].Range
            else:
                return None
        else:
            return None


"""
CHANGE LOG:
-----------
$Log: word.py  $
Revision 1.2 2015/12/07 08:50:01CET Mertens, Sven (uidv7805) 
some pep8 cleanup
Revision 1.1 2015/04/23 19:05:02CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/05_Software/04_Engineering/01_Source_Code/stk/rep/project.pj
Revision 1.20 2015/01/27 10:23:13CET Mertens, Sven (uidv7805)
successor is a property and should be mentioned
--- Added comments ---  uidv7805 [Jan 27, 2015 10:23:13 AM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.19 2015/01/26 20:20:14CET Ellero, Stefano (uidw8660)
Removed all rep based deprecated function usage inside stk and module tests.
--- Added comments ---  uidw8660 [Jan 26, 2015 8:20:15 PM CET]
Change Package : 296836:1 http://mks-psad:7002/im/viewissue?selection=296836
Revision 1.18 2014/10/24 11:43:05CEST Hospes, Gerd-Joachim (uidv8815)
pep8 and pylint fixes
--- Added comments ---  uidv8815 [Oct 24, 2014 11:43:05 AM CEST]
Change Package : 270444:1 http://mks-psad:7002/im/viewissue?selection=270444
Revision 1.17 2014/10/24 10:05:03CEST Danciu, Alin (DanciuA)
Added functionality related to :
header and footer text and page alignment
inserting inline shapes from file.
--- Added comments ---  DanciuA [Oct 24, 2014 10:05:04 AM CEST]
Change Package : 272009:1 http://mks-psad:7002/im/viewissue?selection=272009
Revision 1.16 2014/10/14 17:57:18CEST Hospes, Gerd-Joachim (uidv8815)
add set_paragraph_heading_style() with test
--- Added comments ---  uidv8815 [Oct 14, 2014 5:57:21 PM CEST]
Change Package : 271854:1 http://mks-psad:7002/im/viewissue?selection=271854
Revision 1.15 2014/03/28 10:25:51CET Hecker, Robert (heckerr)
Adapted to new coding guiedlines incl. backwardcompatibility.
--- Added comments ---  heckerr [Mar 28, 2014 10:25:52 AM CET]
Change Package : 228098:1 http://mks-psad:7002/im/viewissue?selection=228098
Revision 1.14 2014/03/25 08:59:31CET Hecker, Robert (heckerr)
Adaption to python 3.
--- Added comments ---  heckerr [Mar 25, 2014 8:59:31 AM CET]
Change Package : 227240:1 http://mks-psad:7002/im/viewissue?selection=227240
Revision 1.13 2013/04/19 12:53:37CEST Hecker, Robert (heckerr)
Functionality revert to version 1.11.
--- Added comments ---  heckerr [Apr 19, 2013 12:53:37 PM CEST]
Change Package : 106870:1 http://mks-psad:7002/im/viewissue?selection=106870
Revision 1.12 2013/04/11 10:17:02CEST Mertens, Sven (uidv7805)
fixing some pylint errors
--- Added comments ---  uidv7805 [Apr 11, 2013 10:17:03 AM CEST]
Change Package : 179495:1 http://mks-psad:7002/im/viewissue?selection=179495
Revision 1.11 2013/04/03 08:02:19CEST Mertens, Sven (uidv7805)
pylint: minor error, warnings fix
--- Added comments ---  uidv7805 [Apr 3, 2013 8:02:19 AM CEST]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.10 2013/04/02 10:24:59CEST Mertens, Sven (uidv7805)
pylint: E0213, E1123, E9900, E9904, E1003, E9905, E1103
--- Added comments ---  uidv7805 [Apr 2, 2013 10:25:01 AM CEST]
Change Package : 176171:9 http://mks-psad:7002/im/viewissue?selection=176171
Revision 1.9 2013/03/28 15:25:13CET Mertens, Sven (uidv7805)
pylint: W0311 (indentation), string class
--- Added comments ---  uidv7805 [Mar 28, 2013 3:25:13 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.8 2013/03/28 14:20:05CET Mertens, Sven (uidv7805)
pylint: solving some W0201 (Attribute %r defined outside __init__) errors
Revision 1.7 2013/03/28 13:31:15CET Mertens, Sven (uidv7805)
minor pep8
--- Added comments ---  uidv7805 [Mar 28, 2013 1:31:15 PM CET]
Change Package : 178224:1 http://mks-psad:7002/im/viewissue?selection=178224
Revision 1.6 2013/03/28 09:33:15CET Mertens, Sven (uidv7805)
pylint: removing unused imports
Revision 1.5 2013/02/28 17:21:00CET Hecker, Robert (heckerr)
Updates regarding Pep8 Style.
--- Added comments ---  heckerr [Feb 28, 2013 5:21:01 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.4 2013/02/28 08:12:26CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 28, 2013 8:12:26 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.3 2013/02/27 16:19:59CET Hecker, Robert (heckerr)
Updates regarding Pep8 StyleGuide (partly).
--- Added comments ---  heckerr [Feb 27, 2013 4:20:00 PM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.2 2013/02/20 08:21:53CET Hecker, Robert (heckerr)
Adapted to Pep8 Coding Style.
--- Added comments ---  heckerr [Feb 20, 2013 8:21:53 AM CET]
Change Package : 168499:1 http://mks-psad:7002/im/viewissue?selection=168499
Revision 1.1 2013/02/12 16:13:29CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/rep/project.pj
Revision 1.9 2012/09/25 08:08:01CEST Mogos, Sorin (mogoss)
* bug-fix: fixed "global name 'create_new_word_instance' is not defined" error
--- Added comments ---  mogoss [Sep 25, 2012 8:08:05 AM CEST]
Change Package : 147308:2 http://mks-psad:7002/im/viewissue?selection=147308
Revision 1.8 2012/09/25 08:05:43CEST Mogos, Sorin (mogoss)
* update: turn off grammatical and spelling errors
--- Added comments ---  mogoss [Sep 25, 2012 8:05:50 AM CEST]
Change Package : 147308:2 http://mks-psad:7002/im/viewissue?selection=147308
Revision 1.7 2010/10/04 10:20:19CEST Raicu, Ovidiu (RaicuO)
Bug-fix for remove_table function, error handling in save_as function, and table_id_to_index() function.
--- Added comments ---  RaicuO [Oct 4, 2010 10:20:19 AM CEST]
Change Package : 37852:1 http://mks-psad:7002/im/viewissue?selection=37852
Revision 1.6 2010/04/29 10:31:36CEST oraicu
Added auto resize for tables when the size of the data is greater than the size of the table.
Bugfix for set_row_style.
--- Added comments ---  oraicu [2010/04/29 08:31:36Z]
Change Package : 41938:1 http://LISS014:6001/im/viewissue?selection=41938
Revision 1.5 2010/03/22 08:32:24CET Ovidiu Raicu (oraicu)
Changed the name of the functions to be according to coding guidelines.
--- Added comments ---  oraicu [2010/03/22 07:32:24Z]
Change Package : 37852:1 http://LISS014:6001/im/viewissue?selection=37852
Revision 1.4 2010/02/19 15:06:31CET dkubera
update header and footer
--- Added comments ---  dkubera [2010/02/19 14:06:31Z]
Change Package : 33974:2 http://LISS014:6001/im/viewissue?selection=33974
Revision 1.3 2010/01/26 07:25:10CET Ovidiu Raicu (oraicu)
Updated stk_word class.
--- Added comments ---  oraicu [2010/01/26 06:25:10Z]
Change Package : 35288:1 http://LISS014:6001/im/viewissue?selection=35288
Revision 1.2 2009/06/24 22:18:34CEST Robert Hecker (rhecker)
Some Changes for Doxygen Comments
--- Added comments ---  rhecker [2009/06/24 20:18:34Z]
Change Package : 27994:1 http://LISS014:6001/im/viewissue?selection=27994
--- Added comments ---  rhecker [2009/06/24 20:18:34Z]
Change Package : 27994:1 http://LISS014:6001/im/viewissue?selection=27994
Revision 1.1 2009/06/24 21:36:04CEST Robert Hecker (rhecker)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/31_PyLib/project.pj
"""
