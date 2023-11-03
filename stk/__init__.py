"""
STK (Scripting Tool Kit)
------------------------

Scripting Tool Kit Package for ADAS Algo Validation

This Toolkit is an collection of scripts, for further usage in other
scripts and programs. It supports the programmer with some basic libraries
which are needed more than once.

The main goal of this library is:

  - Easy programming interface (API) for the programmer.
  - Fast and Powerful execution with low overhead.

The Scripting Tool Kit provides tools for the Scripting Language Python

Package Organization
--------------------

The stk package contains the following subpackages and modules:

.. packagetree::
   :style: UML

"""
# pylint: disable=E0603
# - defines -----------------------------------------------------------------------------------------------------------
__all__ = ['cmd', 'db', 'dmt', 'util', 'io', 'img', 'mks', 'mts', 'rep', 'obj', 'valf', 'val']

# - log STK usage ------------------------------------------------------------------------------------------------
try:
    if __builtins__.get('stk_log', True):
        from stk import db_update

        # run DB update thread
        db_update()
except:
    pass

r"""
===============
VERSION HISTORY
===============

from release 02.01.01 on the change and failure requests contained in a release
are directly managed in IMS: http://ims-adas:7002/im;issues?query=stk%20Releases

The main CRs/FRs are also listed on Algo Valdation Wiki:
https://connext.conti.de/wikis/home?lang=de#!/wiki/ADAS Algo Validation

==============
older releases
==============
Release 2.00.08       AL_STK_V02.00.08_INT-3
--------------------------------------------

  **stk.valf**

- valf: purge flag neccessary for not cleaning sim output directory
- FR199155: AD_FR: STK: Extend Error Message when Observer method returns with error value
- fixes in util/find.py, valf/process_manager.py and valf/valf.py to provide errors during module load
- ew error class ValfError based on StkError in valf/error.py
- update in stk/error.py: new optional parameter dpth

  **stk.val**

- save event filters, improved filters
- added general switch to store testruns in DB or simply add them to the databus
- improved deprecated warnings

  **stk.hpc**

- fixed mts simulation utils supporting the new folder structure

Release 2.00.08       AL_STK_V02.00.08_INT-2
========================================================

Redo Checkpoint because of Error Message during Checkpointing


Release 2.00.08       AL_STK_V02.00.08_INT-1
========================================================

  **stk.hpc**

- Reogrganisation of internal sturkture.
- Added section handling to TaskFactoryMTS and SubTaskFaktoryMTS

  **stk.mts**

- FR195174: AD_FR: bpl_xml.py returns empty list when no "Section" Tag is inside.

  **stk.valf**
- signal_extractor.py:
  - new feature HIL timestamp conversion, documented in valf training slides
  - new test_signal_extractor with basic HIL tests

- bpl_reader.py:
  - BugFixes for errors found during implementation of test_bpl_reader


Release 2.00.07       AL_STK_V02.00.07_INT-2
--------------------------------------------

  **stk.val.base_events**

- extended asmt.ValAssessment with GetAssesmentState Method
- base_events.ValEventDatabaseInterface:
    - Added Initialisation of RecCatalogDB
    - Added Initialisation of BaseObjDataDB
    - Added Initialisation fo GenLabelDB

  **stk**

- changed pylint settings regarding our new guidelines:
  - Corrected regular expression for Method Names
  - Corrected regular expression for Function Names.

- marked following classes and functions as deprecated (will be removed until Release 2.0.9)

  - stk.rep.report_base
    class onFirstPage()
    class onLaterPage()
    class ValidationReportBase()
    class NumberedCanvas()
    class OverallSummary()
    class SummaryTestcases()
    class ValTableOfContent()
    class ValDocTemplate()

  - stk.val.base_events
    class ValEventNotImplemented()
    class ValEventLoader()
    class ValEventUpdater()
    class SaveEventDB()
    class LoadEventAttributesDB()
    class SetAssessmentID()
    class SetAssessment()
    class GetAssesmentComment()
    class ValStatObstEvent()
    class ValGenericStateEvent()

  -stk.mks.si
    class MksSI()
    class MksSIMember()
    class MksSIProject()
    class MksSISandbox()


Release 2.00.07       AL_STK_V02.00.07-INT-1
--------------------------------------------

**stk/hpc**

- Added extension for using the _HPC Folder Name.
- New HPCFolder Name is build on _HPC + Numbers from the Server.
    e.g. _HPC Folder of LIFS006 = _HPC006
         _HPC Folder of LIFS066 = _HPC066
- removed journal-feature in db-ifc of HPC to improve performance.
- added SubTask Feature to HPC.

**stk/valf**

- valf: add new module/class valf to start validation scripts with .py instead of .bat/.cmd files
- process_manager: move instantiation of data_manager from load_configfile into __init__
- add new start scripts to valf_demo.cat_demo
- add new test_valf with basic tests

**stk/val**

- Add Testcase to ValTestrun
- Add Support of Testcase Events
- new module events.py supporting eventlists
- add Events to testcase / save and load the events
- extended Signal and Binary signal class
-  Signal Plot and PlotXy
-  new math functions
- marked several classes and functions a deprecated (will be removed until Release 2.0.9)
- Add new column RDID into VAL_EVENTS table
  (Oracle DB update required, please contact guenther.raedler@continental.corporation.com)


Release 2.00.06       AL_STK_V02.00.06
--------------------------------------

**stk/valf**

- add feature "SimSelection" to enter list of indices for particular bpl/cat list selection
- add option 'assign-port' to set any port value using -a <PortName> <PortValue>
- move vpc.data-extractor to stk.valf.signal_extractor with addons for MFC SOD
- also move signal_defs to stk/valf as it is used by signal_extractor

**stk**

- AD_FR: 183382 Gauss Ploting error and wrong pylint warning corrections
- AD_FR: 183260 "ShiftTimelineOfPointPairList" Function

- Python SQLAlchemy (0.8.1) is needed now to use the stk.
  Please use package from \\cw01.contiwan.com\lndp\didk7746\_public\Tools\python\SQLAlchemy-0.8.1
    1. Copy package to local disk.
    2. open cmdprompt in directory.
    3. type "setup.py install"

**stk/hpc**

- Added SubTask Support for hpc.
- Increased Max possible CMDLine Length for Tasks in HPC. (no Limitation)
- Added DB Support for HPC Job/Task/SubTask Handling.
- Added HPCSim() Class to simulate submit process localy.
  Also a test.bat File will be created to start the 1. Task localy.
- Added new Utils used for ARS4xx Simulation runs

**stk/val**

- stk.val.testrun.py
- Added changes into TestRunManager Class for managing hirarchichal testrun data with repace functinality
- Fixed bugs in TestRun class for Reload and replace operation of testrun

- fix error in io/dlm.py: empty local signal dict in case of errors instead returning None
- Added a new file obj/ego.py. Contains a class for
  the ego motion
- Added a new package obj/clothoid. Contains functions
  to handle clothoid objects (Estimation error, event generation).
- Added a new file db/lbl/genlabel_defs.py. Contains classes
  with definitions for specific labels. Currently only road type label
  definitions are included.
- Modified db/dbenhquery.py. Road type label reading function now
  uses the label definitions mentionned in genlabel_defs.py.
- Removed functions from util/helper.py that are now in the clothoid package.

- Added classes to send emails with Smtp and lotus Notes:
  stk.util.email.smtp
  stk.util.email.NotesMail

- Added Method: UseGlobalDataFolder() in TaskFactory of Hpc.


Release 2.00.05       AL_STK_V02.00.05
--------------------------------------

- No changes, only problems during checkpointing solved.

Release 2.00.04       AL_STK_V02.00.04
--------------------------------------

**stk**

 - MKS Source Integrity
    - Added new class stk.mks.si.Si()
     - Added Unittest stk/mks/test_si.py
 - added cat_demo to 05_Testing/05_Test_Environment/valf_demo
     example of easy cat reader observer using stk.valf.main.py
 - updated stk/valf/base_component_wizard.py to create stk 2.0 code
 - added stk.valf.main.py
    - replacement of vpc.validationmain.py
    - supports valf run without DB connnection
 - fixed sqlite error in stk.valf.db_connector.py
    - new default value
 - added new Result API
    - stk.val.asmt.py
        - added ValAssessment class
        - added ValAssessmentStates class
        - added ValAssessmentWorkFlows
    - stk.val.result.py
        - added ValResult class
        - added ValSaveLoadLevel class
        - added ValTestcase class
    - stk.val.testrun.py
        - added TestRun class
        - improved input port parser for testrun configurations
 - stk.db.gbl.gbl.py
    - extended interface of GetUser() method
 - stk.db.val.val.py
    - added new method GetResultDescriptorInfoForTestrun()
    - added classname column into result type table
        --> update in Databases required
 - stk.db.sqlite_db
    - added classname column into result type table

Release 2.00.03       AL_STK_V02.00.03
--------------------------------------

**stk**

- Removed pylint Errors
- Fixed Pep8 Messages.
- ......


Release 2.00.02       AL_STK_V02.00.02
--------------------------------------

**stk**

- Updates in hpc (Error handling for copy results)
- Updates in db (changed some interfaces)
- ......


Release 2.00.01       AL_STK_V02.00.01
--------------------------------------

**stk**

- Added a bunch of modules into stk, to
  support the different validations from the
  single Teams.


Release 2.00.00       AL_STK_V02.00.00_20130125
-----------------------------------------------

**stk**

- First official Release for stk 2.0
- Changed stk to package structure.


Release 1.19.01       AL_STK_V01.19.00_20121026
-----------------------------------------------

**stk.hpc**

- Prevent AppStarter from Chrash when using no Static cfg File.
- Corrected CommandLine Usage of App Starter (Removed -c without arg)


Release 1.19.00       AL_STK_V01.19.00_20121004
-----------------------------------------------

**stk.hpc**

- Added separate Exit Code for CPU IDLE and I/O Idle.
- Changed rule when Application will be killed.
  CPU Idle is depending from I/O idle.
- BugFix for Atomatic replacemanet -> Added import


Release 1.18.07       AL_STK_V01.18.07_20120919
-----------------------------------------------

**stk.hpc**

- Automatic replacement (lifs010 -> lifs010s) for fast server connection added.
- App_Watcher: Extended Appwatcher to watch on the started Application
               and all the started subprocesses.


Release 1.18.06       AL_STK_V01.18.06_20120907
-----------------------------------------------

**stk.hpc**

- MTS_Final_Check: BugFix solves chrash in Database Query.
- AppStarter: Added I/O watching to app watcher.
- Improved dynamic parameter handling. No problems with spaces anymore.
- AppStarter: Introduced possibility to define a pre task which will run
  before the actual application.
- AppStarter: Fix for small issues in app watcher.
- AppStarter: Moved app watching in seperate process.
- AppStarter: Introduced new error code for script malfunction.
- AppStarter BugFix: Copying of StdOut and StdErr Files works again.
- BugFix for re-set Current Working Dir in app_starter.py


Release 1.18.05       AL_STK_V01.18.05_20120303
-----------------------------------------------

**stk.hpc**

- Added Current Working Directory Feature
- Limited JobName to 32 Character
- Inserted Check for max CMDLine for Task for 480 Characters.
- Added Relative call to App Starter
- Added Rel parameter app.cfg

Release 1.18.04       AL_STK_V01.18.04_20120803
-----------------------------------------------

**stk.hpc**

- BugFix in App_Starter. MultiThreading caused RaceCondition to Copy
  results twice or not.


Release 1.18.03       AL_STK_V01.18.03_20120803
-----------------------------------------------

**stk.hpc**

- Added Application Watcher to AppStarter.
- When CPULoad of Application is longer than ~7 min under 2%,
  Application will be Killed.


Release 1.18.02       AL_STK_V01.18.03_20120802
-----------------------------------------------

**stk.hpc**

- Check After Application call after Chrashdump. If Chrash detected,
  Error Code will be -101.


Release 1.18.01       AL_STK_V01.18.01_20120801
-----------------------------------------------

**stk.hpc**

- Added correct Exit Code at Cancel Task in app_starter.py
- Removed unused mts_starter in hpc/util/__init__.py
- Added the possibility to limit the max used number of cores or
  nodes for a job.
- BugFix: Replaced self.__JobName with self.JobName in stk_hpc.py


Release 1.4.2       AL_STK_V01.04.02_20101011
---------------------------------------------

**stk_ini**

- Extended class with new functionality: DeleteKey,GetSectionKeys,GetSections

**stk_word**

- Bug-fix for remove_table function, error handling in save_as function,
  and table_id_to_index() function.


Release 1.4.1       AL_STK_V01.04.01_20100903
---------------------------------------------

**GENERAL**

- **stk_log** bug-fix
- **stk_report_generator** extended pdf report with confidential information
- **stk_base** get_class_list added, gives list of class names in a module
- **stk_mts** cleaned up, main removed

Release 1.4.0       AL_STK_V01.04.00_20100719
---------------------------------------------

**GENERAL**

- **stk_project** added - access for MS project files
- **stk_plot** added - will replace stk_plot_generator in next release
- **stk_report** dropped - content was merged to **stk_report_generator**
- stk_excel new interfaces added

**stk_dlm_read**

- some logging mechanisms removed

**stk_excel**

- generic read get_data added
- set_data and set_format functions added for robust and comfortable
  writing and formatting
- get_work_sheet_names added
- get_last_cell added
- documentation updated regarding guideline
- set_format: optional worksheet name, default current
- set_data: optional worksheet name, default current, when given write
  into existing or create new sheet

**stk_mks**

- add new class stkMKSIntegrity


Release 1.3.1       AL_STK_V01.03.01_20100429
---------------------------------------------

**GENERAL**

- unit test for stk_db_access added (only sqlite)
- unit test bugfix for stk_excel test cases
- unit test report added to 05_Testing\02_Reports\stk_unit_test_results.txt

**stk_word**

- Added auto resize for tables when the size of the data is greater than
  the size of the table.
- Bugfix for set_row_style.

**stk_bsig**

- Convert the result to python list
- Improve the speed for the binary data parser

**stk_db_access**

- SQLite interface added


Release 1.3.0       AL_STK_V01.03.00_20100409
---------------------------------------------

**GENERAL**

- unit test for stk_word added
- CMD_Tools integrated into ETK : /nfs/projekte1/REPOSITORY/Base_Development/
  05_Algorithm/ETK_EngineeringToolKit/04_Engineering/CMD_Tools
- **stk_mts_extract_scenarios.py** moved to ETK_EngineeringToolKit
- **stk_mts_distribute_batch.py** moved to ETK_EngineeringToolKit
- **stk_algo_if_wrapper** moved to ETK_EngineeringToolKit
- graphviz now shared from STP
- **stk_bsig.m** added - Matlab binary format reader
- **stk_bsig.m** example script added
- db_access demo script dropped. Will be replaced by unit test in future
- doxygen dropped
- epydoc installation package added
- STK help file added to 03_Supporting_Documents (auto docu by epydoc)


**stk_mts_bpl**

- stkBplReader removed/renamed to **mts_bpl_reader**
- add mts_bpl_writer class (write, append, merge bpls, NO SECTIONS so far)
- unit test for mts_bpl_writer added
- mts_bpl_reader bug fix : encoding for rec-file pathes: iso-8859-1 --> utf-8
- mts_bpl_reader bug fix : check if file exists

**stk_excel**

- Fix for inconsitent data : SetRangeValues fills empty cells instead of
  doing nothing
- header and footer update

**stk_ini**

- Encoding bug fix for rec-file pathes

**stk_logger**

- docu update, fix example

**stk_report_generator**

- Bug fix due to merging stk_report and stk_report_generator

**stk_word**

- Changed the name of the functions to be according to coding guidelines.


Release 1.2.0       AL_STK_V01.02.00_20100319
---------------------------------------------

- **stk_sql.py** added
- **stk_mks.py** added
- **stk_logger.py** added to replace **stk_log**
- **stk_log** dropped

- code customisation and reworks for **stk_db_access** and **stk_labelread**


**stk_base**

- delim_strip_left added

**stk_bsig**

- Bug fix for signals with Double type

Release 1.1.0       AL_STK_V01.01.00_20100219
---------------------------------------------
- **stk_mts_extract_scenarios.py** added
- **stk_mts_distribute_batch.py** added
- **stk_word.py** added
- dropped: **stk_dbg.py**
- dropped: **stk_file.py**  line_replace function added to **stk_base**
- several header and footer updates

**stk_bsig**

- support for binary signal files of version 2.0.0 added (used in ACC VALF)


Release 1.0.0       AL_STK_V01.00.00_20091208
---------------------------------------------

**stk_base** fully reworked

- unit tests added
- functions REMOVED and documentation added:
    - **create_dir(..)**  use : **os.makedirs(..)**
    - **StripPath()**     use : **os.path.split(..)**
    - **StripPathOld()**  use : **os.path.split(..)**
    - **BuildPath()**     use : **os.path.abspath(..)**
    - **CopyFile()**      use : **shutil.copyfile(src, dest)**
    - **CopyTree()**      use : **shutil.copytree(src, dest)**
- functions RENAMED :
    - AppendFile --> append_file
    - ShellExecute --> sys_cmd_sub_process
    - ListFileNames  --> list_file_names
    - ListDirNames  --> list_dir_names
- documentation reworks (reST)

**stk_dlm_reader**

- robustness of dirty input pathes (strip used)
- examples added to documentation
- documentation reworks (reST)
- type handling extended

**stk_mts_bpl**

- "get_section_list" and "get_file_section_list" added
  (returning simple data lists)
- bugfis: support "UTF-8" for bpls and return strings as 'latin-1'
  ('iso-8859-1')
- Documentation extended
- Class stkBplReader renamed to mts_bpl_reader  (stkBplReader still working)
- Interface classes removed for easier handling
- unit test added
- merge_bpl_files

**stk_md5**

- renamed function : MD5FromFile --> md5_from_file

**stk_algo_if_wrapper** added (wrap object list architecture from xls to
  xml (ARS))

- DROPPED: see also stk_module_change_list.xls
- dropped: **stk_mts_pl.py**  function added temp. to **stk_mts_bpl**
- dropped: **stk_mts_bat.py** condor will be used in future
- dropped: **stk_mts_cfg.py** in general : manipulation of this config
  is risky strategy
- dropped: **stk_mts_ini.py** functionality added to stk_mts_bpl.py

**stk_log**

- stk_err dependency removed

**stk_csv**

- stk_err dependency removed
- indentation fixes

Release 0.9.5       AL_STK_V00.09.05_20091118
---------------------------------------------

- dropped: **stk_merge_bplfiles.py** function added temp. to stk_mts_bpl
- bugfix: **stk_labelread**
- bugfix **stk_bsig**
- comment reworks

Release 0.9.4       AL_STK_V00.09.04_20091112
---------------------------------------------

- DROPPED: see also stk_module_change_list.xls
- dropped: **stk_bpl2ini.py** (use: stk_mts_bpl)
- dropped: **stk_err.py** (use python error handling instead)
- dropped: **stk_glob_class.py**
  (will be just documented as example singleton class)
- dropped: **stk_merge_bpl_files.py** (use: stk_mts_bpl)
- dropped: **stk_pc_lint.bat** (now implemented as tool SWBT_PCLint)
- dropped: **stk_pc_lint.py** (now implemented as tool SWBT_PCLint)
- dropped: **stk_timer.py** (use: stk_time)
- dropped: **stk_tsim_storage.py** (will be part of condor tooling itself)

Release 0.9.1
-------------
- Initial Release
  This Version is integrated into initial version of VALF Validation Framework

.. stk_module_change_list: http://liss014.auto.contiwan.com:6001/si/
   viewrevision?projectName=/nfs/projekte1/REPOSITORY/Base_Development/
   05_Algorithm/STK_ScriptingToolKit/04_Engineering/03_Supporting_Documents/
   project.pj&selection=stk_module_change_list.xls
"""

