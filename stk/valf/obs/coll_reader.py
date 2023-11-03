"""
stk/valf/coll_reader
--------------------

The component for reading mts batch play list from bpl, ini or DB catalogue.

**User-API Interfaces**

    - `stk.valf` (complete package)
    - `CollReader` (this module)

:org:           Continental AG
:author:        Sven Mertens

:version:       $Revision: 1.11 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/07/09 22:46:40CEST $
"""
# pylint: disable=W0702,C0103
# - import Python modules ---------------------------------------------------------------------------------------------
from os import walk
from os.path import abspath, basename, isdir, isfile, join, splitext
from dircache import listdir
from re import search as research

# - import STK modules ------------------------------------------------------------------------------------------------
from stk.db.db_common import BaseDB
from stk.db.catalog import Collection, CollManager
from stk.mts.bpl import Bpl
from stk.mts.bpl.bpl_base import Section
from stk.valf import BaseComponentInterface
from stk.valf.db_connector import MASTER_DB_USR_PORT_NAME, MASTER_DB_PW_PORT_NAME, MASTER_DB_SPX_PORT_NAME, \
    DB_FILE_PORT_NAME
from stk.valf.signal_defs import GLOBAL_BUS_NAME, COLLECTION_NAME_PORT_NAME, PLAY_LIST_FILE_PORT_NAME, \
    COLLECTION_PORT_NAME, COLLECTION_LABEL_PORT_NAME, COLLECTIONID_PORT_NAME, DATABASE_OBJECTS_CONN_PORT_NAME, \
    FILE_COUNT_PORT_NAME, SIM_PATH_PORT_NAME, REMOVED_FILES_PORT_NAME, CURRENT_SIMFILE_PORT_NAME, \
    CURRENT_FILE_PORT_NAME, IS_FINISHED_PORT_NAME, SIMFILEBASE_PORT_NAME, DBCONNECTION_PORT_NAME, \
    IS_DBCOLLECTION_PORT_NAME, SIMCHECK_PORT_NAME, SIMFILEEXT_PORT_NAME, EXACTMATCH_PORT_NAME, SIMSELECTION_PORT_NAME, \
    RECURSE_PORT_NAME, CURRENT_SECTIONS_PORT_NAME, CURRENT_MEASID_PORT_NAME


