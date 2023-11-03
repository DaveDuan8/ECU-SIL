r"""
cdl_update.py
-------------

**prepare usage of ADTF files in simulation**

- get labels of CDL files in MKS project dir
    - labels with additional INT-x entries contain fixes and have higher preference
    - the biggest INT number is taken for the linked sw version
- get list of CDL files in target dir
- check out missing CDL file from MKS project to target dir with extended name, check out can be suppressed
    - existing copies of file revisions are kept untouched
- write config to CDL dispatcher mo configuration file cdl_files.ini in target dir
- create csv file with all revisions, labels and descriptions to find missing revs

**user api:**

    - `CdlUpdate.update`
    - cdl_update.py -c -p <mks_project> -t <target_dir> [-v <vers1> <vers2>...] [-l <path/filename of logfile>]
    - `CdlUpdate.checkout_cdl_files`(["sw_version1", "sw_version2" ...])

For the mks_project the sandbox directory or the mks url can be passed.

If no project is given CdlUpdate tries to read the mks url from an existing cdl_files.ini.

Be aware that the program needs to checkout different cdl file revisions,
therefore if you use an existing sandbox it can show a different revision of the cdl file after the update than before!

**example:**

.. python::

    > python cdl_update.py -p d:\my_sandbox\proj\...\out -t \\lifs010\prj\my_project\_cdl

inside python script:

.. python::

    from stk.mts.cdl_update import CdlUpdate

    CdlUpdate(mks_prj, trgt_dir, log_file).update()


based on RO 381253 in issue 361821

:org:           Continental AG
:author:        Joachim Hospes

:version:       $Revision: 1.14 $
:contact:       $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
:date:          $Date: 2017/09/29 16:31:45CEST $
"""

# - imports -----------------------------------------------------------------------------------------------------------
from sys import exit as sexit, path as spath
from os import path as opath
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from tempfile import mkdtemp
from shutil import rmtree, copyfile, move
from glob import glob
from re import compile as re_compile

# - import STK modules ------------------------------------------------------------------------------------------------
STK_FOLDER = opath.abspath(opath.join(opath.split(__file__)[0], r"..\.."))
if STK_FOLDER not in spath:
    spath.append(STK_FOLDER)

import stk.util.logger as log
from stk.error import StkError
import stk.mks.si as mks_si
import stk.util.dir as u_dir

# - defines -----------------------------------------------------------------------------------------------------------
TMP_DIR = r'd:\tmp\cdl_sandbox'
INI_FILE_NAME = 'cdl_files.ini'
INI_FILE_HEADER = """[VersionSignalURL]
Url   =  ARS4xx Device.SW_RccCycle.APL_VersionInfo.s_ApplVers.ApplDetail_t.u_ComponentID
Order = 1
[VersionSignalURL]
Url   =  ARS4xx Device.SW_RccCycle.APL_VersionInfo.s_ApplVers.ApplDetail_t.u_MajorVersion
Order = 2
[VersionSignalURL]
Url   =  ARS4xx Device.SW_RccCycle.APL_VersionInfo.s_ApplVers.ApplDetail_t.u_MinorVersion
Order = 3
[VersionSignalURL]
Url   =  ARS4xx Device.SW_RccCycle.APL_VersionInfo.s_ApplVers.ApplDetail_t.u_PatchLevel
Order = 4

"""
REF_LIST_FILE_NAME = 'cdl_rev_list.csv'


# - functions ---------------------------------------------------------------------------------------------------------
def main():
    """ parse arguments and update CDL target dir
    """
    opts = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    opts.add_argument("-p", "--mks_prj", type=str,
                      help="sandbox path or url of mks sub project with CDL files, "
                           "if not set it will be read from ini file in target dir")
    opts.add_argument("-t", "--trgt_dir", type=str, help="target dir to check out missing CDL files to / mandatory!")
    opts.add_argument("-v", "--versions", type=str, nargs="*",
                      help="versions to check out, separated by ' ', if not set all missing files will be checked out")
    opts.add_argument("-n", "--no_checkout", action="store_true",
                      help="do not checkout cdl files, just create ini and csv files")
    opts.add_argument("-l", dest="log_file", type=str, default=None, help="optional log file name")
    opts.add_argument("-c", "--checkout", action="store_true",
                      help="checkout cdl files only using existing ini file, no update of ini file")
    args = opts.parse_args()

    if not args.trgt_dir:
        opts.print_help()
        print('ERROR: no target directory given!')
        exit(1)

    if args.checkout:
        return CdlUpdate(args.mks_prj, args.trgt_dir, args.log_file).checkout_cdl_files(args.versions)
    else:
        return CdlUpdate(args.mks_prj, args.trgt_dir, args.log_file).update(args.no_checkout, args.versions)


