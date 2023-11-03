"""
fct\cgeb\usecase
----------------

**generate a test report with special constraint visualization** for all constraints saved in a given data base

Mode of the report can be selected:

MODE_BASIC:
  Visualize all constraint sets referenced by constraint_set_id_list.  For each constraint set generate a
  SubSection with all of its constraints plotted in one SubSubsection.

MODE_PER_SET:
  Create report out of list of constraint sets. Write one subsection per Set with one subsubsection per constr.

You need to specify the SqLite file and can also set output path & filename and report title.

call ``uvc_gen_report.py -h`` to get a full list of all parameters

**usage**::

    uvc_gen_report.py -f <sqlite_file>
    uvc_gen_report.py -m all_per_set -f <sqlite_file> -d <destination_path> -o <out_file> -r <report_title>

**add. User-API Interfaces**

    - `UcvGenReport`  class to create test report with special constraint visualization
    - `MODE_BASIC`, `MODE_PER_SET`  supported report modes

:org:           Continental AG
:author:        Oliver Weinhold

:version:       $Revision: 1.3 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2015/12/07 16:31:30CET $

"""
# pylint: disable=C0103
# ====================================================================
# System Imports
# ====================================================================

from argparse import ArgumentParser
# from re import search as research
from os import getcwd, path
import os
from sqlite3 import connect
import sys

# ====================================================================
# Set system path
# ====================================================================

STK_FOLDER = path.abspath(path.join(path.split(__file__)[0], r"..\.."))

if STK_FOLDER not in sys.path:
    sys.path.append(STK_FOLDER)

# ====================================================================
# Local Imports
# ====================================================================

import stk.db.cl.cl as cl
import stk.img as val_plot
# import stk.rep as rep
# import stk.rep.report_base as rep_base
# from stk.db.cl.cl import PluginCLDB
# from stk.rep import ValidationReportBase
# from stk.rep.report_base import BaseReportLabGenerator
from stk.rep.report_base import PdfReport
from stk.val.ucv import UcvPlot
# from stk.db.db_connect import DBConnect
from stk.util import logger

# ====================================================================
# Constants
# ====================================================================
MODE_BASIC = 'all_basic'
MODE_PER_SET = 'all_per_set'

MODES = [MODE_BASIC, MODE_PER_SET]

DEFAULT_IMAGENAME = 'UseCaseImage'
DEFAULT_IMAGE_EXTENSION = 'png'

SECTION_CONSSET = 'Constraints per ConstraintSet'
SUBSECTION_CONSSET = 'ConsSet'

SECTION_APPENDIX = 'Settings'
SUBSECTION_SIGNALS = 'Signal overview'
SUBSECTION_OPERANTS = 'Operant overview'

TABLE_KEYLIST_CONSSET = ['SetID', 'ParentID', 'Name', 'Operant', 'MeasID']

TABLE_KEYMAP_CONSSET = {'SetID': cl.COL_NAME_CONSET_SETID,
                        'ParentID': cl.COL_NAME_CONSET_PARENTID,
                        'Name': cl.COL_NAME_CONSET_NAME,
                        'Operant': cl.COL_NAME_CONSET_SETOP,
                        'MeasID': cl.COL_NAME_CONSET_MEASID}

TABLE_KEYLIST_CONS = ['ConsID', 'MeasID', 'SignalID', 'MinSamples', 'MaxSamples']

TABLE_KEYMAP_CONS = {'ConsID': cl.COL_NAME_SIGCON_CONSID,
                     'MeasID': cl.COL_NAME_SIGCON_MEASID,
                     'SignalID': cl.COL_NAME_SIGCON_SIGNALID,
                     'MinSamples': cl.COL_NAME_SIGCON_MINSAMPLES,
                     'MaxSamples': cl.COL_NAME_SIGCON_MAXSAMPLES}

TABLE_KEYLIST_SIGNALS = ['SignalID', 'Name']

TABLE_KEYMAP_SIGNALS = {'SignalID': cl.COL_NAME_CONSIG_SIGNALID,
                        'Name': cl.COL_NAME_CONSIG_NAME}


# ====================================================================
# Helper Functions
# ====================================================================
class BaseConstrReportException(BaseException):
    """Base of all cl errors"""
    pass


