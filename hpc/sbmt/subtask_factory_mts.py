r"""
subtask_factory_mts.py
----------------------

SubTaskFactoryMTS Module for hpc.

**User-API Interfaces**

    - `hpc` (complete package)
    - `SubTaskFactoryMTS` (this module)
"""
# pylint: disable=E1103,W0212
# - import Python modules ----------------------------------------------------------------------------------------------
from os import makedirs, environ, unlink, chmod, walk, rename
from os.path import join, exists, isfile, splitext, abspath, basename, dirname, relpath
from stat import S_IWRITE
from shutil import ignore_patterns, rmtree
from tempfile import NamedTemporaryFile, mkdtemp
from re import sub
from configparser import ConfigParser, ParsingError
from hashlib import sha1
from zipfile import ZipFile, ZIP_DEFLATED
from six import iteritems

# - import HPC modules -------------------------------------------------------------------------------------------------
from ..bpl import Bpl, BplListEntry
from ..core.error import HpcError
from ..core.tds import replace_server_path, DATA_PATH, LOC_HEAD_MAP
from ..core.convert import arg_trans
from ..core.path import merge_path
from ..core.robocopy import Robocopy
from ..core.artifact import articopy
from ..core.logger import deprecated
from ..mts.mts_check import debug_lib_check, check_mts_ini
from ..rdb.catalog import Collection
from .subtask_factory import SubTaskFactory

# - defines ------------------------------------------------------------------------------------------------------------
ACTIVE_ALGOS = 'active_algos'
INACTIVE_ALGOS = 'inactive_algos'
EXPORTERS = 'exporters'
URL_CNT = 'signal_url_count'
WILD_URL_CNT = 'wildcard_url_count'
CHANNEL_SRC = 'channel_sources'
CHANNEL_TYP = 'channel_types'

XCHANGES = [["SynchroCycle", "Fast cycle"], ["Play Speed", "MAX"], ["ReadErrorAction", "2"]]
BPLMODE = "BatchPlayerMode"
GDVPLUS = ['gdvplus.dll', 'gdvplus.pdb']