"""
CHANGE LOG:
-----------
$Log: __init__.py  $
Revision 1.4 2016/08/19 20:59:05CEST Hospes, Gerd-Joachim (uidv8815) 
try saving stk version
Revision 1.3 2016/04/04 13:31:22CEST Mertens, Sven (uidv7805)
pylint -1
Revision 1.2 2015/10/26 16:39:39CET Hospes, Gerd-Joachim (uidv8815)
update mks server to ims-adas
--- Added comments ---  uidv8815 [Oct 26, 2015 4:39:39 PM CET]
Change Package : 384737:1 http://mks-psad:7002/im/viewissue?selection=384737
Revision 1.1 2015/04/28 17:34:21CEST Hospes, Gerd-Joachim (uidv8815)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Tools/Validation_Tools/Lib_Libraries/STK_ScriptingToolKit/
    05_Software/04_Engineering/01_Source_Code/stk/project.pj
Revision 1.25 2015/03/05 11:32:29CET Mertens, Sven (uidv7805)
please, no stk log when using e.g. VAT
--- Added comments ---  uidv7805 [Mar 5, 2015 11:32:30 AM CET]
Change Package : 312733:1 http://ims-adas:7002/im/viewissue?selection=312733
Revision 1.24 2015/02/16 17:27:31CET Hospes, Gerd-Joachim (uidv8815)
remove hpc from __all__
--- Added comments ---  uidv8815 [Feb 16, 2015 5:27:32 PM CET]
Change Package : 307161:1 http://ims-adas:7002/im/viewissue?selection=307161
Revision 1.23 2015/01/30 10:43:36CET Mertens, Sven (uidv7805)
removing jenkins build problem of relative import
--- Added comments ---  uidv7805 [Jan 30, 2015 10:43:37 AM CET]
Change Package : 288765:1 http://ims-adas:7002/im/viewissue?selection=288765
Revision 1.22 2015/01/29 11:05:07CET Mertens, Sven (uidv7805)
removing some pylint errors on top
--- Added comments ---  uidv7805 [Jan 29, 2015 11:05:08 AM CET]
Change Package : 299025:1 http://ims-adas:7002/im/viewissue?selection=299025
Revision 1.21 2015/01/19 13:18:54CET Mertens, Sven (uidv7805)
???
--- Added comments ---  uidv7805 [Jan 19, 2015 1:18:55 PM CET]
Change Package : 296850:1 http://ims-adas:7002/im/viewissue?selection=296850
Revision 1.20 2015/01/19 13:17:55CET Mertens, Sven (uidv7805)
update4thread
--- Added comments ---  uidv7805 [Jan 19, 2015 1:17:55 PM CET]
Change Package : 296850:1 http://ims-adas:7002/im/viewissue?selection=296850
Revision 1.19 2014/12/08 11:46:39CET Mertens, Sven (uidv7805)
update according CR
--- Added comments ---  uidv7805 [Dec 8, 2014 11:46:40 AM CET]
Change Package : 288772:1 http://ims-adas:7002/im/viewissue?selection=288772
Revision 1.18 2014/07/17 11:00:02CEST Hospes, Gerd-Joachim (uidv8815)
add new dmt package
--- Added comments ---  uidv8815 [Jul 17, 2014 11:00:03 AM CEST]
Change Package : 245477:1 http://ims-adas:7002/im/viewissue?selection=245477
Revision 1.17 2014/05/22 11:14:08CEST Mertens, Sven (uidv7805)
moving pylint disable to remove pep8 error
--- Added comments ---  uidv7805 [May 22, 2014 11:14:09 AM CEST]
Change Package : 238250:1 http://ims-adas:7002/im/viewissue?selection=238250
Revision 1.16 2014/05/22 08:12:50CEST Mertens, Sven (uidv7805)
include cmd folder to get epydoc running
--- Added comments ---  uidv7805 [May 22, 2014 8:12:51 AM CEST]
Change Package : 238250:1 http://ims-adas:7002/im/viewissue?selection=238250
Revision 1.15 2013/10/16 13:33:03CEST Hecker, Robert (heckerr)
Replaced dedicated imports with __all__ variable.
--- Added comments ---  heckerr [Oct 16, 2013 1:33:03 PM CEST]
Change Package : 106870:1 http://ims-adas:7002/im/viewissue?selection=106870
Revision 1.14 2013/10/07 07:59:18CEST Raedler, Guenther (uidt9430)
- prepare new checkpoint, updated release info
--- Added comments ---  uidt9430 [Oct 7, 2013 7:59:18 AM CEST]
Change Package : 199465:1 http://ims-adas:7002/im/viewissue?selection=199465
Revision 1.13 2013/09/26 19:30:26CEST Hecker, Robert (heckerr)
Corrected Imports, removed pep8 Issues.
--- Added comments ---  heckerr [Sep 26, 2013 7:30:26 PM CEST]
Change Package : 197303:1 http://ims-adas:7002/im/viewissue?selection=197303
Revision 1.12 2013/08/01 15:55:00CEST Hecker, Robert (heckerr)
Removed unecessary imports.
--- Added comments ---  heckerr [Aug 1, 2013 3:55:00 PM CEST]
Change Package : 192377:1 http://ims-adas:7002/im/viewissue?selection=192377
Revision 1.11 2013/07/18 11:17:15CEST Hecker, Robert (heckerr)
Revision 1.11 2013/07/18 11:17:15CEST Hecker, Robert (heckerr)
Added History Information.
--- Added comments ---  heckerr [Jul 18, 2013 11:17:15 AM CEST]
Change Package : 106870:1 http://ims-adas:7002/im/viewissue?selection=106870
Revision 1.10 2013/07/16 15:53:21CEST Hecker, Robert (heckerr)
Added History to file.
--- Added comments ---  heckerr [Jul 16, 2013 3:53:22 PM CEST]
Change Package : 106870:1 http://ims-adas:7002/im/viewissue?selection=106870
Revision 1.9 2013/04/16 20:29:06CEST Hecker, Robert (heckerr)
Added docu for upcoming Release.
--- Added comments ---  heckerr [Apr 16, 2013 8:29:07 PM CEST]
Change Package : 106870:1 http://ims-adas:7002/im/viewissue?selection=106870
Revision 1.8 2013/03/15 14:51:15CET Hecker, Robert (heckerr)
Removed pylint Warning with relative imports.
--- Added comments ---  heckerr [Mar 15, 2013 2:51:15 PM CET]
Change Package : 106870:1 http://ims-adas:7002/im/viewissue?selection=106870
Revision 1.7 2013/03/05 15:23:19CET Hecker, Robert (heckerr)
Added Checkpoint Description.
--- Added comments ---  heckerr [Mar 5, 2013 3:23:20 PM CET]
Change Package : 106870:1 http://ims-adas:7002/im/viewissue?selection=106870
Revision 1.6 2013/02/26 16:36:59CET Raedler, Guenther (uidt9430)
- import val packages to support base events
--- Added comments ---  uidt9430 [Feb 26, 2013 4:37:00 PM CET]
Change Package : 174385:1 http://ims-adas:7002/im/viewissue?selection=174385
Revision 1.5 2013/02/11 11:09:22CET Raedler, Guenther (uidt9430)
- added new packages and changed order of import
--- Added comments ---  uidt9430 [Feb 11, 2013 11:09:22 AM CET]
Change Package : 174385:1 http://ims-adas:7002/im/viewissue?selection=174385
Revision 1.4 2013/01/23 10:19:06CET Hecker, Robert (heckerr)
Improved MainPage of stk docu with Input from MFC-ATM.
--- Added comments ---  heckerr [Jan 23, 2013 10:19:06 AM CET]
Change Package : 168499:1 http://ims-adas:7002/im/viewissue?selection=168499
Revision 1.3 2013/01/23 07:56:33CET Hecker, Robert (heckerr)
Updated epydoc docu.
--- Added comments ---  heckerr [Jan 23, 2013 7:56:33 AM CET]
Change Package : 168499:1 http://ims-adas:7002/im/viewissue?selection=168499
Revision 1.2 2012/12/05 13:49:52CET Hecker, Robert (heckerr)
Updated code to pep8 guidelines.
--- Added comments ---  heckerr [Dec 5, 2012 1:49:52 PM CET]
Change Package : 168499:1 http://ims-adas:7002/im/viewissue?selection=168499
Revision 1.1 2012/12/04 17:36:47CET Hecker, Robert (heckerr)
Initial revision
Member added to project /nfs/projekte1/REPOSITORY/Base_Development/
05_Algorithm/STK_ScriptingToolKit/04_Engineering/stk/project.pj
"""