# ====================================================================
# Classes
# ====================================================================
class UcvGenReport(PdfReport):
    """
    Write a pdf report with constraint visualizations.  Default mode of operation is to create one section in the
    report with one subsection for every constraint set.  Each of the subsections then contains a subsubsection for
    each of its constraints, with one plot for each constraint.

    **usage**::

        ugr = UcvGenReport(report_title, out_file_with_path, MODE_PER_SET, cl_db_conn, cat_db_conn)
        ugr.CreateReport()

    """

    def __init__(self, report_title, outfile_path_name, mode, cl_connection, cat_connection):
        """
        :param report_title: Name of report, printed on first page
        :param outfile_path_name: full path to the ouput file
        :param db_connector: represents db object
        """
        self.__logger = logger.Logger(self.__class__.__name__, logger.INFO)
        self.outfile_path_name = outfile_path_name
        PdfReport.__init__(self, report_title=report_title, outfile_path_name=outfile_path_name,
                           make_table_of_content=True)
        self.__logger.info('Creating report at %s' % outfile_path_name)
        self._mode = mode
        self._cl = cl_connection
        self._cat = cat_connection
        self.plotter = val_plot.ValidationPlot(path.dirname(outfile_path_name))

        self._ucvp = UcvPlot(self._cl)
        self._imagenames = []

    def __del__(self):

        self.__DeleteImages()
        pass

    def DefaultGenerator(self, constraint_set_id_list):
        """
        Visualize all constraint sets referenced by constraint_set_id_list.  For each constraint set generate a
        SubSection with all of its constraints plotted in one SubSubsection.

        :param constraint_set_id_list: for example get these via cl.getConstraintSetIDs()
        :type constraint_set_id_list: list of int
        """
        self.AddSection('All Constraint Sets')
        for constraint_set_id in constraint_set_id_list:
            self._AddSubsectionFromConstraintSet(constraint_set_id, 'Constraint Set ' + str(constraint_set_id),
                                                 constraint_list_list=None, constraint_list_names=None)

    def _AddSubsectionFromConstraintSet(self, constraint_set_id, subsection_name, constraint_list_list=None,
                                        constraint_list_names=None):
        """
        Add one SubSection to the report.

        Don't call directly, use AddSectionFromConstraintSet(), because
        adding a SubSection without adding a Section results in a ValueError from self.BuildReport().

        Default content of the SubSection is one SubSubSection as constructed by
        _AddSubsubsectionFromConstraintList() that contains all the constraints in the set.  Deviate from that
        default with parameter constraint_list_list.

        :param constraint_set_id: constraint set to extract constraints from, which are plotted in a SubSubSection.
        :type constraint_set_id: get this from a DB, e.g. using cl.getConstraintSetIDs()
        :param subsection_name: SubSection header in the report
        :param constraint_list_list: group  the constraints of set constraint_set to lists of constraints that should
            be plotted together.
        :type constraint_list_list: list of list of ints
        :param constraint_list_names: names for
        :type constraint_list_names: list of string
        """
        consSet_maps = self._cl.get_cons_map(constraint_set_id, col=cl.COL_NAME_CONMAP_SETID)
        constraint_list = []
        for i in range(len(consSet_maps)):
            _ = consSet_maps[i][cl.COL_NAME_CONMAP_CONSID]
            constraint_list.append([self._cl.get_sig_constraint(_)])