# - class -------------------------------------------------------------------------------------------------------------
class CdlUpdate(object):
    """
    class to update CDL file in a target directory from a given MKS sub project

    usage: see module header
    """
    #
    # Regular expressions for parsing section headers and options.
    #
    SECTION = re_compile(
        r'\['  # [
        r'([^]]+)'  # very permissive!
        r'\]'  # ]
    )
    VALUEDEF = re_compile(
        r'([^:=\s][^:=]*)'  # very permissive!
        r'\s*[:=]\s*'  # separator (either : or =),
        r'(.*)$'  # everything up to eol
    )

    def __init__(self, mks_project, target_dir, log_file=None):
        r"""
        setting up the sandbox:

        pass either the sandbox directory or the mks url of it,
        init will check if it's an existing directory and create an own sandbox if not.

        Option mks_project can be set to '' if read from cdl_files.ini file later.

        :param mks_project: sandbox dir or url of mks subproject where to find the CLD files,
        :type  mks_project: str
        :param target_dir:  directory storing the CDL files, e.g. \\lifs010\prj\ARS4D0\cdl\
        :type  target_dir:  str
        :param log_file: opt. path/file name of log file, default: <target_dir>/cdl_files.log
        :type  log_file: str
        """
        self._target_dir = target_dir
        self._sandbox = None
        self._mks_project = mks_project if mks_project else None
        self._mks = None
        self._cdl_versions = {}
        self._cdl_filename = None

        if not log_file:
            log_file = opath.join(self._target_dir, 'cdt_update.log')
        self._logger = log.Logger('CDL_update', level=log.INFO, filename=log_file)
        self._logger.info('started CDL update for target {} and project {}'.format(target_dir, self._mks_project))

        if not self._mks_project:
            # get project from ini file if possible
            self.read_cfg()

    def _init_mks(self):
        """ internal setup mks connection to stored project

        either using existing sandbox if sandbox path is stored in _mks_project,
        or creating temporary sandbox if project name ("/nfs/projecte1/PROJECTS/.../project.pj") is stored

        :return:
        """
        if not self._mks_project:
            raise StkError('no mks project set to initiate mks!')

        self._logger.debug('setting up mks connection for {}'.format(self._mks_project))
        self._mks = mks_si.Si()

        if opath.exists(self._mks_project):
            self._sandbox = self._mks_project
            self._mks_project = None
        else:
            self._sandbox = mkdtemp()
            self._logger.debug('creating sandbox for {} in dir {}'.format(self._mks_project, self._sandbox))
            res = self._mks.createsandbox(self._mks_project, self._sandbox, skip_subpro=True)
            if res:
                self._logger.error("could not create sandbox for {}".format(self._mks_project))

        # current requirement: there's just one cdl file in the directory:
        cdl_files = glob(opath.join(self._sandbox, '*.cdl'))
        if not cdl_files:
            self._logger.exception('no *.cdl file found in mks sandbox %s' % self._sandbox)
            raise StkError('no *.cdl file found in mks sandbox %s' % self._sandbox)
        self._cdl_filename = cdl_files[0]

    def __del__(self):
        """delete temporary sandbox (if mks project url was initialised),
        otherwise leave passed sandbox as it is
        """
        if self._mks:
            self._logger.debug('dropping sandbox for %s' % self._mks_project)
            self._mks.dropsandbox(self._sandbox, delete='all')
            rmtree(self._sandbox, True)

    def update(self, no_checkout=False, versions=None):
        """
        update the missing files:

        - get list of CDL file labels,
        - create extended file names,
        - get list of existing files in target dir,
        - check out missing files, use list of versions if passed in call
        - write new cfg file (overwrite old one)

        needs parameters `_target_dir` and existing sandbox with cdl files in `_mks_sandbox`
        set in `__init__` method or during reading an existing cdl_files.ini

        :param no_checkout: flag to disable checkout of cdl files, default: False for backward compatibility
        :type  no_checkout: bool
        :param versions: list of sw versions to checkout cdl files for; version as declared in ini file
        :type  versions: list of str
        """
        self._init_mks()

        ini_file_name = opath.join(self._target_dir, INI_FILE_NAME)
        if opath.exists(ini_file_name):
            move(ini_file_name, ini_file_name + '.bak')

        # - get list of labels for that file
        lbl_dict = self._mks.get_file_labels(self._cdl_filename)

        # create extended list of all revisions
        ref_list_file_name = opath.join(self._target_dir, REF_LIST_FILE_NAME)
        dsc_dict = self._mks.get_revision_descriptions(self._cdl_filename)
        self._create_rev_list_file(lbl_dict, dsc_dict, ref_list_file_name)

        self._create_cdl_versions(lbl_dict)

        if not no_checkout:
            self._checkout_missing_files(versions)

        self.write_cfg(ini_file_name)

    def checkout_cdl_files(self, versions=None):
        """
        checkout files only without updating ini file

        :param versions: list of sw versions to checkout cdl files for
        :type  versions: list of str
        """
        self._init_mks()
        self._checkout_missing_files(version_list=versions)

    def _create_cdl_versions(self, lbl_dict):
        r"""
        create file names for all labels and store in internal _cdl_versions like

            {'4.3.8.1': {'Labels': ['SW_ARS4D0_04.03.08_INT-1'],
                         'Revision': '1.209.1.1.23',
                         'CDLFile': '\\lifs010\meta\ARS4D0\_CDL\ARS4D0_Appl_Release_1.209.1.1.23.cdl'}

        :param lbl_dict: dict of all checkpoints with csv of labels as returned by `stk.mks.si.Si.get_labels`
        :type  lbl_dict: dict
        :return:
        """
        # regular expressions for extracting sw version and int version from label
        # extract version and int no from "SW_ARS4D0_04.03.08_INT-1_RELEASE"
        lab_ver = re_compile(r'.*\D((\d\d)[\._](\d\d)[\._](\d\d\d?)).*')  # extract version 4.3.8 from label above
        lab_int = re_compile(r'.*\d\d[\._]\d\d[\._]\d\d(_INT-(\d+)?).*')  # extract int version '1' from label above
        self._cdl_versions = {}

        basename = opath.basename(self._cdl_filename)

        for cdl in lbl_dict:
            for label in [l.strip() for l in lbl_dict[cdl].split(',')]:
                # build version like 4.3.8.1 out of SW_ARS4D0_04.03.08_INT-1_RELEASE
                rel_match = lab_ver.match(label)
                if not rel_match:
                    self._logger.warning('can not parse version in label name {}, '
                                         'valid label format is "##.##.###_INT-#"'.format(label))
                    continue
                rel_vstr = rel_match.group(1)
                rel_version = '0.' + str(int(rel_match.group(2)))
                rel_version += '.' + str(int(rel_match.group(3)))
                rel_version += '.' + str(int(rel_match.group(4)))

                rel_match = lab_int.match(label)
                if rel_match:
                    rel_int = rel_match.group(2)
                else:
                    # !!! here we decide how to handle labels without INT-x:
                    # set to '0':
                    # if INT-x is found that one is newer than labels without any INT-x extension
                    #    (01.02.03_INT-4 is newer than 01.02.03_RELEASE)
                    # set to '999':
                    # all labels without INT-x are preferred before INT-x versions
                    #    (01.02.03_test_version is newer than 01.02.03_INT-3)
                    rel_int = '0'

                filename = opath.join(self._target_dir, opath.splitext(basename)[0] + '_' + cdl + '.cdl')

                if rel_version not in self._cdl_versions:
                    # new sw version: add to list
                    self._cdl_versions[rel_version] = {'Labels': [label],
                                                       'Revision': cdl,
                                                       'CDLFile': filename}
                elif self._cdl_versions[rel_version]['Revision'] == cdl:
                    # already found sw version: if same file revision just add the label
                    self._cdl_versions[rel_version]['Labels'].append(label)
                else:
                    # same sw version but different file revision:
                    # check INT value and use biggest for this sw version
                    for stored_label in self._cdl_versions[rel_version]['Labels']:
                        if lab_ver.match(stored_label) and lab_ver.match(stored_label).group(1) == rel_vstr:
                            if lab_int.match(stored_label) and int(lab_int.match(stored_label).group(2)) < int(rel_int):
                                # stored int version is smaller so this is the newer version, store this
                                self._logger.info(('replace version %s with new Revision %s, label %s, '
                                                   'first stored with revision %s, labels %s' %
                                                   (rel_version, cdl, label,
                                                    self._cdl_versions[rel_version]['Revision'],
                                                    self._cdl_versions[rel_version]['Labels'])))
                                self._cdl_versions[rel_version]['Revision'] = cdl
                                self._cdl_versions[rel_version]['CDLFile'] = filename
                                self._cdl_versions[rel_version]['Labels'].remove(stored_label)
                                self._cdl_versions[rel_version]['Labels'].append(label)
                                # found the regarding level, leave this loop
                                break
                            else:
                                self._logger.info(('version %s of label %s, Revision %s '
                                                   'already stored with newer revision %s, labels %s' %
                                                   (rel_version, label, cdl,
                                                    self._cdl_versions[rel_version]['Revision'],
                                                    self._cdl_versions[rel_version]['Labels'])))
        return

    def _checkout_missing_files(self, version_list=None):
        """
        checkout cdl files that are not stored in _target_dir

        :param version_list: sw versions to checkout cld files for,
                             versions as stored in cdl_files.ini with "Version ="
        :type  version_list: list of str
        """
        self._logger.info('update target directory with cdl file versions of %s' % self._cdl_filename)
        # get list of existing files in target dir
        prj_files = u_dir.list_file_names(self._target_dir, '*.cdl')
        if version_list is None:
            versions = self._cdl_versions
        else:
            key_list = set(self._cdl_versions.keys()) & set(version_list)
            versions = {key: self._cdl_versions[key] for key in key_list}

        for cdl in versions:
            trgtname = opath.basename(self._cdl_versions[cdl]['CDLFile'])
            if trgtname not in prj_files:
                # checkout missing file and copy to project dir:
                srcfile = opath.join(self._sandbox, self._cdl_filename)
                res = self._mks.co(srcfile, lock=False, revision=self._cdl_versions[cdl]['Revision'])
                self._logger.debug(res)

                copyfile(srcfile, opath.join(self._target_dir, trgtname))
                prj_files.append(trgtname)
                self._logger.info('added file %s' % trgtname)
        return

    def write_cfg(self, filename):
        """
        write config to a new file in win ini style

        :param filename: path and filename to write to
        """
        with open(filename, mode='w') as ini_file:
            ini_file.write(INI_FILE_HEADER)
            ini_file.write('[MksProject]\n')
            ini_file.write('ProjectName = ' + self._mks_project + '\n\n')
            for cdl in sorted(self._cdl_versions.keys()):
                ini_file.write('[VersionMapping]\n')
                ini_file.write('Version = ' + cdl + '\n')
                ini_file.write('Revision = ' + self._cdl_versions[cdl]['Revision'] + '\n')
                ini_file.write('Labels = ' + ', '.join(self._cdl_versions[cdl]['Labels']) + '\n')
                ini_file.write('CDLFile = ' + self._cdl_versions[cdl]['CDLFile'] + '\n')
                ini_file.write('\n')
        no_files = len(set([ver['Revision'] for ver in self._cdl_versions.values()]))
        self._logger.info("new ini file created: %d versions mapped to %d files: %s"
                          % (len(self._cdl_versions), no_files, filename))

    def read_cfg(self):
        """
        read ini file from target dir into internal cdl structure like::

            {'4.3.8.1': {'Labels': ['SW_ARS4D0_04.03.08_INT-1'],
                         'Revision': '1.209.1.1.23',
                         'CDLFile': 'ARS4D0_Appl_Release_1.209.1.1.23.cdl'}

        ini file structure has to follow strictly the written format::

            [VersionMapping]
            Version = 0.1.2.3
            ...

        with **Version as the first line in the section!!**

        also reads MksProject setting to store in internal path for check out::

            [MksProject]
            ProjectName = /nfs/projekte1/REPOSITORY/.../project.pj

        :return: cdl mapping
        :rtype:  dict
        """
        ini_file_name = opath.join(self._target_dir, INI_FILE_NAME)
        if not opath.exists(ini_file_name):
            # self._logger.info("Couldn't read ini file '%s', exception:\n%s" % (ini_file_name, err))
            return {}
        cdl_map = {}
        cdl_ver = ''
        mapping = False
        project = False

        with open(ini_file_name, "r") as inifile:
            for line in inifile:
                if line.strip() == '' or line[0] in '#;':
                    continue
                if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
                    # no leading whitespace
                    continue

                # skip to VersionMapping part:
                sect = self.SECTION.match(line)
                if sect and sect.group(1) == 'VersionMapping':
                    mapping = True
                    cdl_ver = ''
                    continue
                elif sect and sect.group(1) == 'MksProject':
                    project = True
                    mapping = False
                    continue

                if mapping or project:
                    setting = self.VALUEDEF.match(line)
                    opt = setting.group(1).strip()
                    val = setting.group(2).strip()
                    if opt == 'Version':
                        cdl_ver = val
                        cdl_map[cdl_ver] = {}
                    elif opt == 'ProjectName':
                        self._mks_project = setting.group(2).strip()
                        project = False
                    else:
                        if opt == 'Labels':
                            val = [v.strip() for v in val.split(',')]
                        cdl_map[cdl_ver][opt] = val
        self._cdl_versions = cdl_map
        return cdl_map

    @staticmethod
    def _create_rev_list_file(lbl_dict, dsc_dict, filename):
        """ create a file giving for all revisions the passed labels and descriptions

        :param lbl_dict: labels of revisions to save in file
        :type  lbl_dict: dict
        :param dsc_dict: descriptions of revisions (only first line expected, see code for details)
        :type  dsc_dict: dict
        :param filename: path and file name where to store
        :type  filename: str
        """
        # check that found line starts with a revision number
        # needed to keep only 1st line of multi line descriptions (assuming sw version is stored there)
        pattern = r"(^\d*\.\d*.*)$"

        # write in tab separated columns: rev, 'label eq descr', label, description (first line)
        with open(filename, 'w') as revfile:
            revfile.write('rev\teq str\tlabel\tdescription\n')
            # pass list of all revisions in descriptions and labels
            for rev in sorted(set(dsc_dict).union(lbl_dict)):
                if re_compile(pattern).search(rev):
                    revfile.write('{}\t{}\t{}\t{}\n'
                                  .format(rev, ('==' if lbl_dict.get(rev, '') == dsc_dict.get(rev, '') else ''),
                                          lbl_dict.get(rev, ''), dsc_dict.get(rev, '')))