# - classes ------------------------------------------------------------------------------------------------------------
class MTSCmdHelper(object):  # pylint: disable=R0902
    """
    Command Helper class which handles all MTS specific
    commands for the TaskFactoryMTS.
    """

    def __init__(self, mode="MTS", exist=None, **kwargs):
        """init the helper"""
        self._type = mode
        self._mode = None
        self._exists = exist
        self._cmd_var_list = {'%DataFolder%': '{}\\%JobName%\\2_Output\\%TaskName%\\data'.format(DATA_PATH),
                              '%LogFolder%': '{}\\%JobName%\\2_Output\\%TaskName%\\log'.format(DATA_PATH)}
        self._xparam = kwargs.get("xparam", [])
        if kwargs.get("playexit", True):
            self._xparam.extend(['-pal', '-eab'])

        if mode == "MTS":
            self._cmd_var_list.update({'%MeasAppPath%':
                                           '{}\\%JobName%\\1_Input\\%SubPath%\\measapp.exe'.format(DATA_PATH),
                                       '%SubPath%': kwargs.get("subpath", "mts_system")})
        elif mode == "SIL":
            self._cmd_var_list.update({'%SilLiteAppPath%':
                                           '{}\\%JobName%\\1_Input\\%SubPath%\\sil_lite.exe'.format(DATA_PATH),
                                       '%SubPath%': kwargs.get("subpath", "sil_lite")})
        else:
            raise HpcError("other than 'MTS' or 'SIM' type is not allowed!")

    def get_property(self, key):
        """get a property"""
        return self._cmd_var_list["%{}%".format(key)]

    def set_property(self, key, value):
        """
        set a key replacement to a certain value

        :param obj key: name of key
        :param obj value: value
        """
        self._cmd_var_list['%{}%'.format(key)] = value

    def set_app_path(self, app_path):
        """
        set the path of the mts / sil_lite application, which is used
        by hpc to do the calling. Path of executable.

        Following Variables will be resolved automatically:

            - %JobName%
            - %TaskName%

        :param str app_path: absolute path to measapp.exe
        """
        if app_path is None:
            app_path = "D:\\data\\%JobName%\\1_Input\\%SubPath%\\measapp.exe"
        self._cmd_var_list['%MeasAppPath%' if self._type == "MTS" else "%SilLiteAppPath%"] = app_path

    def set_rec_file_path(self, recfile_path):
        """
        Set the rec file path parameter for mts.

        :param str recfile_path: absolute path to the recfile.
        :raises hpc.HpcError: recfile cannot be set when on SIM mode
        """
        if self._mode == "sim":
            raise HpcError("not allowed to set rec file path!")
        self._set_file_path(recfile_path, 'rec')

    def set_sim_file_path(self, simfile_path):
        """
        Set the sim file path parameter for SIL lite.

        :param str simfile_path: absolute path to the recfile.
        :raises hpc.HpcError: recfile cannot be set when on SIM mode
        """
        if self._mode == "rec":
            raise HpcError("not allowed to set sim file path!")
        self._set_file_path(simfile_path, 'sim')

    def _set_file_path(self, file_path, mode):
        """set path of file and mode"""
        if self._exists:
            if self._exists("SELECT COUNT(MEASID) FROM DMT_FILES WHERE LOWER(FILEPATH) LIKE :path "
                            "AND STATUS = 'transmitted'", path=file_path.lower())[0][0] == 0:
                raise HpcError("'%s' doesn't exist!" % file_path)

        self._mode = mode
        self._cmd_var_list['%{}File%'.format(mode.capitalize())] = file_path

    def set_bpl_file_path(self, bplfile_path):
        """
        set the bpl file path parameter for MTS / SIL.

        :param str bplfile_path: absolute path to the recfile, typically a subfolder under %JobName%/1_Input
        """
        self._mode = 'bpl'
        self._cmd_var_list['%BatchFile%'] = bplfile_path

    @property
    def cfg_file(self):
        """
        :return: full path to config file
        :rtype: str
        """
        return join(self.get_property('CfgPath'), self.get_property('CfgName'))

    def get_cmd_list(self, cmd_asis=False):  # pylint: disable=W0613
        r"""
        prepare the whole cmd_list, either for \*.bpl or \*.rec usage.
        Replace all internal used placeholder with the data given by the user,
        and provide it to the user.

        :param bool cmd_asis: compatibility parameter for CmdHelper class (as of broken Popen), not used here
        :return: command line as list
        :rtype: list
        :raises hpc.HpcError: once, path is not specified
        """
        if self._type == "MTS":
            if self._mode == 'rec':
                cmd_list = ['%MeasAppPath%', '-norestart', '-silent', '-pc%CfgPath%', '-lc%CfgName%', '-lr%RecFile%']
            elif self._mode == 'bpl':
                cmd_list = ['%MeasAppPath%', '-norestart', '-silent', '-pc%CfgPath%', '-lc%CfgName%', '-lb%BatchFile%']
            else:
                raise HpcError("file path not specified, set it first!")
        else:
            if self._mode == 'sim':
                cmd_list = ['%SilLiteAppPath%', '-pc%CfgPath%', '-cfg%CfgPath%' + '\\' + '%CfgName%',
                            '-meas_pathd:\\data\\%JobName%\\1_Input\\mts_measurement', '-lr%SimFile%']

            elif self._mode == 'bpl':
                cmd_list = ['%SilLiteAppPath%', '-silent', '-cfg%CfgPath%\\%CfgName%', '-pc%CfgPath%', '-lb%BatchFile%']
            else:
                raise HpcError("file path not specified, set it first!")

        cmd_list.extend(['-pd' + self._cmd_var_list['%DataFolder%'], '-pl' + self._cmd_var_list['%LogFolder%']])
        cmd_list.extend(self._xparam)
        cmd_list = self._replace(cmd_list)

        return cmd_list

    def get_cmd_var_list(self):
        """
        return the whole cmd_var_list, which is a dictionary.

        :return: cmd_var_list
        :rtype: dict
        """
        return self._cmd_var_list

    @property
    def command(self):
        """
        :return: actual command
        :rtype: str
        """
        return " ".join(self.get_cmd_list())

    @property
    def cwd(self):
        """
        :return: working directory
        :rtype: str
        """
        return dirname(self._replace([self._cmd_var_list['%MeasAppPath%'
                                                         if self._type == "MTS" else "%SilLiteAppPath%"]])[0])

    def _replace(self, cmd_list):
        """replace with real values"""
        for _ in range(2):
            for i, v in enumerate(cmd_list):
                if "%" not in v:
                    continue
                for item, repl in iteritems(self._cmd_var_list):
                    cmd_list[i] = sub("(?i)" + item, repl.replace("\\", "\\\\"), v)
                    if v != cmd_list[i]:
                        break
        return cmd_list