# TODO: OLIVER: handling of constraint_list_list: postponed
#        if constraint_list_list:
#            pass
#        else:
#            constraint_list_list = [constraint_list]
#            subsubsection_names = ['All Constraints of Set ' + str(constraint_set_id)]
# OLIVER: handling of constraint_list_list: postponed
        constraint_list_list = [constraint_list]
        subsubsection_names = ['Constraint ' + str(constraint_set_id)]

        self.AddSubSection(subsection_name)
        for i in range(len(constraint_list_list)):
            for j in range(len(constraint_list_list[i])):
                self._AddSubsubsectionFromConstraintList(constraint_list_list[i][j],
                                                         subsubsection_names[i] + '_' + str(j))

    def _AddSubsubsectionFromConstraintList(self, constraint_list, subsubsection_name):
        """
        Add one SubSubSection to the report.

        Don't call directly, use _AddSubsectionFromConstraintSet(), because
        adding a SubSubSection without adding a SubSection and Section
        results in a ValueError from self.BuildReport().

        :param constraint_list: the constraints that are to be put into single subplots of one figure
        :type constraint_list: list of list of dict
        :param subsubsection_name: SubSubSection header in the report
        :type subsubsection_name: string
        """
        self.AddSubSubSection(subsubsection_name)
        constraint_names = []
        for single_constraint in constraint_list:
            constraint_names.append([str(single_constraint[0]['CONSID'])])
        self.AddPlotsToDocument(constraint_list=constraint_list, constraint_names=constraint_names)

    def AddPlotsToDocument(self, constraint_list, constraint_names, show_grid=False, keep_time_offset=True):
        """
        Add one plot to the pdf document.  The plot is constructed from constraint_list.  Use parameters as for
        `stk.val.ucv.UcvPlot.PlotConstraints()`.

        The constraints in constraint_list are put into one figure each.

        :param constraint_list: the constraints that are to be put in the figures
        :type constraint_list: list of lists of dict
        :param constraint_names: names for legend
        :type constraint_names: list of strings
        :param show_grid: opt. show grid in plot, default: False
        :type show_grid:  Boolean
        :param keep_time_offset: opt. use original constraint time stamps or plot in interval [0, endts - begints]
        :type keep_time_offset: Boolean
        """
        n_constraints = len(constraint_list)
        ucvp = UcvPlot(self._cl)
        for i, single_constraint in enumerate(constraint_list):
            plt = ucvp.PlotConstraints([constraint_list[i]], constraint_names=constraint_names[i],
                                       x_label='t [s]', y_label='tbd', single_figures=True,
                                       show_grid=show_grid, plotter=self.plotter, titles=[''],
                                       show_plots=False, keep_time_offset=keep_time_offset)
            buffer = self.plotter.get_plot_data_buffer(grid=show_grid)
            # don't give parameter file_name! Else: Only one plot in buffer:
            drawing = self.plotter.get_drawing_from_buffer(buffer, width=450, height=150)