# - classes -----------------------------------------------------------------------------------------------------------
class CollectionReader(BaseComponentInterface):
    r"""
    Observer class to handle Batch Play Lists provided as .bpl or .ini file or DB catalogue
    called by Process_Manager during the different states:

    Process Manager states used:

    - Initialize: read the catalogue
    - LoadData: provide the next rec file name
    - all others -> PostInitialize, ProcessData to Terminate: not used

    Ports used on local bus:

    - read ``CollectionName``: path\to\filename (.bpl / .ini / .txt) or DB catalogue name **(mandatory)**
    - read ``CollectionLabel``: when DB catalogue in use, this label states according label to use, default: None/null
    - read ``DBConnection``: if collection is DB catalog, set to 'VGA', 'MFC4XX' or 'ARS4XX' or path/to/sqlite.file
    - read ``SimOutputPath``: path to simulation output files **(mandatory if SimCheck isn't set to False)**
      can also be list of paths -> check description below as CurrentSimFile then also returns list of list
    - read ``SimFileBaseName``: opt. base name of simulation files, default: ""
    - read ``Recurse``: opt. recurse into sub directories if set to True
    - read ``ExactMatch``: opt. set True if simulation file name must match exactly the recording file name.
      If activated, finds only name.bsig but not name_v1.bsig, name_tst.bsig etc., default: None
    - read ``SimFileExt``: opt. file extension e.g. 'csv' or extension list ['csv','bsig'] of simulation files,
      default .csv
    - read ``SimCheck``: default: True, set it to False when you don't want simulation files (e.g. bsigs) to be
      checked, and only want to go through recordings. ``Recurse``, ``ExactMatch``, ``SimFileExt``, ``SimFileBaseName``
      and ``SimOutputPath`` isn't in use then. Only ``SimSelection`` can be used. To be backward compatible,
      ``CurrentSimFile`` will contain same as ``CurrentFile`` instead.
    - set ``CurrentSimFile``: name of current sim output file loaded by BplReader
    - set ``IsDbCollection``: True/False whether it is a collection from DB or file
    - set ``CollectionId``:  CatDb internal measurement id of the current rec file if DB is used, None for bpl files

    Ports on 'Global' bus:

    - read ``SimSelection``: opt. list of indices to use only particular recordings (list starts with '0')
      e.g. "[ 1, 3, 5, 7, 9]" or shorter "[(1,10,2)]" (syntax as in range() )

    - set ``CurrentFile``: name of current rec file as listed in bpl file
    - set ``IsFinished``: True if last file was provided
    - read ``IsFileComplete``: check if file processing is finished,
      set by component, prevents setting "IsFinished" if set to True

    - set ``FileCount``: number of measurement files in catalog list

    :note: ports "CollectionName" and "SimOutputPath" are mandatory to Initialize

    This port usage allows to have several CollectionReader instances in parallel. Some projects requested this
    as they need to read different sim output files in parallel for one recording.


    **HPC support**
    ===============

    LIFS010s adaption
    =================

    In ``BplFilePath`` and all entries of the loaded bpl list and rec file list the path is adapted
    if bpl_reader is running on an HPC client.

    In all mentioned path names the name ``LIFS010`` is changed to ``LIFS010s`` to use the fast connection
    to the file server. Ports ``CurrentFile`` and ``CurrentSimFile`` will store the adapted path to the
    current recording resp. Simulation Output (bsig) file, the bpl file will be read using the adapted path.

    sim file selection
    ==================

    To run several valf suites in parallel on HPC the port ``SimSelection`` is set
    to run only one bpl entry for each task (see `Valf` class how to activate).
    If running on HPC only that entry of the bpl according the HPC task number is validated:

      - task T00001  ->  bpl_list[0]
      - task T00002  ->  bpl_list[1]
      - (more)

    **file formats**
    ================

    two different bpl file formats are supported, file extension defines the format:

    .ini file
    =========

    simple list just defining the filenames and paths::

            [SimBatch]
            FileCount=3
            File0="<path>\\<rec-filename1>"
            File1="<path>\\<rec-filename2>"
            File2="<path>\\<rec-filename3>"

    .bpl file
    =========

    xml file format,  supporting one or more time sections for each recording::

            <?xml version="1.0" encoding="UTF-8"?>
            <BatchList>
                <BatchEntry fileName="<path>\\<rec-filename1>">
                    <SectionList>
                        <Section startTime="10000" endTime="19999" />
                        <Section startTime="20000" endTime="29999" />
                    </SectionList>
                </BatchEntry>
                <BatchEntry fileName="<path>\\<rec-filename1>">
                    <SectionList/>
                </BatchEntry>
                <BatchEntry fileName="<path>\\<rec-filename1>">
                    <SectionList/>
                </BatchEntry>
            </BatchList>

    **usage examples**

    let's assume a list of recordings for the bpl with:

      rec1, rec2, rec3

    there are simulation files in ``SimOutputPath``::

        rec1.bsig
        rec1_extract.bsig
        rec1_1hil.bsig
        rec2.bsig
        rec2.csv
        rec2_1hil.bsig
        rec2_2hil.bsig
        rec3.csv
        rec3_hil.csv

    in case given CollectionName does not result in a file, it's assumed you're using a collection from DB.

    minimum setting:
    ================

    (defaults: only \*.csv, no ``ExactMatch``, empty ``SimFileBaseName``, no ``Recurse``, no ``SimSelection``)

    - set ``CollectionName`` to .ini or .bpl file
    - set ``SimOutputPath`` to path where simulation files (\*.bsig, \*.csv) are stored

    > all \*.csv simulation files::

        rec2.csv
        rec3.csv
        rec3_hil.csv

    use bsig simulation files:
    ==========================

    - set ``SimFileExt`` to 'bsig'

    > this will get all \*.bsig files::

        rec1.bsig
        rec1_extract.bsig
        rec1_1hil.bsig
        rec2.bsig
        rec2_1hil.bsig
        rec2_2hil.bsig

    to get both, the \*.csv and \*.bsig files:
    ==========================================

    - set ``SimFileExt`` to ['bsig', 'csv']

    > this will get all files in this SimOutputPath

    to get only sim files without naming expansion like \*_1sim.bsig:
    =================================================================

    - set ``SimFileExt`` to 'bsig'
    - set ``ExactMatch`` to True

    > only rec?.bsig files::

        rec1.bsig
        rec2.bsig

    to get only sim files with naming expansion \*hil.[csv|bsig]:
    =============================================================

    - set ``SimFileExt`` to ['bsig', 'csv']
    - set ``SimFileBaseName`` to 'hil'

    > all rec\*hil.[csv|bsig] files::

        rec1_1hil.bsig
        rec2_1hil.bsig
        rec2_2hil.bsig
        rec3_hil.csv

    specifying exactly the base file name:
    ======================================

    - set ``SimFileExt`` to 'bsig'
    - set ``ExactMatch`` to True
    - set ``SimFileBaseName`` to '_1hil'

    > only rec?_1hil.bsig files::

        rec1_1hil.bsig
        rec2_1hil.bsig

    to get sim files from 2 or more directories:
    ============================================

    - set ``SimOutputPath`` to [r'...\bin60', r'...\bin20]
    - assuming you've got sim1, sim2 and sim3 inside bin60, but missing sim2 inside bin20,

    > through each cycle ``CURRENT_FILE_PORT_NAME`` contains next recording's bin file
      and ``CURRENT_SIMFILE_PORT_NAME`` contains a 2-valued list (same as ``SimOutputPath``)
      each made of all found bin files for each recording::

        #) [[sim1], [sim1]]
        #) [[sim2], []]
        #) [[sim3], [sim3]]


    **further notes**

    The files are ordered in following way:

      - all rec1 based simulation files will be listed first
      - all rec2 based simulation files will follow
      - ... and so on

    (order of rec1, rec2,... as configured in bpl file)

    This means:

    if you need to compare several sim files of one recording in your observer you can simply

      #. configure it as listed in one of the above examples
      #. store first signals internally in the Load method of your observer
      #. store the ``CurrentSimFile`` to compare in next loop
      #. if  ``CurrentSimFile`` has not changed in next LoadData than compare signals of both sim files,
      #. otherwise: mark as error for you

    """

    def __init__(self, data_manager, component_name, bus_name="BUS_BASE", *args, **kwargs):
        """setup default values

        :param data_manager: data manager to pass through
        :param component_name: name of component to pass through (see config)
        :param bus_name: name of bus to use
        :param args: additional argument, just taking version, if not inside keyword
        :keyword version: version info string from MKS (usually)
        :keyword bpl: internal backward compatibility flag for deprecated BplReader
        :keyword cat: internal backward compatibility flag for deprecated CatReader
        """
        BaseComponentInterface.__init__(self, data_manager, component_name, bus_name,
                                        kwargs.pop("version", "$Revision: 1.11 $" if len(args) <= 0 else args[0]))

        self._logger.debug()

        self._curr_sim = None
        self._curr_rec = None

        self._rec_list = None
        self._measid_dict = None
        self._db_based = None
        self._section_dict = None
        self._sim_dict = None
        self._is_sim_path_list = None

        # if we go for deprecated BplReader, we need to align default name
        self._coll_name = COLLECTION_PORT_NAME
        self._coll_label = COLLECTION_LABEL_PORT_NAME
        self._cat_comp = False
        err_log = "using '%s' for now, but please use '%s' in future for %s!"
        if "bpl" in kwargs:
            self._coll_name = PLAY_LIST_FILE_PORT_NAME
            self._logger.info(err_log % (PLAY_LIST_FILE_PORT_NAME, COLLECTION_PORT_NAME, self.__class__.__name__))
        elif "cat" in kwargs:
            self._coll_name = COLLECTION_NAME_PORT_NAME
            self._cat_comp = True
            self._logger.info(err_log % (COLLECTION_NAME_PORT_NAME, COLLECTION_PORT_NAME, self.__class__.__name__))

    def Initialize(self):
        r""" called once by Process_Manager, **reads list of recordings and prepares loop through all entries**

        Only rec files that have sim output files are added to the list, see possible ways to configure
        the selection of sim output files in the class description above.

        Files named \*_tstp.<ext> are used as original time stamp files and do not provide complete simulation output.
        These are excluded from the returned list.

        If running on HPC file server names like **LIFSxxx** in path names of rec files or sim output files
        are replaced with **LIFSxxxS** during initialisation.
        """
        self._logger.debug()

        self._rec_list = []
        self._measid_dict = {}
        self._db_based = None
        self._section_dict = {}
        self._sim_dict = {}
        sim_cnt = 0

        self._set_data(IS_FINISHED_PORT_NAME, False, GLOBAL_BUS_NAME)
        self._set_data(IS_DBCOLLECTION_PORT_NAME, self._db_based)

        # get the collection name and according settings for backward compatibility to CatReader
        tbl_prefix = None
        if self._cat_comp:
            db_bus = self._get_data("DBBus")
            if db_bus is None:
                db_bus = "DBBus#1"
            # MASTER_DB_DBQ_PORT_NAME, MASTER_DB_USR_PORT_NAME, MASTER_DB_PW_PORT_NAME, DB_FILE_PORT_NAME
            db_conn = self._get_data(DB_FILE_PORT_NAME, db_bus)
            if db_conn is None:
                try:
                    db_conn = ""
                    for i, k in (("uid=", MASTER_DB_USR_PORT_NAME),
                                 ("pwd=", MASTER_DB_PW_PORT_NAME)):
                        db_conn += i + self._get_data(k, db_bus) + ';'
                    db_conn = db_conn[:-1]
                    tbl_prefix = self._get_data(MASTER_DB_SPX_PORT_NAME, db_bus)
                except:
                    try:  # this try / except is only to leave unittests unchanged
                        db_conn = self._get_data(DATABASE_OBJECTS_CONN_PORT_NAME, db_bus)[0].db_connection
                    except:
                        db_conn = None

                if db_conn is None:
                    self._logger.error("'%s' or '%s' port was not set." % (DB_FILE_PORT_NAME, MASTER_DB_USR_PORT_NAME))
                    return BaseComponentInterface.RET_VAL_ERROR
        else:
            db_conn = self._get_data(DBCONNECTION_PORT_NAME)

        coll_name = self._get_data(self._coll_name)
        self._set_data(COLLECTIONID_PORT_NAME, None)
        if coll_name is None:
            self._logger.error("'%s' port was not set." % self._coll_name)
            return BaseComponentInterface.RET_VAL_ERROR

        # get collection of files
        try:
            for rec in Bpl(self._uncrepl(coll_name)).read():
                recname = str(rec)
                if recname not in self._rec_list:
                    self._rec_list.append(recname)

                if len(rec.sectionlist) > 0:
                    self._section_dict[recname] = rec.sectionlist
                else:
                    self._section_dict[recname] = []
            self._db_based = False
        except:
            pass

        if len(self._rec_list) == 0 and db_conn is None:
            self._logger.error("no recording in list or collection name not properly set")
            return BaseComponentInterface.RET_VAL_ERROR

        try:
            if self._db_based is None:
                coll_label = self._get_data(self._coll_label)

                def _get_details(src):
                    """grab details of all"""
                    for i in src:
                        if i.type == CollManager.REC:
                            if i.name not in self._rec_list:
                                self._rec_list.append(i.name)
                                self._measid_dict[i.name] = i.id

                            if i.name in self._section_dict:
                                self._section_dict[i.name].append(Section(i.beginrelts, i.endrelts, True))
                            elif i.beginrelts and i.endrelts:
                                self._section_dict[i.name] = [Section(i.beginrelts, i.endrelts, True)]
                            else:
                                self._section_dict[i.name] = []
                        else:
                            _get_details(i)

                collection = Collection(BaseDB(db_conn, table_prefix=tbl_prefix), name=coll_name, label=coll_label)
                self._set_data(COLLECTIONID_PORT_NAME, collection.id)
                _get_details(collection)

                self._db_based = True
        except:
            self._logger.exception("Couldn't open collection: '%s'" % coll_name)
            if self._cat_comp:
                self._logger.exception("you need to specify either '%s' OR ('%s' and '%s' and '%s')"
                                       % (DB_FILE_PORT_NAME, MASTER_DB_USR_PORT_NAME,
                                          MASTER_DB_PW_PORT_NAME, MASTER_DB_SPX_PORT_NAME))
            return BaseComponentInterface.RET_VAL_ERROR
        self._logger.info("Using collection: '%s'." % coll_name)

        self._set_data(IS_DBCOLLECTION_PORT_NAME, self._db_based)

        if len(self._rec_list) == 0:
            self._logger.error("No recording entries found in '%s'" % coll_name)
            return BaseComponentInterface.RET_VAL_ERROR
        else:
            self._logger.info("%d recordings are inside collection" % (len(self._rec_list)))
            # update DB statistics about used recordings
            # try:
            #     # on ice for 2.2.3 as more info needs to be stored and tables slidely redesigned...
            #     with BaseDB('VGA') as stat:
            #         for rec in self._rec_list:
            #             stat.execute("UPDATE %s SET LAST_USAGE = $CD, USAGES = USAGES + 1 "
            #                          "WHERE FILEPATH LIKE '%%%s' ESCAPE '/'"
            #                          % (TABLE_NAME_FILES, opath.splitunc(rec)[1].replace('_', '/_')))
            #         stat.commit()
            # except AdasDBError:
            #     pass  # don't mind if we cannot update, e.g. due to missing network connection

        # do a simulation output check (bisg / csv / ...)
        sim_check = self._get_data(SIMCHECK_PORT_NAME, default=True) in (True, "True")

        # use post selection of sim files if defined
        sim_selection = self._get_data(SIMSELECTION_PORT_NAME)
        if sim_selection is not None:
            sim_selection = eval(sim_selection)
            self._logger.info("'%s' set to '%s'." % (SIMSELECTION_PORT_NAME, str(sim_selection)))

            # select only particular rec files if configured
            # to run on HPC and for developing/debugging usage
            rec_list = []
            for sel in sim_selection:
                rec_list.extend(self._rec_list[slice(*sel) if type(sel) == tuple else slice(sel, sel + 1)])

            self._rec_list = rec_list
            self._logger.info("selected only %s / %d recording file(s)." % (len(rec_list), len(self._rec_list)))

        # now sort recordings
        self._rec_list = sorted(self._rec_list, key=lambda fn: basename(fn), reverse=True)

        if not sim_check:  # we're not checking simulation output files, but rather iterate through recordings
            self._sim_dict = {rec: [[rec]] for rec in self._rec_list}
            self._set_data(FILE_COUNT_PORT_NAME, len(self._sim_dict), GLOBAL_BUS_NAME)
            self._logger.debug("simulation list has %d files" % sim_cnt)
            return BaseComponentInterface.RET_VAL_OK

        # where are sim files ...
        sim_file_path = self._get_data(SIM_PATH_PORT_NAME)
        if sim_file_path is None:
            self._logger.error("'%s' port was not set." % SIM_PATH_PORT_NAME)
            return BaseComponentInterface.RET_VAL_ERROR

        self._is_sim_path_list = type(sim_file_path) == list
        if not self._is_sim_path_list:
            sim_file_path = [sim_file_path]

        sim_file_path = [self._uncrepl(str(abspath(sfp))) for sfp in sim_file_path]
        for sfp in sim_file_path:
            if not isdir(sfp):
                self._logger.error(";-( there is no '%s' like '%s'." % (SIM_PATH_PORT_NAME, sfp))
                return BaseComponentInterface.RET_VAL_ERROR

        # how about the extension of sim files ...
        sim_file_ext = self._get_data(SIMFILEEXT_PORT_NAME)
        if sim_file_ext is None:
            sim_file_ext_list = ["csv"]
            self._logger.info("'%s' port was not set, falling back to '%s'"
                              % (SIMFILEEXT_PORT_NAME, sim_file_ext_list[0]))
        elif type(sim_file_ext) == str:
            sim_file_ext_list = [sim_file_ext]
        elif type(sim_file_ext) in (tuple, list):
            sim_file_ext_list = sim_file_ext
        else:
            self._logger.error("Invalid '%s': '%s'!" % (SIMFILEEXT_PORT_NAME, str(sim_file_ext)))
            return BaseComponentInterface.RET_VAL_ERROR
        sim_file_ext_list = [str(ext).strip('. ') for ext in sim_file_ext_list]

        # base name of sim files ...
        sim_file_base_name = ""
        sim_file_base = self._get_data(SIMFILEBASE_PORT_NAME)
        if sim_file_base is not None:
            sim_file_base_name = sim_file_base

        # Use exact matching or not
        exact_match = self._get_data(EXACTMATCH_PORT_NAME) not in (False, "False", None)
        # wether to do a recurse search
        recurse = self._get_data(RECURSE_PORT_NAME, default=False) in (True, "True")

        # start searching for sim files ...
        bin_files = [[] for _ in sim_file_path]
        for idx in xrange(len(sim_file_path)):
            if recurse:
                for dirname, _, filenames in walk(sim_file_path[idx]):
                    for fname in filenames:
                        bin_files[idx].append(abspath(join(dirname, fname)))
            else:
                for name in listdir(sim_file_path[idx]):
                    bin_files[idx].append(join(sim_file_path[idx], name))

        # go and find related sim files now
        removed_recs = []
        for rec in self._rec_list:
            fname = splitext(basename(rec))[0]
            pattern = ((r"(?i)%s%s(?<!_tstp)\.(%s)$" if exact_match
                        else r"(?i)[\.\w\_\-\+]*%s[\.\w\_\-\+]*%s(?<!_tstp)\.(%s)$") %
                       (fname, sim_file_base_name, "|".join(sim_file_ext_list)))
            sim_files = []
            for bfs in bin_files:
                sim_files.append(sorted([file_.lower() for file_ in bfs
                                         if research(pattern, file_) is not None and isfile(file_)], reverse=True))

            if any(sim_files):
                self._sim_dict[rec] = sim_files
                sim_cnt += sum([len(sfs) for sfs in sim_files])
            else:
                self._logger.warning("No simulation file found for '%s' with given extension(s): %s"
                                     % (rec, str(sim_file_ext_list)))
                removed_recs.append(rec)

        if sim_cnt == 0:
            self._logger.error("No simulation files found for '%s'" % coll_name)
            return BaseComponentInterface.RET_VAL_ERROR

        for rec in removed_recs:
            self._rec_list.remove(rec)

        self._set_data(REMOVED_FILES_PORT_NAME, removed_recs, GLOBAL_BUS_NAME)

        self._logger.debug("simulation list has %d files" % sim_cnt)
        self._set_data(FILE_COUNT_PORT_NAME, sim_cnt, GLOBAL_BUS_NAME)

        return BaseComponentInterface.RET_VAL_OK

    def LoadData(self):
        """ **provides next measurement, sections and simulation result file name**
        on ports ``CurrentFile``, ``CurrentSections`` and ``CurrentSimFile``,

        sets "IsFinished" to True if last file is provided
        """
        self._logger.debug()

        # file_completed self.__data_manager.GetDataPort('IsFileComplete', self._bus_name)
        # next_section_last = self.__data_manager.GetDataPort('NextSection', self._bus_name)

        # Set next measurement and simulation files
        if self._is_sim_path_list:
            self._curr_rec = self._rec_list.pop()
            self._curr_sim = self._sim_dict.pop(self._curr_rec)
        else:
            if self._curr_rec is None or len(self._sim_dict[self._curr_rec][0]) == 0:
                self._curr_rec = self._rec_list.pop()
            self._curr_sim = self._sim_dict[self._curr_rec][0].pop()

        self._set_data(CURRENT_FILE_PORT_NAME, self._curr_rec, GLOBAL_BUS_NAME)
        self._set_data(CURRENT_SIMFILE_PORT_NAME, self._curr_sim)
        self._set_data(CURRENT_SECTIONS_PORT_NAME, self._section_dict[self._curr_rec], GLOBAL_BUS_NAME)
        if self._db_based:
            self._set_data(CURRENT_MEASID_PORT_NAME, self._measid_dict[self._curr_rec])

        self._logger.info("Loading file: '%s'" % self._curr_sim)

        if len(self._rec_list) == 0 and (self._sim_dict and len(self._sim_dict[self._curr_rec][0]) == 0):
            self._set_data(IS_FINISHED_PORT_NAME, True, GLOBAL_BUS_NAME)

        return BaseComponentInterface.RET_VAL_OK