if __name__ == "__main__":
    sexit(main())


"""
CHANGE LOG:
-----------
$Log: cdl_update.py  $
Revision 1.14 2017/09/29 16:31:45CEST Hospes, Gerd-Joachim (uidv8815) 
ignore ###.##.## versions, but allow ##.##.###
Revision 1.13 2016/11/29 12:00:10CET Hospes, Gerd-Joachim (uidv8815)
add --no_checkout, --checkout_cdl_files and --versions as options
Revision 1.12 2016/04/18 16:16:55CEST Hospes, Gerd-Joachim (uidv8815)
fix fixed path
Revision 1.11 2016/04/18 11:19:36CEST Hospes, Gerd-Joachim (uidv8815)
target path for ini file fixed
Revision 1.10 2016/04/15 17:37:42CEST Hospes, Gerd-Joachim (uidv8815)
pylint fixes
Revision 1.9 2016/04/15 15:55:28CEST Hospes, Gerd-Joachim (uidv8815)
add path to cdl file name in ini file,
add csv file with labels and descriptions for all revisions
Revision 1.8 2016/03/15 19:34:58CET Hospes, Gerd-Joachim (uidv8815)
use new option to skip subprojects, speedup!
Revision 1.7 2015/12/07 13:50:45CET Mertens, Sven (uidv7805)
removing pep8 errors
Revision 1.6 2015/12/03 17:46:49CET Hospes, Gerd-Joachim (uidv8815)
fix mks/ims keywords after update to ptc 10.6, pylint fixes
Revision 1.5 2015/11/16 15:21:48CET Hospes, Gerd-Joachim (uidv8815)
use orig version strings, compare INT versions and use biggest only,
use any 2digit triple diveded by '.' or '_' as sw version number
--- Added comments ---  uidv8815 [Nov 16, 2015 3:21:51 PM CET]
Change Package : 394803:1 http://mks-psad:7002/im/viewissue?selection=394803
Revision 1.4 2015/10/14 14:52:19CEST Hospes, Gerd-Joachim (uidv8815)
fix to not check out one file several times
--- Added comments ---  uidv8815 [Oct 14, 2015 2:52:20 PM CEST]
Change Package : 381253:1 http://mks-psad:7002/im/viewissue?selection=381253
Revision 1.3 2015/10/14 11:24:40CEST Hospes, Gerd-Joachim (uidv8815)
add more logging info, error if version is reuesed
--- Added comments ---  uidv8815 [Oct 14, 2015 11:24:41 AM CEST]
Change Package : 381253:1 http://mks-psad:7002/im/viewissue?selection=381253
Revision 1.2 2015/10/09 16:50:08CEST Hospes, Gerd-Joachim (uidv8815)
pep8 pylint fixes
--- Added comments ---  uidv8815 [Oct 9, 2015 4:50:09 PM CEST]
Change Package : 381253:1 http://mks-psad:7002/im/viewissue?selection=381253
Revision 1.1 2015/10/09 09:57:37CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
05_Software/04_Engineering/01_Source_Code/stk/mts/project.pj
"""