#            self.InsertImage("Constraint list", drawing)
            self.InsertImage('Constraint' + str(constraint_names[i][0]), drawing)
        # test drawing.save(['gif'], outDir='D:\\aa', title=str(time.time()), fnRoot=str(time.time()), bmFmt='png')

    def StructuredSetGenerator(self, constraint_set_id_list):
        """
        Create report out of list of constraint sets. Write one subsection per Set with one subsubsection per constr.

        :param constraint_set_id_list: list with all constraint set ids to write to pdf
        """
        self.__logger.info('Add section %s' % SECTION_CONSSET)
        self.AddSection(SECTION_CONSSET)

        show_grid = True
        keep_time_offset = True

        for constraint_set_id in constraint_set_id_list:

            # constraint sets
            consSet_info = self._cl.get_constraint_set(constraint_set_id)
            subsection_name = SUBSECTION_CONSSET + ' ' + consSet_info[0][cl.COL_NAME_CONSET_NAME]
            self.__logger.info('Add subsection %s' % subsection_name)
            self.AddSubSection(subsection_name)

            table_data = self._ucvp.GetTableData(consSet_info, TABLE_KEYMAP_CONSSET)
            self.InsertTable(consSet_info[0][cl.COL_NAME_CONSET_NAME],
                             TABLE_KEYLIST_CONSSET, table_data, spacer=False)

            # constraints per set
            consSet_complete = self._cl.get_constraints(constraint_set_id, None)
            constraint_list = consSet_complete[0].value[cl.KID_VALUENAME_CONSTRAINTS]

            for constraint in constraint_list:

                cons_name = 'Constraint_' + str(constraint[cl.COL_NAME_SIGCON_CONSID])
                self.AddSubSubSection(cons_name)

                table_data = self._ucvp.GetTableData([constraint], TABLE_KEYMAP_CONS)
                self.InsertTable(cons_name, TABLE_KEYLIST_CONS, table_data, spacer=False)

                file_name = self._GetUniqueImageName(cons_name)
                plt = self._ucvp.PlotConstraints([constraint],
                                                 constraint_names=str(constraint[cl.COL_NAME_SIGCON_CONSID]),
                                                 x_label='t [s]', y_label='tbd', single_figures=True,
                                                 show_grid=show_grid, plotter=self.plotter, titles=[''],
                                                 show_plots=False, keep_time_offset=keep_time_offset)
                plt_buffer = self.plotter.get_plot_data_buffer(grid=show_grid)
                drawing = self.plotter.get_drawing_from_buffer(plt_buffer, file_name=file_name, width=450, height=150)
                self.InsertImage(cons_name, drawing)
        return

    def _GetUniqueImageName(self, imagename=None):
        """create unique image file name

        :param imagename: imagename to check, use default if None given [str]
        :return imagename: maybe changed imagename
        """
        if imagename is None:
            imagename = DEFAULT_IMAGENAME

        if imagename in self._imagenames:
            number = -1
            constrset_name_unique = False

            while constrset_name_unique is False:
                number += 1
                imagename = '%s_%04d' % (imagename, number)

        self._imagenames.append(imagename)
        return imagename

    def __DeleteImages(self):

        for imagename in self._imagenames:
            imagename = '.'.join([imagename, DEFAULT_IMAGE_EXTENSION])
            imagepath = path.join(os.path.dirname(self.outfile_path_name), imagename)
            if os.path.isfile(imagepath):
                os.remove(imagepath)

    def AddSignalTable(self):
        """
        Read all signal definitions and create table with this info.
        """
        self.__logger.info('Add subsection %s' % SUBSECTION_SIGNALS)
        self.AddSubSection(SUBSECTION_SIGNALS)
        signal_info = self._cl.get_cons_signal('%')

        table_data = self._ucvp.GetTableData(signal_info, TABLE_KEYMAP_SIGNALS)
        self.InsertTable(SUBSECTION_SIGNALS, TABLE_KEYLIST_SIGNALS, table_data, spacer=False)

        return

    def AddOperantTable(self):
        """
        Get all operant definitions from module cl and create table with this info.
        """
        self.__logger.info('Add subsection %s' % SUBSECTION_OPERANTS)
        self.AddSubSection(SUBSECTION_OPERANTS)
        operant_names = cl.CL_OP_NAME_MAP

        operant_functions = cl.CL_OP_FUNC_MAP

        table_data = []

        for operant_id in operant_names:
            row_data = {}
            row_data['OperantID'] = operant_id
            row_data['Operant'] = operant_names[operant_id]
            row_data['Meaning'] = operant_functions[operant_id]

            table_data.append(row_data)

        self.InsertTable(SUBSECTION_SIGNALS, ['OperantID', 'Operant', 'Meaning'], table_data, spacer=False)

        return

    def AddAppendix(self):
        """
        Switch section numeration to alphabetic character instead of numbers.
        """
        self.__logger.info('Creating Appendix')
        self._PdfReport__report.Appendix()
        return

    def CreateReport(self):
        """
        Main method to create whole report
        """

        if not self._mode in MODES:
            message = 'Mode %s does not exist.' % self._mode
            logging.error(message)
            raise BaseConstrReportException(message)

        self.__logger.info('Mode is: %s' % self._mode)

        if self._mode == MODE_BASIC:
            constraint_set_ids = self._cl.get_constraint_set_ids()
            self.DefaultGenerator(constraint_set_ids)

        elif self._mode == MODE_PER_SET:
            constraint_set_ids = self._cl.get_constraint_set_ids()
            self.StructuredSetGenerator(constraint_set_ids)

        else:
            self.__logger.warning('No special code called for mode: %s' % self._mode)

        self.AddAppendix()
        self.AddSection(SECTION_APPENDIX)
        self.AddSignalTable()
        self.AddOperantTable()

        self.BuildReport()

        # self._DeleteImages()

        return


# ====================================================================
# Main
# ====================================================================
if __name__ == '__main__':

    logging = logger.Logger(None, logger.INFO)
    logging.info('Start creation of constraint report...')

    opts = ArgumentParser(description="Generate a pdf with constraint plots, by default ordered by Constraint Sets")
    opts.add_argument("-m", "--mode", dest="mode", default=MODE_BASIC, type=str, help="one mode of: %s" % str(MODES))
    opts.add_argument("-f", "--db_file", dest="db_file_name",
                      help="Full path to database file from which to read constraints")
    opts.add_argument("-d", "--out_file_path", dest="out_file_path", default=getcwd(),
                      help="Full path to the generated file, excluding file name")
    opts.add_argument("-o", "--out_file_name", dest="out_file_name", default='Default_Report.pdf',
                      help="File name, excluding path")
    opts.add_argument("--report_title", dest="report_title", default='Default Report',
                      help="Title of the generated report")
    args = opts.parse_args()

    if not path.isfile(args.db_file_name):
        message = 'File %s does not exist!' % args.db_file_name
        logging.error(message)
        raise BaseConstrReportException(message)

    db = connect(args.db_file_name)
    _cl = cl.PluginCLDB(db)
    _cat = cl.PluginCLDB(db)

    ugr = UcvGenReport(args.report_title, path.join(args.out_file_path, args.out_file_name), args.mode, _cl, _cat)
    ugr.CreateReport()

    logging.info('Done')


