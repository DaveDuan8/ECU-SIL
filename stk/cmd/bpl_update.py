# -*- coding:utf-8 -*-
r"""
bpl_update
----------

**Update bpl files in MKS based on changes in collection**


**Features:**
    - check all collections in the oracle database concerning changes
      between now and the last check (delta identification)
    - create bpl for all changed collections according to the defined folder structure (see below)
    - **todo** update the affected bpls in MKS (see MKS structure) according to ini file

    the script runs with the given config file updating all listed collections.


**UseCase:**
    update tree with bpl files over night to get defined checkpoints for testing

**Usage:**

bpl_update_in_mks bpl_config.ini

**Configuration file:**

Configuration of used database and of the list of collections to be checked is stored using following structure:

.. python::

    ; config to update bpl files based on collections

    [db_connection]
    ; define connection parameters for oracle catalog db or sqlite file
    ; possible values: 'MFC4XX', 'ARS4XX' or SQLite path/file name
    connection: 'Test_BplUpdate.sqlite'

    [collections]
    ; list all collection names here as stored in Catalog DB,
    ; the script will generate bpl files with same names
    update_list: ['Test_Fct1_BplUpdate',
                  'Test_Fct1_BplUpdate_child'
                  'Test_Fct2_BplUpdate']

As the bpl files are stored relative to the path of the configuration file it is possible to update
only a subset of collections (e.g. for one function) using a config file in that folder.

**bpl folder structure**

Files are generated relative to the path of the configuration file (the project directory).

  - Update is starting at the folder where the config file is stored, all subfolders are searched for bpl files.
  - Files will be named like ``<collection>.bpl``
  - files are also expected/generated for empty collections
  - If a function name can be recognised a folder for that function will be generated/expected.
    - Naming convention used to create folders: ``<project>_<function>_<other_parameters>``
  - execution is logged to ``bpl_update.log``
  - ``bpl_update_result.csv`` lists all collections and bpl files with their final status
::

    project_dir \ config_file.ini
                \ collection_with-max-one-underscore.bpl
                \ function1 \ project_function1_all.bpl
                            \ project_function1_daylight.bpl
                            \ project_function1_night.bpl
                \ function2 \ project_function2_performance_tests.bpl
                            \ project_function2_function_tests.bpl
                \ function3 \ ...
                \ bpl_update.log
                \ bpl_update_results.csv


:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.3 $
:contact:       $Author: Mertens, Sven (uidv7805) $ (last change)
:date:          $Date: 2016/03/29 18:12:37CEST $
"""
# - import Python modules ---------------------------------------------------------------------------------------------
from sys import exit as sexit, path as spath
from os import walk, makedirs, chmod, remove, rename
from os.path import abspath, join, dirname, isabs, relpath, splitext, exists, isfile
from stat import S_IWUSR
from filecmp import cmp as fcmp
from traceback import print_exc
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from configparser import RawConfigParser, Error as ParseError
from collections import OrderedDict

# - import STK modules ------------------------------------------------------------------------------------------------
STK_FOLDER = abspath(join(dirname(__file__), r"..\.."))
if STK_FOLDER not in spath:
    spath.append(STK_FOLDER)

from stk.util.logger import Logger, INFO
import stk.mks.si as mks_si
from stk.db.db_common import AdasDBError
from stk.db.cat.cat import BaseRecCatalogDB
from stk.mts.bpl import Bpl, BplListEntry

# - defines -----------------------------------------------------------------------------------------------------------
ERR_OK = 0
ERR_UPDATE_ERROR = -200
ERR_CHECKIN_ERROR = -201
ERR_CONFIG_FILE_DOES_NOT_EXIST = -202
ERR_FILE_NOT_FOUND = -203
ERR_CONFIG_FILE_READ = -204
ERR_CONFIG_FILE_CONTENT = -205
ERR_DB_CONNECTION_CONFIG = -210
ERR_DB_COLL_MISSING = -211
ERR_BPL_READ_FILE = -220
ERR_BPL_FILE_CREATION = -221
ERR_NO_TASK_ID = -230
ERR_NO_SANDBOX = -231
ERR_CO_ERROR = -232
ERR_CI_ERROR = -233