"""
CHANGE LOG:
-----------
$Log: coll_reader.py  $
Revision 1.11 2017/07/09 22:46:40CEST Hospes, Gerd-Joachim (uidv8815) 
add new bsigs to other tests
Revision 1.10 2017/07/09 19:06:46CEST Hospes, Gerd-Joachim (uidv8815)
check for sim files for last rec file, test valf modified to run 2 bsig files for last rec file
Revision 1.9 2016/07/11 15:50:46CEST Mertens, Sven (uidv7805)
removing those 8 pylints
Revision 1.8 2016/07/11 14:57:01CEST Mertens, Sven (uidv7805)
let's use new Catalog fully
Revision 1.7 2016/07/11 13:20:18CEST Mertens, Sven (uidv7805)
some changes missed
Revision 1.6 2016/07/11 12:07:27CEST Mertens, Sven (uidv7805)
enabling CollectionLabel
Revision 1.5 2015/07/31 14:10:50CEST Hospes, Gerd-Joachim (uidv8815)
fix no sim settings
- Added comments -  uidv8815 [Jul 31, 2015 2:10:51 PM CEST]
Change Package : 363124:1 http://mks-psad:7002/im/viewissue?selection=363124
Revision 1.4 2015/07/31 11:42:33CEST Hospes, Gerd-Joachim (uidv8815)
fix back getting next recording if no sim is used
Revision 1.3 2015/07/31 10:34:26CEST Hospes, Gerd-Joachim (uidv8815)
port SimOutputPath can be list of paths
Revision 1.2 2015/07/14 08:25:57CEST Mertens, Sven (uidv7805)
removing unneeded imports
--- Added comments ---  uidv7805 [Jul 14, 2015 8:25:58 AM CEST]
Change Package : 355971:1 http://mks-psad:7002/im/viewissue?selection=355971
Revision 1.1 2015/04/23 19:05:51CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/valf/obs/project.pj
Revision 1.35 2015/04/23 15:18:43CEST Hospes, Gerd-Joachim (uidv8815)
typo
--- Added comments ---  uidv8815 [Apr 23, 2015 3:18:44 PM CEST]
Change Package : 328888:1 http://mks-psad:7002/im/viewissue?selection=328888
Revision 1.34 2015/03/25 11:13:04CET Mertens, Sven (uidv7805)
removing update of DB again as more requirements arose
--- Added comments ---  uidv7805 [Mar 25, 2015 11:13:04 AM CET]
Change Package : 319735:3 http://mks-psad:7002/im/viewissue?selection=319735
Revision 1.33 2015/03/20 14:32:27CET Mertens, Sven (uidv7805)
removing column check
--- Added comments ---  uidv7805 [Mar 20, 2015 2:32:28 PM CET]
Change Package : 319735:1 http://mks-psad:7002/im/viewissue?selection=319735
Revision 1.32 2015/03/20 13:53:56CET Mertens, Sven (uidv7805)
update the update query
--- Added comments ---  uidv7805 [Mar 20, 2015 1:53:57 PM CET]
Change Package : 319735:1 http://mks-psad:7002/im/viewissue?selection=319735
Revision 1.31 2015/03/20 10:30:57CET Mertens, Sven (uidv7805)
update cat_files usage info
--- Added comments ---  uidv7805 [Mar 20, 2015 10:30:58 AM CET]
Change Package : 319735:1 http://mks-psad:7002/im/viewissue?selection=319735
Revision 1.30 2015/03/12 09:03:05CET Mertens, Sven (uidv7805)
- adaptation for uncrepl,
- fix for removed recs list
--- Added comments ---  uidv7805 [Mar 12, 2015 9:03:05 AM CET]
Change Package : 314923:4 http://mks-psad:7002/im/viewissue?selection=314923
Revision 1.29 2015/03/11 16:31:12CET Mertens, Sven (uidv7805)
providing removed (non-found) recording files at global port
--- Added comments ---  uidv7805 [Mar 11, 2015 4:31:13 PM CET]
Change Package : 314923:3 http://mks-psad:7002/im/viewissue?selection=314923
Revision 1.28 2015/03/10 11:52:13CET Mertens, Sven (uidv7805)
changing comment block
--- Added comments ---  uidv7805 [Mar 10, 2015 11:52:13 AM CET]
Change Package : 314142:2 http://mks-psad:7002/im/viewissue?selection=314142
Revision 1.27 2015/03/10 10:05:16CET Mertens, Sven (uidv7805)
blank line inserted
--- Added comments ---  uidv7805 [Mar 10, 2015 10:05:17 AM CET]
Change Package : 314923:2 http://mks-psad:7002/im/viewissue?selection=314923
Revision 1.26 2015/03/10 10:02:20CET Mertens, Sven (uidv7805)
simplyfiying code a bit
--- Added comments ---  uidv7805 [Mar 10, 2015 10:02:21 AM CET]
Change Package : 314923:2 http://mks-psad:7002/im/viewissue?selection=314923
Revision 1.25 2015/03/09 13:59:23CET Mertens, Sven (uidv7805)
fixing sim list
--- Added comments ---  uidv7805 [Mar 9, 2015 1:59:23 PM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.24 2015/03/09 11:48:44CET Mertens, Sven (uidv7805)
fix for recordings count
--- Added comments ---  uidv7805 [Mar 9, 2015 11:48:45 AM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.23 2015/03/09 10:45:01CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Mar 9, 2015 10:45:02 AM CET]
Change Package : 314290:1 http://mks-psad:7002/im/viewissue?selection=314290
Revision 1.22 2015/03/03 11:25:03CET Mertens, Sven (uidv7805)
another docu update
--- Added comments ---  uidv7805 [Mar 3, 2015 11:25:04 AM CET]
Change Package : 312115:1 http://mks-psad:7002/im/viewissue?selection=312115
Revision 1.21 2015/03/03 11:04:22CET Mertens, Sven (uidv7805)
doc update
Revision 1.20 2015/03/03 09:53:36CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Mar 3, 2015 9:53:37 AM CET]
Change Package : 312115:1 http://mks-psad:7002/im/viewissue?selection=312115
Revision 1.19 2015/02/10 19:40:01CET Hospes, Gerd-Joachim (uidv8815)
update docu, fix epydoc errors
--- Added comments ---  uidv8815 [Feb 10, 2015 7:40:02 PM CET]
Change Package : 302321:1 http://mks-psad:7002/im/viewissue?selection=302321
Revision 1.18 2015/02/10 17:51:26CET Hospes, Gerd-Joachim (uidv8815)
add missing methods to get new data manager running
--- Added comments ---  uidv8815 [Feb 10, 2015 5:51:27 PM CET]
Change Package : 271291:4 http://mks-psad:7002/im/viewissue?selection=271291
Revision 1.17 2015/02/09 09:34:46CET Mertens, Sven (uidv7805)
using proper signal defines
--- Added comments ---  uidv7805 [Feb 9, 2015 9:34:46 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.16 2015/02/06 08:16:20CET Mertens, Sven (uidv7805)
MKS???
Revision 1.15 2015/02/06 08:14:50CET Mertens, Sven (uidv7805)
using db_bus settings for collection detail retrieval
instead of unittest used connections
--- Added comments ---  uidv7805 [Feb 6, 2015 8:14:50 AM CET]
Change Package : 303748:1 http://mks-psad:7002/im/viewissue?selection=303748
Revision 1.14 2015/02/03 16:41:59CET Mertens, Sven (uidv7805)
moving to non relative import to check if import error from jenkins is gone
--- Added comments ---  uidv7805 [Feb 3, 2015 4:42:00 PM CET]
Change Package : 301804:1 http://mks-psad:7002/im/viewissue?selection=301804
Revision 1.13 2015/02/03 10:26:24CET Mertens, Sven (uidv7805)
MKS?
--- Added comments ---  uidv7805 [Feb 3, 2015 10:26:25 AM CET]
Change Package : 301804:1 http://mks-psad:7002/im/viewissue?selection=301804
Revision 1.12 2015/02/03 10:23:56CET Mertens, Sven (uidv7805)
adding SimCheck port to be able to not check sinulation outputs
--- Added comments ---  uidv7805 [Feb 3, 2015 10:23:56 AM CET]
Change Package : 301804:1 http://mks-psad:7002/im/viewissue?selection=301804
Revision 1.11 2015/01/22 10:38:42CET Mertens, Sven (uidv7805)
aligning to define of min sqlite version
Revision 1.10 2015/01/12 13:41:51CET Mertens, Sven (uidv7805)
docu update
--- Added comments ---  uidv7805 [Jan 12, 2015 1:41:51 PM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.9 2014/12/19 13:42:58CET Mertens, Sven (uidv7805)
making coll-reader compatible with cat-reader
Revision 1.8 2014/12/19 11:26:54CET Mertens, Sven (uidv7805)
- alignment of BplReader and CollectionReader,
- using walk / listdir without isfile check first to speed up a bit
--- Added comments ---  uidv7805 [Dec 19, 2014 11:26:55 AM CET]
Change Package : 288758:1 http://mks-psad:7002/im/viewissue?selection=288758
Revision 1.7 2014/12/08 14:19:59CET Mertens, Sven (uidv7805)
update coll_reader according UncReplacer
Revision 1.6 2014/11/21 10:19:47CET Hospes, Gerd-Joachim (uidv8815)
update ports class docu
--- Added comments ---  uidv8815 [Nov 21, 2014 10:19:48 AM CET]
Change Package : 282158:1 http://mks-psad:7002/im/viewissue?selection=282158
Revision 1.5 2014/11/20 19:08:20CET Hospes, Gerd-Joachim (uidv8815)
ping removed, speed up of bsig file search
Revision 1.4 2014/11/13 15:03:24CET Mertens, Sven (uidv7805)
strange, PYTHON_HOME doesn't exist on Jenkins!
--- Added comments ---  uidv7805 [Nov 13, 2014 3:03:24 PM CET]
Change Package : 280786:1 http://mks-psad:7002/im/viewissue?selection=280786
Revision 1.3 2014/11/13 12:32:28CET Mertens, Sven (uidv7805)
support for outdated sqlite versions
--- Added comments ---  uidv7805 [Nov 13, 2014 12:32:28 PM CET]
Change Package : 280786:1 http://mks-psad:7002/im/viewissue?selection=280786
Revision 1.2 2014/11/12 14:22:44CET Mertens, Sven (uidv7805)
speedup using listdir from dircache instead
Revision 1.1 2014/11/11 14:18:43CET Mertens, Sven (uidv7805)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/05_Algorithm/STK_ScriptingToolKit/
    04_Engineering/stk/valf/obs/project.pj
"""