"""
====================================================================
 Log
====================================================================
Log:
$Log: ucv_gen_report.py  $
Revision 1.3 2015/12/07 16:31:30CET Mertens, Sven (uidv7805) 
removing pep8 errors
Revision 1.2 2015/07/14 11:26:50CEST Mertens, Sven (uidv7805)
fixing imports and usages
--- Added comments ---  uidv7805 [Jul 14, 2015 11:26:51 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:03:49CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.10 2014/12/10 17:04:49CET Ellero, Stefano (uidw8660)
Remove all db.cl based deprecated function usage inside stk and module tests
--- Added comments ---  uidw8660 [Dec 10, 2014 5:04:50 PM CET]
Change Package : 281274:1 http://mks-psad:7002/im/viewissue?selection=281274
Revision 1.9 2014/09/25 13:29:07CEST Hospes, Gerd-Joachim (uidv8815)
adapt stk.img files to style guide, new names used in all modules and tests except stk.img tests
--- Added comments ---  uidv8815 [Sep 25, 2014 1:29:08 PM CEST]
Change Package : 264203:1 http://mks-psad:7002/im/viewissue?selection=264203
Revision 1.8 2014/06/03 11:57:56CEST Hospes, Gerd-Joachim (uidv8815)
extend epydoc and fix some minor pylint errors
--- Added comments ---  uidv8815 [Jun 3, 2014 11:57:57 AM CEST]
Change Package : 238266:1 http://mks-psad:7002/im/viewissue?selection=238266
Revision 1.7 2014/04/15 08:57:03CEST Hecker, Robert (heckerr)
Added some pylint exceptions to reduce number of messages.
--- Added comments ---  heckerr [Apr 15, 2014 8:57:03 AM CEST]
Change Package : 231472:1 http://mks-psad:7002/im/viewissue?selection=231472
Revision 1.6 2014/04/11 15:26:03CEST Mertens, Sven (uidv7805)
commenting out:
- unused rep import,
- non existing class import
--- Added comments ---  uidv7805 [Apr 11, 2014 3:26:03 PM CEST]
Change Package : 230890:1 http://mks-psad:7002/im/viewissue?selection=230890
Revision 1.5 2014/02/19 18:03:15CET Skerl, Anne (uid19464)
*use dicts as Trie-values
--- Added comments ---  uid19464 [Feb 19, 2014 6:03:16 PM CET]
Change Package : 220258:1 http://mks-psad:7002/im/viewissue?selection=220258
Revision 1.4 2014/01/15 18:01:01CET Skerl, Anne (uid19464)
*change modes, add mode all_per_set
*add tables with ConstrSet and Constr info
*add appendix
*delete images when report done
*add logging
--- Added comments ---  uid19464 [Jan 15, 2014 6:01:01 PM CET]
Change Package : 198254:13 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.3 2014/01/10 13:34:41CET Skerl, Anne (uid19464)
*remove CAT from ucs
*print pdf location
--- Added comments ---  uid19464 [Jan 10, 2014 1:34:41 PM CET]
Change Package : 198254:11 http://mks-psad:7002/im/viewissue?selection=198254
Revision 1.2 2013/12/06 14:51:02CET Weinhold, Oliver (uidg4236)
Adapt to new signature of UseCaseValidator.__init__()
--- Added comments ---  uidg4236 [Dec 6, 2013 2:51:02 PM CET]
Change Package : 208496:1 http://mks-psad:7002/im/viewissue?selection=208496
Revision 1.1 2013/12/05 14:17:03CET Weinhold, Oliver (uidg4236)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
04_Engineering/stk/cmd/project.pj
"""