# - classes -----------------------------------------------------------------------------------------------------------
class BplUpdate(object):
    r"""
    **Update existing bpl files with changes in catalog db collections**

    Class provides methods to
      - read a config,
      - find all bpl files in the subfolders
      - compare the bpl files with collections
      - create a new bpl file if needed
      - check in the changed files
      - update member revisions for changed files

    It returns an error code to be executed as scheduled task, error code '0' shows execution without problems.
    Additionally the status is logged to the file ``bpl_update.log`` in same path as the config file.

    see more details in module description `bpl_update.py`

    **usage example** (see also function `main`):

    .. python::

        bpl_upd = BplUpdate(config_file)
        result = bpl_upd.update_directories()

    """
    def __init__(self, config_file):
        """
        read config and prepare update

        :param config_file: path/file name of config file
        :type  config_file: string
        """
        self.error_status = ERR_OK
        self.bpl_top_dir = dirname(config_file)
        self._logger = Logger('BplUpdate', INFO, join(self.bpl_top_dir, 'bpl_update.log'))
        self._config = self._read_config(config_file)
        self.db_conn = None
        self.cat_db = None

        # setup db connection,
        # explicitly set default values for parameters that don't set None as default in DBconnect
        # unused for now: error_tolerance=ERROR_TOLERANCE_NONE, use_cx_oracle=False
        if self._config.get('connection') is None:
            self._logger.error('No parameter "connection" in section "[db_connection]" of %s' % config_file)
            self.error_status = ERR_DB_CONNECTION_CONFIG
        else:
            try:
                connection = str(self._config.get('connection'))
                if connection.endswith('.sqlite'):
                    connection = join(self.bpl_top_dir, connection)
                self.cat_db = BaseRecCatalogDB(connection)  # self.db_conn.Connect(cat)
            except Exception as err:
                self.error_status = ERR_DB_CONNECTION_CONFIG
                self._logger.error('can not setup db connection with configured settings: %s\n%s' % (connection, err))
        # get all bpl files in the top dir and all sub dirs
        self.bpl_dict = self.get_bpl_files()

    def _read_config(self, config_file, incl_sect=None):
        """
        private method to read config, check some requirements and return dict with config

        :param config_file: path/file name to read
        :type  config_file: string
        :param incl_sect : section name to include from other config file, for recursive calls
        :type  incl_sect : string
        """
        raw_config = RawConfigParser()
        try:
            raw_config.read(abspath(config_file))
        except ParseError as err:
            self.error_status = ERR_CONFIG_FILE_READ
            self._logger.error(err)
            return {}

        section_names_list = raw_config.sections()
        if not len(section_names_list):
            self.error_status = ERR_CONFIG_FILE_CONTENT
            self._logger.error('No sections defined in config file %s - min: [db_connection] and [collections].'
                               % config_file)
            return {}

        include_section = section_names_list if incl_sect is None else incl_sect

        include_config = []
        sections_list = OrderedDict()
        try:
            for section_name in section_names_list:
                # don't import if not inside specific chapter
                if section_name not in include_section:
                    continue
                # sections_list[section_name] = {}

                try:
                    include = raw_config.get(section_name, "include").strip('"\' ')
                    if len(include):
                        include_config.append([include, section_name])
                except ParseError:
                    pass

                if section_name == "db_connection":
                    sections_list["connection"] = eval(raw_config.get(section_name, "connection"))
                elif section_name == 'collections':
                    sections_list["update_list"] = eval(raw_config.get(section_name, 'update_list'))
                elif section_name == 'mks_settings':
                    if raw_config.has_option('mks_settings', 'task_id'):
                        sections_list['task_id'] = raw_config.get(section_name, 'task_id')

            # iterate through additional configs from includes now
            for inc in include_config:
                if not isabs(inc[0]):
                    inc[0] = join(dirname(config_file), inc[0])
                incl_lst = self._read_config(inc[0], inc[1])
                for incl_sct in incl_lst:
                    if incl_sct not in sections_list:
                        sections_list[incl_sct] = incl_lst[incl_sct]
                    else:
                        sections_list[incl_sct].update(incl_lst[incl_sct])

        except ParseError as err:
            self.error_status = ERR_CONFIG_FILE_CONTENT
            self._logger.error('Parse error during config file reading:\n %s' % err)

        return sections_list

    def get_bpl_files(self):
        """
        find all bpl files starting from set directory

        :return: dict { 'basename': {'path': relpath, 'status': 'old'}}
        """
        bpl_files = {}
        for root, _, files in walk(self.bpl_top_dir):
            for bpl_file in files:
                if splitext(bpl_file)[1] != '.bpl':
                    continue
                bpl_path = relpath(root, self.bpl_top_dir)
                # print r'found file %s\%s' % (bpl_path, bpl_file)
                bpl_file_name = str(splitext(bpl_file)[0]).lower()
                bpl_files[bpl_file_name] = {'path': bpl_path,
                                            'filename': join(root, bpl_file),
                                            'status': 'old'}
        return bpl_files

    @staticmethod
    def compare_col_bpl(col_recs, bpl_list):
        """
        compare rec files in passed lists

        :param col_recs: all recording names of a collection
        :type  col_recs: list of names
        :param bpl_list: all rec files in batch play list
        :type  bpl_list: `BplList` - list of `BplListEntries` with 'filepath' and sectionlist
        :return: True if similar lists
        """
        # first check length
        if len(col_recs) != len(bpl_list):
            return False
        # then check if all bpl entries have matching collection entry
        bpl_rec_names = [r.filepath for r in bpl_list]
        for rec in bpl_rec_names:
            if rec not in col_recs:
                return False
        return True

    def create_fct_dir(self, col_name):
        """
        create the directory for the function named in the collection
        based on the current dir bpl_top_dir
        :param col_name: name of the collection
        :type  col_name: string
        :return: name of function
        """
        if len(col_name.split('_')) > 1:
            funct = col_name.split('_')[1]
        else:
            funct = ''
        # prep: create path if needed
        bpl_path = join(self.bpl_top_dir, funct)
        if not exists(bpl_path):
            makedirs(bpl_path)

        return funct

    def generate_bpl_file(self, col_name, rec_list):
        """
        generate a bpl file for a given collection

        uses existing connection to cat db and creates a bpl file with:
          - file name like collection name
          - in a folder named after the function coded in collection name <project>_<function>_<param>

        a missing folder is also generated starting at current bpl_top_dir

        :param col_name: name of collection listing the recordings
        :type  col_name: string
        :param rec_list: list of recordings
        :type rec_list: list
        :return: path/file name of generated file
        """
        dir_name = self.create_fct_dir(col_name)
        bpl_file_name = join(self.bpl_top_dir, dir_name, col_name + '.bpl')
        # make sure this file is not locked by mks or whatever
        if isfile(bpl_file_name):
            chmod(bpl_file_name, S_IWUSR)
        bpl_writer = Bpl(str(bpl_file_name))
        for rec in rec_list:
            bpl_writer.append(BplListEntry(rec))
        bpl_writer.write()

        return bpl_file_name

    def update_directories(self):
        """run through all subfolders and update existing bpl files
        """

        # get all collections to update
        # for each collection:
        collections = self._config.get('update_list')
        for col_name in collections:
            # print 'search for collection "%s"' % col_name
            try:
                _ = self.cat_db.get_collection_id(col_name)
            except AdasDBError as db_err:
                self._logger.warning(db_err)
                self.error_status = ERR_DB_COLL_MISSING
                continue
            # get directory for function
            fct_name = self.create_fct_dir(col_name)
            # create the new bpl file
            bpl_file_name_new = join(self.bpl_top_dir, fct_name, col_name + '_new.bpl')
            try:
                self.cat_db.export_bpl_for_collection(col_name, bpl_file_name_new, True, True)
            except AdasDBError as err:
                self._logger.error('problems writing bpl file %s:\n%s' % (bpl_file_name_new, err))
                self.error_status = ERR_BPL_FILE_CREATION
                continue
            # compare the new bpl file with an existing one (if there is one)
            bpl_file_name = join(self.bpl_top_dir, fct_name, col_name + '.bpl')
            if isfile(bpl_file_name):
                same = fcmp(bpl_file_name, bpl_file_name_new)
                if not same:
                    self._logger.info('update bpl file %s for collection %s' % (bpl_file_name, col_name))
                    chmod(bpl_file_name, S_IWUSR)
                    remove(bpl_file_name)
                    rename(bpl_file_name_new, bpl_file_name)
                    self.bpl_dict[col_name.lower()]['status'] = 'updated'
                else:
                    self._logger.info('bpl for collection "%s" up to date' % col_name)
                    remove(bpl_file_name_new)
                    self.bpl_dict[col_name.lower()]['status'] = 'match'
            else:
                # bpl file didn't exist before
                self.bpl_dict[col_name.lower()] = {'status': 'new',
                                                   'filename': join(self.bpl_top_dir, col_name + '.bsig')}
                rename(bpl_file_name_new, bpl_file_name)
                self._logger.info('created new bpl file "%s" for collection %s' % (bpl_file_name, col_name))

        # check if collections are removed but bpl files exist for that collection
        # and list bpl files that have no matching collections
        all_col_names = self.cat_db.get_all_collection_names()
        for bpl_name in [b.lower() for b in self.bpl_dict if self.bpl_dict[b]['status'] == 'old']:
            bpl_file_name = relpath(self.bpl_dict[bpl_name]['filename'], self.bpl_top_dir)
            if bpl_name in all_col_names:
                self.bpl_dict[bpl_name]['status'] = 'rem_col?'
                self._logger.warning('collection removed from config? - file %s has matching collection "%s"'
                                     % (bpl_file_name, bpl_name))
            else:
                self.bpl_dict[bpl_name]['status'] = 'junk'
                self._logger.warning('found bpl file with no matching collection: %s' % bpl_file_name)

        # create table with all bpl update results
        with open(join(self.bpl_top_dir, 'bpl_update_result.csv'), 'w') as res_file:
            res_file.write('collection; status; bpl file\n')
            for bpl_name in self.bpl_dict:
                res_file.write(bpl_name + '; ' +
                               self.bpl_dict[bpl_name]['status'] + '; ' +
                               relpath(self.bpl_dict[bpl_name]['filename'], self.bpl_top_dir) + '\n')

        return self.error_status

    def checkin_updated_files(self):
        """
        use internal bpl dict to check in all updated files

        :TODO: currently stk.mks.si does not return sufficient error messages
               checkin_updated_files() does not recognize errors during checkin/checkout
        """
        # first check if bpl top dir contains a mks project file, make sure we have a sandbox
        error = ERR_OK
        task_id = self._config.get('task_id')
        if not task_id:
            self._logger.warning('no mks task configured, if the updates should be checked in define the "task_id" '
                                 'string in a config section "[mks_settings]"')
            return ERR_OK
        if not exists(join(self.bpl_top_dir, 'project.pj')):
            self._logger.error('bpl files not in a sandbox, can not find file project.pj with mks information.')
            return ERR_NO_SANDBOX
        mks = mks_si.Si()
        mks.setChangePackageId(task_id)
        for name in [b.lower() for b in self.bpl_dict if self.bpl_dict[b]['status'] == 'updated']:
            print 'checking in %s' % self.bpl_dict[name]['filename']
            try:
                if mks.co(self.bpl_dict[name]['filename']):
                    error = ERR_CO_ERROR
                    self._logger.error('can not check out %s: returned error %s'
                                       % (self.bpl_dict[name]['filename'], error))
                    continue
            except mks_si.SiException as err:
                self._logger.error('can not check out %s:%s' % (self.bpl_dict[name]['filename'], err))
                error = ERR_CO_ERROR
                continue
            try:
                if mks.ci(self.bpl_dict[name]['filename'], 'modified by bpl_update tool'):
                    error = ERR_CO_ERROR
                    self._logger.error('check in problems with %s - returned error %s'
                                       % (self.bpl_dict[name]['filename'], error))
                    continue
            except mks_si.SiException as err:
                self._logger.error('check in problems with %s:%s' % (self.bpl_dict[name]['filename'], err))
                error = ERR_CO_ERROR
                continue
            self._logger.info('update in mks for %s' % self.bpl_dict[name]['filename'])

        return error


