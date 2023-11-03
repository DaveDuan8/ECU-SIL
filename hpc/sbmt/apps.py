"""
app_helper.py
-------------

helper for :class:`hpc.Job` to encapsulate e.g. MTS or any other application
"""
# # pylint: disable=all
# # - Python imports ---------------------------------------------------------------------------------------------------
# from os import chmod, makedirs, listdir
# from os.path import join, basename, dirname, isfile, exists
# from collections import OrderedDict
# from shutil import ignore_patterns
# from re import match
# from stat import S_IWRITE
# from configparser import ConfigParser
#
# # - HPC imports ------------------------------------------------------------------------------------------------------
# from hpc.core.error import HpcError
# from hpc.core.robocopy import Robocopy
# from hpc.mts.mts_check import check_mts_ini, debug_lib_check
# from hpc.core.path import merge_path
# from hpc.bpl import Bpl, BplListEntry
#
# # - defines ----------------------------------------------------------------------------------------------------------
# ACTIVE_ALGOS = 'active_algos'
# INACTIVE_ALGOS = 'inactive_algos'
# EXPORTERS = 'exporters'
# URL_CNT = 'signal_url_count'
# WILD_URL_CNT = 'wildcard_url_count'
# CHANNEL_SRC = 'channel_sources'
# CHANNEL_TYP = 'channel_types'
#
# XCHANGES = [["SynchroCycle", "Fast cycle"], ["Play Speed", "MAX"], ["ReadErrorAction", "2"]]
# BPLMODE = "BatchPlayerMode"
# GDVPLUS = ['gdvplus.dll', 'gdvplus.pdb']
#
#
# # - classes / functions ----------------------------------------------------------------------------------------------
# class App(object):
#     """application encapsulation, aka CmdHelper"""
#
#     def __init__(self, **kwargs):
#         r"""
#         command line helper for any command
#
#         :keyword \**kwargs:
#             * *job* (``hpc.Job``): Job reference to copy MTS to destination and filter properly, *mandatory*
#         """
#         self._job = kwargs.pop("job")
#         self._kwargs = kwargs
#         self._cmd = self._kwargs.pop("cmd")
#         self._app = self._kwargs.pop("app", "APP")
#         self._dst = self._kwargs.pop("dst", join(self._job.job_folder, "1_Input"))
#         self._cfg = self._kwargs.pop("simcfg", OrderedDict())
#         self._rec = self._kwargs.pop("recording", None)
#         self._playsecs = False
#
#     def __str__(self):
#         """
#         command line
#
#         :return: command line
#         :rtype: str
#         """
#         return self._cmd
#
#     def cmd_list(self, asis=False):
#         """
#         change command line to list
#
#         :return: cmd as list
#         :rtype: list
#         """
#         if asis or isinstance(self._cmd, list):
#             return self._cmd
#
#         # parse the cmdline and create a list out of it
#         arg, part, in_string = [], '', False
#         for char in self._cmd:
#             if char == '"':
#                 in_string = not in_string
#             elif char == ' ' and not in_string:
#                 arg.append(part)
#                 part = ''
#             else:
#                 part += char
#         # append last part
#         if part != '':
#             arg.append(part)
#
#         return arg
#
#     @property
#     def cwd(self):
#         """
#         working directory
#
#         :return: working directory
#         :rtype: str
#         """
#         return self._kwargs.get("cwd", "")
#
#     @property
#     def app(self):
#         """
#         application
#
#         :return: app type
#         :rtype: str
#         """
#         return self._app
#
#     @property
#     def simcfg(self):
#         """
#         return simulation configuration
#
#         :return: simulation config
#         :rtype: str
#         """
#         return self._cfg
#
#     @property
#     def playsecs(self):
#         """
#         play sections config
#
#         :return: MTS should play sections?
#         :rtype: bool
#         """
#         return self._playsecs
#
#     @property
#     def recording(self):
#         """
#         return recording's name
#
#         :return: recording in use
#         :rtype: str
#         """
#         return self._rec
#
#     def __add__(self, other):
#         """
#         add another part to command line and return them together, e.g. a recording
#
#         :param (``str`` | ``hpc.bpl.bpl_cls.BplListEntry``) other:
#         :return: command line
#         :rtype: str
#         """
#         return "{} {}".format(self._cmd, str(other))
#
#     def copy(self, items=None, dst=None):
#         """
#         copy sources to destination
#
#         :param (``list``) items: list of items to be copied
#         :param (``str``) dst: destination folder to copy things to, defaults to __init__(dst=...)
#         """
#         dst = dst if dst else self._dst
#         if dst is None:
#             raise HpcError("destination folder unknown, please specify!")
#
#         robo = Robocopy(verbose=0, stat=False)
#         for i in items:
#             robo.copy(i, dst)
#
#
# class Mts(App):
#     r"""
#     command line helper for MTS
#
#     :keyword \**kwargs:
#         * *sys_dir* (``str``): MTS's system path, *mandatory*
#         * *meas_dir* (``str``): MTS's measurement path, dereived from *sys_path* (..\mts_measurement) if left empty
#         * *job* (``hpc.Job``): Job reference to be able to copy MTS to destination and filter properly, *mandatory*
#         * *cfg_dir (``str``): config dir relative to `mts_measurment` folder, *mandatory*
#         * *cfg_name (``str``): config file path beyond `cfg_dir`, *mandatory*
#         * *use_filter* (``bool``): copy filter, not copying e.g. docs, libs, bsigs, logs, etc., default: True
#     """
#
#     def __init__(self, **kwargs):  # pylint: disable=R1260,R0912
#         """MTS encapsulation"""
#         sys_dir = kwargs["sys_dir"]
#         meas_dir = kwargs.get("meas_dir", join(dirname(sys_dir), "mts_measurement"))
#
#         App.__init__(self, app="MTS", cmd=r"D:\data\%JobName%\1_Input\{}".format(basename(sys_dir)), **kwargs)
#
#         self._jobfldr = basename(self._job.job_folder)
#         cfg_path = join(meas_dir, kwargs["cfg_dir"], kwargs["cfg_name"])
#         cfg_blacklist = kwargs.get('cfg_blacklist', ["EMGenericBv", "EMObjectList"])
#
#         self._cmd = self._cmd.replace("%JobName%", self._jobfldr)
#
#         # check if mts.ini file is correct
#         if self._app == "MTS":
#             if check_mts_ini(join(sys_dir, 'mts.ini'), basename(meas_dir), HpcError):
#                 self._job.logger.warning("mts.ini rewrote, as AllowMultipleInstances wasn't set to '1'!")
#                 self._job.changes.append("manipulated: " + join(sys_dir, 'mts.ini'))
#             exe = join(sys_dir, 'measapp.exe')
#             self._cmd = [join(self._cmd, "measapp.exe"), '-pal', '-eab', '-norestart', '-silent',
#                          '-pc' + join(dirname(self._cmd), "mts_measurement", kwargs["cfg_dir"]),
#                          '-lc' + kwargs["cfg_name"],
#                          '-pdD:\\data\\{}\\2_Output\\%TaskName%\\data'.format(self._jobfldr),
#                          '-plD:\\data\\{}\\2_Output\\%TaskName%\\log'.format(self._jobfldr), None]
#         else:
#             raise HpcError("not yet implemented!")
#             # TO DO: extend self._cmd.....
#             # exe = join(meas_dir, 'sil_lite.exe')
#             # self._cmd = [join(self._cmd, "sil_lite.exe"), None]
#
#         if not isfile(exe):
#             raise HpcError("%s not found in %s" % (basename(exe), dirname(exe)))
#
#         cfg = None
#         if self._app == "MTS":
#             self._cfg[ACTIVE_ALGOS] = []
#             self._cfg[INACTIVE_ALGOS] = []
#             self._cfg[EXPORTERS] = 0
#             self._cfg[URL_CNT] = 0
#             self._cfg[WILD_URL_CNT] = 0
#             self._cfg[CHANNEL_SRC] = []
#             self._cfg[CHANNEL_TYP] = []
#
#             try:
#                 cfg = self._check_mts_cfg(join(meas_dir, kwargs["cfg_dir"]), kwargs["cfg_name"])
#             except UnicodeEncodeError as ex:
#                 raise HpcError("config contains some illegal chars, please check it: {!s}".format(ex))
#
#         # we have a blacklist, so we need to parse our config file
#         if cfg_blacklist:
#             if cfg is None:
#                 cfg = ConfigParser(allow_no_value=True)
#                 cfg.optionxform = str
#                 try:
#                     cfg.read(cfg_path, encoding='utf-8-sig')
#                 except UnicodeEncodeError as ex:
#                     raise HpcError("config contains some illegal chars, please check it: {!s}".format(ex))
#
#             # but do we need to rewrite it, did we find blacklisted sections?
#             if set(cfg.sections()).intersection(set(cfg_blacklist)):
#                 with open(cfg_path, "w") as fp:
#                     cfg.write(fp)
#                 self._job.changes.append("adaptation: " + cfg_path)
#
#         if kwargs.get("fake_copy", False):
#             return
#
#         short_test = self._job.sched.template in ("Short_Test", "WSN_Test")
#         if not short_test and debug_lib_check(sys_dir):
#             raise HpcError("Debug dll's are only allowed in the 'Short_Test' template. Found debug dlls: %s"
#                            % sys_dir)
#
#         self._job.logger.info("starting to copy MTS package")
#         mts_filter = GDVPLUS
#         if not short_test:
#             mts_filter.append("*.pdb")
#         if kwargs.get('use_filter', True) is True:
#             mts_filter.extend(['doc*', 'lib', 'include', 'mi4_system_driver', 'MTSV2AppWizard', '*.bsig',
#                                'CrashRep*.*', 'errmon_*.*', 'errlog.*'])
#         mts_filter = ignore_patterns(*mts_filter)
#
#         replace = {}
#         if self._app == "MTS":
#             if not self._job.job_sim:
#                 replace['*.par'] = ((r'[GenericDrawActive].Value=1', r'[GenericDrawActive].Value=0'),)
#
#         robo = Robocopy(verbose=0, ignore=mts_filter, replace=replace, stat=False)
#         # copy mts_system and mts_measurement
#         robo.copy(sys_dir, join(self._job.sched.net_in_path, basename(sys_dir)))
#         robo.copy(meas_dir, join(self._job.sched.net_in_path, basename(meas_dir)))
#         self._bpldir = join(self._job.job_folder, "1_Input", "bpl")
#         if not exists(self._bpldir):
#             makedirs(self._bpldir)
#
#         self._job.changes.extend(robo.changes)
#         self._job.logger.info("MTS package copy finished")
#
#     def __add__(self, other):
#         """
#         add another part to command line and return them together, e.g. a recording
#
#         :param (``str`` | ``hpc.bpl.bpl_cls.BplListEntry``) other:
#         :return: command line
#         :rtype: str
#         """
#         self._rec = str(other)
#
#         if isinstance(other, BplListEntry) and other.has_sections:
#             mtch = r"rec(\d{5})\.bpl"
#             last = next(iter(sorted([i for i in listdir(self._bpldir) if match(mtch, i)])), "rec00000.bpl")
#             new_name = join(self._bpldir, "rec{:05d}.bpl".format(int(match(mtch, last).group(1)) + 1))
#             with Bpl(new_name, "w") as bpl:
#                 bpl.append(other)
#             self._cmd[-1] = r'-lbD:\data\{}\1_Input\bpl\{}'.format(self._jobfldr, basename(new_name))
#         else:
#             self._cmd[-1] = '-lr{}'.format(self._rec)
#
#         return self
#
#     @staticmethod
#     def copy(items=None, dst=None):
#         """do nothing method"""
#
#     def _check_mts_cfg(self, cfg_path, cfg_name, prev=None):  # pylint: disable=R1260,R0912
#         """check MTS config file"""
#         cfg = ConfigParser(allow_no_value=None)
#         cfg.optionxform = str
#         currcfg = merge_path(cfg_path, cfg_name)
#         cfg.read(currcfg, 'utf-8-sig')
#         rewrite = False
#
#         for section in cfg.sections():
#             if cfg.has_option(section, 'ChannelSources'):
#                 for k, v in (('ChannelSources', CHANNEL_SRC,), ('ChannelTypes', CHANNEL_TYP,)):
#                     ci = cfg.get(section, k, fallback="")
#                     self._cfg[v].extend(list([_f for _f in (x.strip(' \n\\,"\'') for x in ci.splitlines()) if _f]))
#
#             if 'Exporter' in section:
#                 self._cfg[URL_CNT] += int(cfg.get(section, 'Signal URL Count', fallback=0))
#                 self._cfg[WILD_URL_CNT] += int(cfg.get(section, 'Wildcard URL Count', fallback=0))
#                 self._cfg[EXPORTERS] += 1
#
#             elif 'SIM VFB' in section:
#                 if cfg.has_option(section, 'SWC Plugin Folder') and cfg.has_option(section, 'SWC Plugin'):
#                     self._check_mts_cfg(cfg_path,
#                                         join(cfg.get(section, 'SWC Plugin Folder').strip(' ".\\'),
#                                              cfg.get(section, 'SWC Plugin').strip(' "')).replace('\\\\', '\\'),
#                                         section)
#
#             elif section == "MTS Player V2":
#                 if cfg.has_option(section, BPLMODE):
#                     self._playsecs = bool(int(cfg.get(section, BPLMODE)))
#
#                 for k, v in XCHANGES:
#                     if not cfg.has_option(section, k) or cfg.get(section, k) != v:
#                         self._job.logger.warning("'%s' option not set to %s!" % (k, v))
#                         cfg.set(section, k, v)
#                         rewrite = True
#
#             elif prev is not None:
#                 if cfg.has_option(section, 'SimCfgFile'):
#                     if section not in self._cfg[ACTIVE_ALGOS] and cfg.get(section, 'SimCfgFile').find('_meas') >= 0:
#                         self._cfg[ACTIVE_ALGOS].append(section)
#                         self._check_mts_cfg(cfg_path, cfg.get(section, 'SimCfgFile').replace('$UserPathCfg$\\', ''),
#                                             section)
#                     elif section not in self._cfg[INACTIVE_ALGOS]:
#                         self._cfg[INACTIVE_ALGOS].append(section)
#
#                 elif cfg.has_option(section, 'PluginFile'):
#                     self._cfg[section + "_" + prev] = sorted([cfg.get(section, 'PluginFile').split('\\')[-1]])
#
#         if prev is None:
#             self._cfg[ACTIVE_ALGOS] = sorted(self._cfg[ACTIVE_ALGOS])
#             self._cfg[INACTIVE_ALGOS] = sorted(self._cfg[INACTIVE_ALGOS])
#             self._cfg[CHANNEL_SRC] = list(set(self._cfg[CHANNEL_SRC]))
#             self._cfg[CHANNEL_TYP] = list(set(self._cfg[CHANNEL_TYP]))
#
#         if rewrite:
#             chmod(currcfg, S_IWRITE)
#             with open(currcfg, "w") as cfp:
#                 cfg.write(cfp, False)
#             self._job.changes.append("manipulated: " + currcfg)
#
#         return cfg