class SubTaskFactoryMTS(SubTaskFactory):  # pylint: disable=R0902
    """
    .. inheritance-diagram:: hpc.SubTaskFactoryMTS

    Specialized class for creating Hpc SubTasks which run out MTS.

    - Typical usage is first to set all information,
      which is the same for all Tasks. (SetConfigFolder,SetConfigFile,...)
    - After that, multiple calls of the "create_task"
      -> for the real MTS-Task creation.
    - This class is derived from the `SubTaskFactory`,
      this means all methods from there can also be used.
    - a private check method is registered to be executed in Job.submit() checking
      the availability of the MTS config file.
    """

    def __init__(self, hpc, **kwargs):
        r"""
        :param hpc.Job hpc: hpc job class
        :param dict kwargs: see below

        :keyword \**kwargs:
            * *io_watch* (``bool``): whether watchdog shall watch io traffic
            * *cpu_watch* (``bool``): whether watchdog shall track cpu usage
            * *time_watch* (``float``): whether watchdog shall monitor time [h]
            * *prn_watch* (``bool``): whether watchdog shall watch the printout
            * *time_factor* (``float``): default 16 x recording length
            * *loglevel* (``int``): use a certain logging level (mts_check)
            * *exist* (``bool``): check existence of recording, default: False
            * *mtscheck* (``bool``): check MTS log files for problems, default: False
            * *skipon* (``list``): continue on certain exitcodes of previous subtask, e.g. [-302, -402]
            * *cfg_blacklist* (``list[str]``): blacklisted MTS / SilLite config sections
            * *wrapexe* (``str``): executable wrapped around each sub task
        """
        mode = kwargs.pop("mode", "MTS")
        SubTaskFactory.__init__(self, hpc, mode=mode, **kwargs)

        self._checker = kwargs.get('mtscheck', False)
        self._cfg_blacklist = kwargs.get('cfg_blacklist', ["EMGenericBv", "EMObjectList"])
        self._cfg_name = None
        self._fake_copy = False

        try:
            makedirs(join(self._hpc.sched.net_in_path, 'bpl'))
        except Exception:
            pass

        self._cmd_helper = MTSCmdHelper(mode=self._type,
                                        exist=self._hpc.base_db if kwargs.pop('exist', False) else None, **kwargs)

        self._rec_mapping = kwargs.get("map_rec", True)

    def _check_mts_cfg(self, cfg_path, cfg_name, prev=None):  # pylint: disable=R0912,R0915,R1260
        """check MTS config file"""
        cfg = ConfigParser(allow_no_value=None, delimiters=('=',))
        cfg.optionxform = str
        currcfg = merge_path(cfg_path, cfg_name)
        if not self._fake_copy and "$" not in currcfg and not exists(currcfg):
            msg = "config file {} does not exist!".format(currcfg)
            if prev:
                self._hpc.logger.warning(msg)
            else:
                raise HpcError(msg)
        cfg.read(currcfg, 'utf-8-sig')
        rewrite = False

        for section in cfg.sections():
            if cfg.has_option(section, 'ChannelSources'):
                for k, v in (('ChannelSources', CHANNEL_SRC,), ('ChannelTypes', CHANNEL_TYP,)):
                    ci = cfg.get(section, k, fallback="")
                    self._simcfg[v].extend(list([_f for _f in (x.strip(' \n\\,"\'') for x in ci.splitlines()) if _f]))

            if 'Exporter' in section:
                self._simcfg[URL_CNT] += int(cfg.get(section, 'Signal URL Count', fallback=0))
                self._simcfg[WILD_URL_CNT] += int(cfg.get(section, 'Wildcard URL Count', fallback=0))
                self._simcfg[EXPORTERS] += 1
                if not int(cfg.get(section, 'Is Exporting', fallback="0")):
                    self._hpc.logger.error("'Is Exporting' option not set, you might get no output!")

            elif 'SIM VFB' in section:
                if cfg.has_option(section, 'SWC Plugin Folder') and cfg.has_option(section, 'SWC Plugin'):
                    self._check_mts_cfg(cfg_path,
                                        join(cfg.get(section, 'SWC Plugin Folder').strip(' ".\\'),
                                             cfg.get(section, 'SWC Plugin').strip(' "')).replace('\\\\', '\\'),
                                        section)

            elif section == "MTS Player V2":
                if cfg.has_option(section, BPLMODE):
                    self._playsections = bool(int(cfg.get(section, BPLMODE)))
                if cfg.has_option(section, "LoggingServerAddress"):
                    cfg.set(section, "LoggingServerAddress", "")
                    rewrite = True

                for k, v in XCHANGES:
                    if not cfg.has_option(section, k) or cfg.get(section, k) != v:
                        self._hpc.logger.warning("'%s' option not set to %s!", k, v)
                        cfg.set(section, k, v)
                        rewrite = True

            elif prev is not None:
                if cfg.has_option(section, 'SimCfgFile'):
                    if section not in self._simcfg[ACTIVE_ALGOS] and cfg.get(section, 'SimCfgFile').find('_meas') >= 0:
                        self._simcfg[ACTIVE_ALGOS].append(section)
                        self._check_mts_cfg(cfg_path, cfg.get(section, 'SimCfgFile').replace('$UserPathCfg$\\', ''),
                                            section)
                    elif section not in self._simcfg[INACTIVE_ALGOS]:
                        self._simcfg[INACTIVE_ALGOS].append(section)

                elif cfg.has_option(section, 'PluginFile'):
                    self._simcfg[section + "_" + prev] = sorted([cfg.get(section, 'PluginFile').split('\\')[-1]])

        if prev is None:
            self._simcfg[ACTIVE_ALGOS] = sorted(self._simcfg[ACTIVE_ALGOS])
            self._simcfg[INACTIVE_ALGOS] = sorted(self._simcfg[INACTIVE_ALGOS])
            self._simcfg[CHANNEL_SRC] = list(set(self._simcfg[CHANNEL_SRC]))
            self._simcfg[CHANNEL_TYP] = list(set(self._simcfg[CHANNEL_TYP]))

        if rewrite:
            chmod(currcfg, S_IWRITE)
            with open(currcfg, "w") as cfp:
                cfg.write(cfp, False)
            self._hpc.changes.append("manipulated: " + currcfg)

        return cfg

    def set_app_path(self, app_path=None):
        """
        Provide the possibility to set the path to MTS / sil_lite
        to the correct one, if the default path can't be used.

        :note: %JobName% will be replaced with the real JobName.

        :param app_path:   Absolute path to the measapp.exe, which is used to start the Task.
        :type app_path:    str
        """
        self._cmd_helper.set_app_path(app_path)

    @deprecated("that option is not supported any longer")
    def set_split_section(self, value):
        """
        set split_section for section based exports of MTS

        :param bool value: True/False
        """

    def set_config_folder(self, folder):
        """deprecate !!!"""
        self._cmd_helper.set_property('CfgPath', folder)

    def set_config_file_name(self, filename):
        """deprecate !!!"""
        self._cmd_helper.set_property('CfgName', filename)

    def set_config(self, folder, file_name):
        """
        Set the folder, where MTS / sil_lite will find the given config file.
        This folder will also be used, if you have multiple configuration,
        which depends via a relative path from each other.
        So this Folder will also be used as the base config folder to resolve
        the relative paths to other given config files.

        Set the config file name, which shall be used.
        This FileName can also contain a relative path to the config file,
        if the Base Config Folder feature is needed.
        Please see also `SubTaskFactoryMTS.SetConfigFolder`

        :param str folder: path to base config folder
        :param str file_name: relative path to config file
        :raises hpc.HpcError: raised when either folder of file is empty
        """
        if not folder or not file_name:
            raise HpcError("folder or file_name to MTS config is empty!")
        self._cmd_helper.set_property('CfgPath', join(self._hpc.sched.client_in_path, folder))
        self._cmd_helper.set_property('CfgName', file_name)

    def set_data_folder(self, data_folder):
        r"""
        Set output data folder for MTS to a different than standard:
        "D:\\data\\%JobName%\\2_Output\\%TaskName%\\data"

        :param data_folder:   path to the output data folder on the hpc-client.
        :type data_folder:    str
        """
        self._cmd_helper.set_property('DataFolder', data_folder)

    def set_parameter(self, param, value):
        """set an extra parameter's value"""
        self._cmd_helper.set_property(param, value)

    def _get_task_create_mode(self, bpl_rec_file_path):
        r"""
        Analyze a given input file, if we have rec file mode or \*.bpl file mode.
        When unsupported File format will be found, a exception will be raised.

        :param str bpl_rec_file_path: Bpl / Rec File URL which must be used for MTS.
                                      Type depends on initializer mod ('rec', 'bpl')
        :return: mode ('rec'|'bpl')
        :rtype: str
        :raises hpc.HpcError: once we have an unsupportd type
        """
        if isinstance(bpl_rec_file_path, BplListEntry):
            return 'bpl'

        ext = splitext(str(bpl_rec_file_path))[1].lower()
        if ext in (".rec", ".rev", ".rrec", ".dat", ".mf4",):
            return 'rec'
        if ext == '.mron':
            return 'mron'
        if ext == '.sim':
            return 'sim'
        if ext == '.bpl':
            return 'bpl'
        if (isinstance(bpl_rec_file_path, (tuple, list)) and
                self._hpc.base_db("SELECT COUNT(*) FROM COLLECTIONS WHERE NAME = :coll AND (CP_LABEL %s)"
                                  % ("IS NULL OR CP_LABEL = ''" if bpl_rec_file_path[1] is None else
                                     ("= '%s'" % bpl_rec_file_path[1])), coll=bpl_rec_file_path[0])[0][0] > 0):
            return 'coll'
        raise HpcError('Unsupported file type: {0}'.format(ext[1:]))

    def create_task(self, bpl_rec_file_path, **kwargs):  # pylint: disable=R0912,R0915,R1260,W0221
        r"""
        Create a single SubTask based on a given \*.bpl file or a given
        \*.rec file for MTS or a \*.sim file for sil_lite.
        If checker is enabled, it will automatically create also a checker task.

        note: for additional parameters, please review `subtask_factory.create_task` as well

        :param str bpl_rec_file_path: Bpl / Rec / Sim file URL which must be used for MTS / sil_lite.
                                      Type depends on initializer mod ('rec', 'bpl')
        :param dict kwargs: see below
        :keyword \**kwargs:
            * *checker* (``bool``): Enables a second SubTask which checks the MTS / sil_lite Output (xlog, crash)
        :return: created SubTaskList
        :rtype:  list[int]
        :raises hpc.HpcError: in case of a unicode encode problem, reading config
        """
        mode = self._get_task_create_mode(bpl_rec_file_path)
        if mode == 'coll':
            mode = 'bpl'
            bpl_file = join(environ["TEMP"], bpl_rec_file_path[0] +
                            ("" if bpl_rec_file_path[1] is None else bpl_rec_file_path[1]) + ".bpl")
            Collection(self._hpc.base_db, name=bpl_rec_file_path[0], label=bpl_rec_file_path[1]).export_bpl(bpl_file)
            bpl_rec_file_path = bpl_file

        if mode == 'rec':
            self._check_server_url(bpl_rec_file_path)
            bpl_rec_file_path = replace_server_path(bpl_rec_file_path)
            self._cmd_helper.set_rec_file_path(bpl_rec_file_path)
        elif mode == 'mron':
            self._cmd_helper.set_rec_file_path(bpl_rec_file_path)
        elif mode == 'sim':
            self._check_server_url(bpl_rec_file_path)
            bpl_rec_file_path = replace_server_path(bpl_rec_file_path)
            self._cmd_helper.set_sim_file_path(bpl_rec_file_path)

        elif mode == 'bpl':
            with Bpl(bpl_rec_file_path) as bplin:
                for rec in bplin:
                    for rfp in rec.filepath:
                        self._check_server_url(rfp)
                # copy *.bpl to server if not already there
                dest = join(self._hpc.sched.net_in_path, 'bpl', splitext(basename(bplin.filepath))[0] + ".bpl")
                if bpl_rec_file_path != dest:
                    bpl_rec_file_path = dest
                    with Bpl(dest, "w") as bplout:
                        for entry in bplin:
                            bplout.append(entry)

            # modify path to bpl on node
            self._cmd_helper.set_bpl_file_path(join(DATA_PATH, "%JobName%\\1_Input\\bpl", basename(bpl_rec_file_path)))

        cfg_path = join(self._hpc.sched.net_in_path,
                        self._cmd_helper.cfg_file.split(self._hpc.sched.client_in_path.rstrip('\\') + '\\')[-1])

        if not self._hpc.mts_zips and self._cfg_name != self._cmd_helper.get_property('CfgName'):
            cfg = None
            if self._type == "MTS":
                self._simcfg[ACTIVE_ALGOS] = []
                self._simcfg[INACTIVE_ALGOS] = []
                self._simcfg[EXPORTERS] = 0
                self._simcfg[URL_CNT] = 0
                self._simcfg[WILD_URL_CNT] = 0
                self._simcfg[CHANNEL_SRC] = []
                self._simcfg[CHANNEL_TYP] = []

                try:
                    cfg = self._check_mts_cfg(join(self._hpc.sched.net_in_path, self._cmd_helper.get_property('CfgPath')
                                                   .split(self._hpc.sched.client_in_path)[-1].strip('\\')),
                                              self._cmd_helper.get_property('CfgName'))
                except UnicodeEncodeError as ex:
                    raise HpcError("config contains some illegal chars, please check it: {!s}".format(ex))
                except ParsingError as ex:
                    raise HpcError("config syntax error: {!s}".format(ex))

            # we have a blacklist, so we need to parse our config file
            if self._cfg_blacklist:
                if cfg is None:
                    cfg = ConfigParser(allow_no_value=True, delimiters=('=',))
                    cfg.optionxform = str
                    try:
                        cfg.read(cfg_path, encoding='utf-8-sig')
                    except UnicodeEncodeError as ex:
                        raise HpcError("config contains some illegal chars, please check it: {!s}".format(ex))
                cfg_path = splitext(cfg_path)

                # but do we need to rewrite it, did we find blacklisted sections?
                if set(cfg.sections()).intersection(set(self._cfg_blacklist)):
                    with NamedTemporaryFile(dir=dirname(cfg_path[0]), prefix=basename(cfg_path[0]) + '_',
                                            suffix=cfg_path[1], delete=False) as filep:
                        cfg.write(filep)
                    oname = self._cmd_helper.get_property('CfgName')
                    self._cmd_helper.set_property('CfgName', oname.replace(basename(oname), basename(filep.name)))
                    self._hpc.changes.append("adaptation: " + oname)

                # in case users set's another config in the middle (loop)
                self._cfg_name = self._cmd_helper.get_property('CfgName')

        kwcopy = dict(kwargs)
        return self._create_task(self._cmd_helper, recording=bpl_rec_file_path, rec_map=self._rec_mapping,
                                 local_rec=kwcopy.pop('local_rec', self._local_rec),
                                 mtscheck=kwcopy.pop('checker', self._checker), **kwcopy)

    def create_tasks(self, bpl_file_path, checker=True, **kwargs):
        r"""
        create a multiple SubTask based on a given \*.bpl file
        If bpl file entry contains a section, then a bpl file based task
        will be created, and also the needed split new bpl file with this
        single entry. If bpl file entry is without sections, the task creation
        will use directly the \*.rec file path as argument.
        If checker is enabled, it will automatically create also a checker task.

        Note: for additional parameters, please review `subtask_factory.create_task` as well

        :param str bpl_file_path: bpl file URL which must be used for MTS / sil_lite.
        :param bool checker: enables a second SubTask which checks the MTS Output (xlog, crash)
        :param dict kwargs: see below
        :return: SubTaskList
        :rtype: list[int]
        """
        sub_tasks = []

        with Bpl(bpl_file_path, db="VGA_PWR", ignore_missing=kwargs.get("ignore_missing", False),
                 loc=next((k for k, v in iteritems(LOC_HEAD_MAP) if self._hpc.head_node in v), '')) as bpl:
            for item in bpl:
                if item.is_simple:
                    sub_tasks += self.create_task(item.filepath[0], checker=checker, **kwargs)
                else:
                    self._hpc.bpl_cnt += 1
                    bpl_file = join(self._hpc.sched.net_in_path, 'bpl', "rec{:05d}.bpl".format(self._hpc.bpl_cnt))
                    item.save(bpl_file)
                    sub_tasks += self.create_task(bpl_file)

            # for bplf, item in BplSplitter(self._hpc, bpl_file_path):
            #     # Check if entry contains sections
            #     if bplf:  # use the created bpl file
            #         sub_tasks += self.create_task(item, checker=checker, **kwargs)
            #     else:  # just use the rec file
            #         sub_tasks += self.create_task(str(item), checker=checker, **kwargs)

        return sub_tasks

    def copy_mts_folders(self, *args, **kwargs):  # pylint: disable=R0912,R0914,R0915,R1260
        r"""
        copy MTS folders from default (or given) directories and
        omit unneeded mts files and folders that are not needed in offline simulation

        :param \*args: *mts_sys_folder_name*, *mts_measure_folder_name*, *use_filter*, *mts_sys_dest*
                       and *mts_measure_dest* can be given, others are optional (kwargs)

        :keyword \**kwargs:
            * *mts_sys_folder_name* (``str``): MTS system folder path
            * *mts_measure_folder_name* (``str``): MTS measurement folder path
            * *use_filter* (``bool``): deactivate ignore filter, default: True
            * *mts_sys_dest* (``str``): destination path for mts_system
            * *mts_measure_dest* (``str``): destination path for mts_measurement
        :raises hpc.HpcError: on copy error
        :raises ValueError: in case path cannot be found
        """
        # mts_sys_folder_name=r'.\mts_system', mts_measure_folder_name=r'.\mts_measurement',
        # use_filter=False, mts_sys_dest=r'mts_system', mts_measure_dest=r'mts_measurement'
        opts = arg_trans([['mts_sys_folder_name', '.\\' + self._cmd_helper.get_cmd_var_list()['%SubPath%']],
                          ['mts_measure_folder_name', r'.\mts_measurement'], ['use_filter', True],
                          ['mts_sys_dest', self._cmd_helper.get_cmd_var_list()['%SubPath%']],
                          ['mts_measure_dest', r'mts_measurement']], *args, **kwargs)

        if "debug_run" in kwargs:
            self._hpc.logger.warning("debug_run parameter is deprecated, please don't use any longer!")

        self._cmd_helper.set_property("SubPath", opts["mts_sys_dest"])

        self._fake_copy = kwargs.get("fake_copy", False)
        if self._fake_copy:
            return

        tmpdir = None
        if opts["mts_sys_folder_name"].startswith("http"):
            tmpdir = mkdtemp(prefix='mts_')
            articopy(opts["mts_sys_folder_name"], tmpdir, self._hpc.logger)
            opts.update({"mts_sys_folder_name": join(tmpdir, "mts_system"),
                         "mts_measure_folder_name": join(tmpdir, "mts_measurement")})

        # check for correct mts_system path
        if not exists(abspath(opts['mts_sys_folder_name'])):
            raise ValueError("can't find path '" + opts['mts_sys_folder_name'] + "'")

        if not exists(abspath(opts['mts_measure_folder_name'])):
            raise ValueError("can't find path '" + opts['mts_measure_folder_name'] + "'")

        # Check if mts.ini file is correct
        if self._type == "MTS":
            if check_mts_ini(join(opts['mts_sys_folder_name'], 'mts.ini'), basename(opts['mts_measure_dest'])):
                self._hpc.changes.append("manipulated: " + join(opts['mts_sys_folder_name'], 'mts.ini'))
            exe = join(opts['mts_sys_folder_name'], 'measapp.exe')
        else:
            exe = join(opts['mts_sys_folder_name'], 'sil_lite.exe')

        if not isfile(exe):
            raise HpcError("%s not found in %s" % (basename(exe), dirname(exe)))

        for i in debug_lib_check(opts['mts_sys_folder_name']):
            self._hpc.logger.warning("debug DLL found: %s", i[len(opts['mts_sys_folder_name']) + 1:])
        # short_test = self._hpc.sched.template in ("Short_Test", "WSN_Test")
        # if not short_test and debug_lib_check(opts['mts_sys_folder_name']):
        #     raise HpcError("Debug dll's are only allowed in the 'Short_Test' template. Found debug dlls: %s"
        #                    % opts['mts_sys_folder_name'])

        self._hpc.logger.info("copying MTS package (%s) to job's path", dirname(opts['mts_sys_folder_name']))
        mts_filter = GDVPLUS
        # if not short_test:
        #     mts_filter.append("*.pdb")
        if opts['use_filter'] is True:
            # *.pdb added here instead
            mts_filter.extend(['doc*', 'lib', 'include', 'mi4_system_driver', 'MTSV2AppWizard', 'www', '*.bsig',
                               'CrashRep_measapp_*.*', 'CrashReport.*', 'errmon_*.*', 'errorlog.*', '*.pdb'])
        mts_filter = ignore_patterns(*mts_filter)

        replace = {}
        if self._type == "MTS":
            if not self._hpc.job_sim:
                replace['*.par'] = [(r'[GenericDrawActive].Value=1', r'[GenericDrawActive].Value=0',)]

        if opts['zip'] and not self._hpc.job_sim:
            tmpfn = join(self._hpc.sched.net_in_path, "mts.zip")
            with ZipFile(tmpfn, 'w', ZIP_DEFLATED, allowZip64=True) as zfp:
                for path in (abspath(opts['mts_sys_folder_name']), abspath(opts['mts_measure_folder_name']),):
                    for root, _dirs, files in walk(path):
                        # what we need to ignore
                        ignored = mts_filter(root, files)
                        self._hpc.changes.extend(["ignored: {}".format(join(root, i)) for i in ignored])

                        for file in set(files) - ignored:
                            fpath = join(root, file)
                            rel = relpath(fpath, dirname(path))
                            zfp.write(fpath, rel)
            hsh = sha1()
            for i in zfp.infolist():
                hsh.update(str(i).encode())
            hx = hsh.hexdigest()
            for i in range(33, 0, -1):
                hxfn = join(self._hpc.sched.net_in_path, hx[i:])
                if not exists(hxfn):
                    rename(tmpfn, hxfn)
                    self._hpc.mts_zips.append(hx[i:])
                    break
            else:
                opts['zip'] = False
                unlink(tmpfn)

        if not opts['zip']:
            robo = Robocopy(verbose=0, progress=kwargs.get('progress', False), ignore=mts_filter, replace=replace,
                            stat=False)
            # copy mts_system and mts_measurement
            robo.copy(abspath(opts['mts_sys_folder_name']),
                      join(self._hpc.sched.net_in_path, opts['mts_sys_dest']))
            robo.copy(abspath(opts['mts_measure_folder_name']),
                      join(self._hpc.sched.net_in_path, opts['mts_measure_dest']))

            self._hpc.changes.extend(robo.changes)

        if tmpdir:
            rmtree(tmpdir, ignore_errors=True)

        if self._cfg_name is not None:  # let's remove temp config again...
            try:
                unlink(self._cfg_name)
            except Exception as _:  # pragma: no cover
                pass
        self._hpc.logger.info("MTS package copy finished")