def main():
    """
    **main function**

    read options and loop through bpl files

    usage: bpl_update.py [-h]  <config-file>
    """
    error = ERR_OK
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    # mandatory settings:
    opts.add_argument('config_file', type=str, help='configuration with list of collections')

    args = opts.parse_args()

    if error is ERR_OK and isfile(args.config_file) is False:
        error = ERR_CONFIG_FILE_DOES_NOT_EXIST
        print 'can not find config file %s' % args.config_file

    # now run the update
    if error is ERR_OK:
        bpl_upd = BplUpdate(args.config_file)
        try:
            error = bpl_upd.update_directories()
        except StandardError as err:
            print(err)
            print_exc()
            error = ERR_UPDATE_ERROR
        '''
        stk.mks.si checkin does not work, new FR created
        try:
            error = bpl_upd.checkin_updated_files()
        except StandardError as err:
            print(err)
            print_exc()
            error = ERR_CHECKIN_ERROR
        '''
    if error != ERR_OK:
        print("\n\bpl_update causes error:" + str(error))

    return error


# - main--- -----------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    sexit(main())


"""
CHANGE LOG:
-----------
$Log: bpl_update.py  $
Revision 1.3 2016/03/29 18:12:37CEST Mertens, Sven (uidv7805) 
fix for path
Revision 1.2 2016/03/29 17:39:46CEST Mertens, Sven (uidv7805)
import only the neccessary
Revision 1.1 2015/04/23 19:03:43CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/cmd/project.pj
Revision 1.7 2015/01/22 14:51:41CET Mertens, Sven (uidv7805)
pylint fixes
--- Added comments ---  uidv7805 [Jan 22, 2015 2:51:42 PM CET]
Change Package : 270558:1 http://mks-psad:7002/im/viewissue?selection=270558
Revision 1.6 2014/11/20 18:25:03CET Ellero, Stefano (uidw8660)
The "update_directories" method in the "BplUpdate" class was updated to store also sections information when
generating/updating BPL files (if the DB collection was defined with sections). The module "test_bpl_update.py"
was updated to take advantage of the new functionality introduced in the "BplUpdate" class.
--- Added comments ---  uidw8660 [Nov 20, 2014 6:25:03 PM CET]
Change Package : 280053:1 http://mks-psad:7002/im/viewissue?selection=280053
Revision 1.5 2014/10/24 11:22:59CEST Hospes, Gerd-Joachim (uidv8815)
get back searching for collection before writing
--- Added comments ---  uidv8815 [Oct 24, 2014 11:23:00 AM CEST]
Change Package : 272109:1 http://mks-psad:7002/im/viewissue?selection=272109
Revision 1.4 2014/10/24 10:12:25CEST Hospes, Gerd-Joachim (uidv8815)
add error output for ci, but not all errors are provided by stk.mks.si.Si.ci()
--- Added comments ---  uidv8815 [Oct 24, 2014 10:12:25 AM CEST]
Change Package : 272109:1 http://mks-psad:7002/im/viewissue?selection=272109
Revision 1.3 2014/10/21 18:09:02CEST Hospes, Gerd-Joachim (uidv8815)
fix missing task_id problem
--- Added comments ---  uidv8815 [Oct 21, 2014 6:09:03 PM CEST]
Change Package : 272109:1 http://mks-psad:7002/im/viewissue?selection=272109
Revision 1.2 2014/10/20 19:42:41CEST Hospes, Gerd-Joachim (uidv8815)
add check-in of updated files, change to cat db method to create bpl files, tests updated
--- Added comments ---  uidv8815 [Oct 20, 2014 7:42:42 PM CEST]
Change Package : 272109:1 http://mks-psad:7002/im/viewissue?selection=272109
Revision 1.1 2014/10/10 13:40:24CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/cmd/project.pj
"""
