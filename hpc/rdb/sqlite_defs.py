"""
sqlite_defs.py
--------------

sqlite DB definitions
"""
# - Python imports -----------------------------------------------------------------------------------------------------
from os import unlink
from os.path import exists

# - import HPC things --------------------------------------------------------------------------------------------------
from hpc.rdb.base import BaseDB

# - defines ------------------------------------------------------------------------------------------------------------
# CREATE TRIGGER [DMT_FILES_SUBPATH] AFTER INSERT ON [DMT_FILES] FOR EACH ROW BEGIN UPDATE [DMT_FILES]
# SET [SUBPATH] = subpath(NEW.FILEPATH), [RECFILEID] = basename(NEW.FILEPATH); END
SQLITE_DEF = """
CREATE TABLE [DMT_FILES] ([MEASID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [FILEPATH] NVARCHAR2(300) NOT NULL, [RECFILEID] NVARCHAR2(255), [FILESIZE] INTEGER, [BEGINABSTS] INTEGER, [ENDABSTS] INTEGER, [PROJECT] NVARCHAR2(100), [STATUS] NVARCHAR2(11) NOT NULL DEFAULT 'transmitted', [BASEPATH] NVARCHAR2(250), [SERVERSHARE] NVARCHAR2(64), [CRC_NAME] INTEGER, [PARENT] INTEGER)
CREATE UNIQUE INDEX [UQ_DMT_FILES_PATH] ON [DMT_FILES] ([FILEPATH])
CREATE TABLE [HPC_ERRTYPE] ([TYPEID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [TYPENAME] NVARCHAR2(128) NOT NULL)
CREATE UNIQUE INDEX [UQ_APPERR_TYPE_TYPENAME] ON [HPC_ERRTYPE] ([TYPENAME])
CREATE TABLE [HPC_EXITCODES] ([EXITCODE] INTEGER NOT NULL PRIMARY KEY, [DESCR] VARCHAR2(128) NOT NULL, [PRIO] INTEGER NOT NULL)
CREATE UNIQUE INDEX [HPC_EXITCODES_PRIO_UK] ON [HPC_EXITCODES] ([PRIO])
CREATE TABLE [HPC_NODE] ([NODEID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [NODENAME] NVARCHAR2(32) NOT NULL, [CONFIG] BLOB, [LOCATION] NVARCHAR2(20) NOT NULL DEFAULT 'LND')
CREATE UNIQUE INDEX [NODENAME_IDX] ON [HPC_NODE] ([NODENAME])
CREATE TABLE [HPC_SLAVE] ([SLAVEID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [NODEID] INTEGER NOT NULL CONSTRAINT [HPC_SLAVE_NODE_FK] REFERENCES [HPC_NODE]([NODEID]) ON DELETE CASCADE, [NAME] NVARCHAR2(32) NOT NULL, [DTOTAL] INTEGER NOT NULL DEFAULT 0, [RAMTOTAL] INTEGER NOT NULL DEFAULT 0, [CONFIG] BLOB, [PING] TIMESTAMP, [SOCKETS] INTEGER NOT NULL DEFAULT 1, [CORES] INTEGER NOT NULL DEFAULT 1)
CREATE UNIQUE INDEX [HPC_SLAVE_NAME_UK] ON [HPC_SLAVE] ([NAME])
CREATE TABLE [HPC_LOGITEM] ([IID] INTEGER NOT NULL PRIMARY KEY, [SLAVEID] INTEGER DEFAULT NULL CONSTRAINT [HPC_LOGITEM_NODE_FK] REFERENCES [HPC_SLAVE]([SLAVEID]) ON DELETE SET NULL, [NAME] NVARCHAR2(128) NOT NULL, [DESCR] NVARCHAR2(128), [CNT] INTEGER NOT NULL DEFAULT 0)
CREATE UNIQUE INDEX [HPC_LOGITEM_NAME_UK] ON [HPC_LOGITEM] ([NAME], [DESCR])
CREATE TABLE [HPC_NETLOG] ([SLAVEID] INTEGER NOT NULL CONSTRAINT [HPC_NETLOG_SLAVE_FK] REFERENCES [HPC_SLAVE]([SLAVEID]) ON DELETE CASCADE, [LOGTIME] TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, [SEGRECV] INTEGER NOT NULL, [SEGSENT] INTEGER NOT NULL, [SEGRETR] INTEGER NOT NULL)
CREATE TABLE [HPC_PRJTMPL] ([PTID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [NAME] VARCHAR(32) UNIQUE)
CREATE TABLE [HPC_FUNCLASS] ([FCID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [FCNAME] VARCHAR(4) UNIQUE)
CREATE TABLE [HPC_STATE] ([STATEID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [NAME] VARCHAR(11) UNIQUE)
CREATE TABLE [HPC_VER] ([VERID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [VERSTR] VARCHAR(96) UNIQUE)
CREATE TABLE [HPC_PYVER] ([PYVERID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [VERSTR] VARCHAR(12) UNIQUE)
CREATE TABLE [HPC_JOB] ([JOBID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [HPCJOBID] INTEGER NOT NULL, [NODEID] INTEGER NOT NULL CONSTRAINT [HPC_JOB_FK] REFERENCES [HPC_NODE]([NODEID]) ON DELETE CASCADE, [IID] INTEGER DEFAULT NULL CONSTRAINT [HPC_JOB_USER_FK] REFERENCES [HPC_LOGITEM]([IID]) ON DELETE CASCADE, [SID] INTEGER DEFAULT 0 CONSTRAINT [HPC_JOB_SOURCE_PC_FK] REFERENCES [HPC_LOGITEM]([IID]) ON DELETE CASCADE, [SUBMITSTART] TIMESTAMP, [SUBMITSTOP] TIMESTAMP, [RECSIZE] INTEGER, [RECDURATION] FLOAT, [SUBMIT_LOG] BLOB, [CHANGES] BLOB, [PRJID] INTEGER NOT NULL DEFAULT 0 CONSTRAINT [HPC_JOB_PRJ_FK] REFERENCES [HPC_PRJTMPL]([PTID]), [TMPLID] INTEGER NOT NULL DEFAULT 0 CONSTRAINT [HPC_JOB_TMPL_FK] REFERENCES [HPC_PRJTMPL]([PTID]), [RESRS] NVARCHAR2(1), [VERID] INTEGER CONSTRAINT [HPC_JOB_VER_FK] REFERENCES [HPC_VER]([VERID]) ON DELETE SET NULL, [PYVERID] INTEGER NOT NULL DEFAULT 0 CONSTRAINT [HPC_JOB_PYVER_FK] REFERENCES [HPC_PYVER]([PYVERID]), [JOBNAME] VARCHAR(128), [FNCID] INTEGER CONSTRAINT [HPC_JOB_FNC_FK] REFERENCES [HPC_FUNCLASS]([FCID]), [CLSID] INTEGER CONSTRAINT [HPC_JOB_CLS_FK] REFERENCES [HPC_FUNCLASS]([FCID]), [STATEID] INTEGER DEFAULT 0 CONSTRAINT [FK_JOB_STATE] REFERENCES [HPC_STATE]([STATEID]) ON DELETE CASCADE, [TASK_CNT] INTEGER DEFAULT 0, [SPID] INTEGER DEFAULT 0)
CREATE UNIQUE INDEX [HPC_JOB_UK] ON [HPC_JOB] ([HPCJOBID], [NODEID])
CREATE TABLE [HPC_MASTERJOB] ([MASTERJOBID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [MASTERID] INTEGER NOT NULL, [NODEID] INTEGER NOT NULL CONSTRAINT [HPC_MASTERJOB_NODE_FK] REFERENCES [HPC_NODE]([NODEID]) ON DELETE CASCADE, [JOBID] INTEGER CONSTRAINT [HPC_MASTERJOB_JOB_FK] REFERENCES [HPC_JOB]([JOBID]) ON DELETE CASCADE, [BUILDNO] INTEGER NOT NULL, [STATUS] NVARCHAR2(64), UNIQUE ([NODEID], [MASTERID]))
CREATE TABLE [HPC_TASK] ([TASKID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [JOBID] INTEGER NOT NULL CONSTRAINT [FK_JOBID] REFERENCES [HPC_JOB]([JOBID]) ON DELETE CASCADE, [HPCTASKID] INTEGER NOT NULL, [TASKNAME] VARCHAR2(128), [REQUEUE] INTEGER NOT NULL DEFAULT 0, [EXITCODE] INTEGER CONSTRAINT [HPC_TASK_EXIT_FK] REFERENCES [HPC_EXITCODES]([EXITCODE]) ON DELETE SET NULL, [STDOUT] BLOB, [SLAVEID] INTEGER NOT NULL CONSTRAINT [HPC_TASK_SLAVE_FK] REFERENCES [HPC_SLAVE]([SLAVEID]) ON DELETE CASCADE DEFAULT 0, [STARTTIME] TIMESTAMP, [STOPTIME] TIMESTAMP, [RECSIZE] INTEGER, [RECDURATION] INTEGER, [CPU_TIME] FLOAT DEFAULT 0, [STATEID] INTEGER DEFAULT 0 CONSTRAINT [FK_TASK_STATE] REFERENCES [HPC_STATE]([STATEID]) ON DELETE CASCADE)
CREATE UNIQUE INDEX [HPC_TASK_UK] ON [HPC_TASK] ([JOBID], [REQUEUE], [HPCTASKID])
CREATE TABLE [HPC_TASKERRORS] ([TASKID] NUMBER NOT NULL CONSTRAINT [HPC_TASKERRORS_TASKID_FK] REFERENCES [HPC_TASK]([TASKID]) ON DELETE CASCADE, [TYPEID] NUMBER NOT NULL CONSTRAINT [HPC_TASKERRORS_TYPE_FK] REFERENCES [HPC_ERRTYPE]([TYPEID]) ON DELETE CASCADE, [CNT] NUMBER NOT NULL, CONSTRAINT [sqlite_autoindex_HPC_TASKERRORS_1] PRIMARY KEY ([TASKID], [TYPEID]))
CREATE TABLE [HPC_SIMCFG] ([CFGID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [CFG] VARCHAR2(4000), [CFGHASH] VARCHAR2(64), [CFGBIN] BLOB)
CREATE TABLE [HPC_ERRORS] ([ERRORID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [TASKID] INTEGER NOT NULL CONSTRAINT [HPC_ERRORS_TASKID_FK] REFERENCES [HPC_TASK]([TASKID]) ON DELETE CASCADE, [TYPEID] INTEGER NOT NULL CONSTRAINT [FK_APPERROR_APPERR_TYPE] REFERENCES [HPC_ERRTYPE]([TYPEID]) ON DELETE CASCADE, [CODE] INTEGER NOT NULL, [DESCR] NVARCHAR2(512), [SRC] NVARCHAR2(512), [ERRDATE] TIMESTAMP, [CNT] INTEGER NOT NULL DEFAULT 1, [MTSTIME] INTEGER NOT NULL DEFAULT 0)
CREATE TABLE [HPC_SUBTASK] ([SUBID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [TASKID] INTEGER NOT NULL CONSTRAINT [HPC_SUBTASK_TASK_FK] REFERENCES [HPC_TASK]([TASKID]) ON DELETE CASCADE, [SUBTASKID] INTEGER NOT NULL, [STARTTIME] TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, [STOPTIME] TIMESTAMP, [EXITCODE] INTEGER NOT NULL CONSTRAINT [HPC_SUBTASK_EXIT_FK] REFERENCES [HPC_EXITCODES]([EXITCODE]) ON DELETE SET NULL DEFAULT 0, [COMMAND] NVARCHAR2(32), [PID] INTEGER, [MEASID] INTEGER CONSTRAINT [HPC_SUBTASK_MEAS_FK] REFERENCES [DMT_FILES]([MEASID]) ON DELETE SET NULL, [APP] NVARCHAR2(64), [CFGID] INTEGER CONSTRAINT [HPC_SUBTASK_CFG_FK] REFERENCES [HPC_SIMCFG]([CFGID]) ON DELETE SET NULL, [DISK_IO] INTEGER, [CPU_TIME] FLOAT DEFAULT 0)
CREATE TABLE [HPC_SUBTASK_WDOG] ([WDOGID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [SUBID] INTEGER NOT NULL CONSTRAINT [HPC_SUBTASK_WDOG_FK] REFERENCES [HPC_SUBTASK]([SUBID]) ON DELETE CASCADE, [IOLOAD] INTEGER NOT NULL, [IOCONF] INTEGER NOT NULL, [CPULOAD] INTEGER NOT NULL, [CPUCONF] INTEGER NOT NULL, [MEMLOAD] INTEGER NOT NULL, [VIRTLOAD] INTEGER NOT NULL, [NETLOAD] INTEGER NOT NULL, [WDOGTIME] INTEGER NOT NULL)
CREATE UNIQUE INDEX [HPC_SUBTASK_UK] ON [HPC_SUBTASK] ([TASKID], [SUBTASKID])
CREATE TABLE [HPC_TASK_ECODE_HIST] ([HISTID] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, [TASKID] INTEGER NOT NULL CONSTRAINT [HPC_ECODE_HIST_TASK_FK] REFERENCES [HPC_TASK]([TASKID]) ON DELETE CASCADE, [EXITCODE] INTEGER NOT NULL CONSTRAINT [HPC_ECODE_HIST_ECODE_FK] REFERENCES [HPC_EXITCODES]([EXITCODE]) ON DELETE CASCADE, [LOGTIME] TIMESTAMP NOT NULL)
-- now insert some data into the tables
insert into HPC_NODE (NODENAME, LOCATION) values ('OTHER', 'misc')
insert into HPC_NODE (NODENAME, LOCATION) values ('UNIT000', 'misc')
insert into HPC_NODE (NODENAME, LOCATION) values ('LU00156VMA', 'LND')
insert into HPC_NODE (NODENAME, LOCATION) values ('LU00160VMA', 'LND')
insert into HPC_NODE (NODENAME, LOCATION) values ('LU00199VMA', 'LND')
insert into HPC_NODE (NODENAME, LOCATION) values ('LU00200VMA', 'LND')
insert into HPC_NODE (NODENAME, LOCATION) values ('LUAS003A', 'LND')
insert into HPC_NODE (NODENAME, LOCATION) values ('LUAS004A', 'LND')
insert into HPC_NODE (NODENAME, LOCATION) values ('LSAS002A', 'FFM')
insert into HPC_NODE (NODENAME, LOCATION) values ('LSAS003A', 'FFM')
insert into HPC_NODE (NODENAME, LOCATION) values ('LSAS095A', 'FFM')
insert into HPC_NODE (NODENAME, LOCATION) values ('QHS6U5BA', 'ABH')
insert into HPC_NODE (NODENAME, LOCATION) values ('QHS6U5CA', 'ABH')
insert into HPC_NODE (NODENAME, LOCATION) values ('OZAS012A', 'BLR')
insert into HPC_NODE (NODENAME, LOCATION) values ('OZAS013A', 'BLR')
insert into HPC_NODE (NODENAME, LOCATION) values ('ITAS004A', 'SHB')
insert into HPC_NODE (NODENAME, LOCATION) values ('ITAS005A', 'SHB')
insert into HPC_SLAVE (SLAVEID, NODEID, NAME) values(0, (SELECT NODEID FROM HPC_NODE WHERE NODENAME = 'OTHER'), '(missing)')
insert into HPC_LOGITEM (IID, NAME) values(0, 'unknown/missing')
insert into HPC_ERRTYPE (TYPEID, TYPENAME) values (0, 'Crash')
insert into HPC_ERRTYPE (TYPEID, TYPENAME) values (1, 'Exception')
insert into HPC_ERRTYPE (TYPEID, TYPENAME) values (2, 'Error')
insert into HPC_ERRTYPE (TYPEID, TYPENAME) values (3, 'Alert')
insert into HPC_ERRTYPE (TYPEID, TYPENAME) values (4, 'Warning')
insert into HPC_ERRTYPE (TYPEID, TYPENAME) values (5, 'Information')
insert into HPC_ERRTYPE (TYPEID, TYPENAME) values (6, 'Debug')
insert into HPC_PRJTMPL (PTID, NAME) values (0, null)
insert into HPC_VER (VERID, VERSTR) values(1, 'unknown')
insert into HPC_PYVER (PYVERID, VERSTR) values(0, 'unknown')
insert into HPC_FUNCLASS (FCID, FCNAME) values(0, 'n/a')
insert into HPC_STATE values(0, 'None')
insert into HPC_STATE values(1, 'Configuring')
insert into HPC_STATE values(2, 'Submitted')
insert into HPC_STATE values(4, 'Validating')
insert into HPC_STATE values(8, 'Dispatching')
insert into HPC_STATE values(16, 'Queued')
insert into HPC_STATE values(32, 'Running')
insert into HPC_STATE values(64, 'Finishing')
insert into HPC_STATE values(128, 'Finished')
insert into HPC_STATE values(256, 'Failed')
insert into HPC_STATE values(512, 'Canceled')
insert into HPC_STATE values(1024, 'Canceling')
-- generate new inserts, copy / paste this:
-- select 'insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(' || to_char(exitcode) || ', ''' || descr || ''', ' || to_char(prio) || ')' from hpc_exitcodes where exitcode >= 0 order by prio;
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(2, 'application: wrong argument (python)', 119)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(150, 'infrastructure: unspecified error found', 510)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(152, 'infrastructure: (robo)copy caused an error', 512)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(153, 'infrastructure: network name is not longer available', 513)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(154, 'infrastructure: failed to connect to DB', 514)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(155, 'infrastructure: recording is not available', 516)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(156, 'infrastructure: (robo)copy overwrote output data files', 517)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(157, 'infrastructure: recording is archived', 518)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(159, 'infrastructure: GPU driver or kernel module error', 519)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(146, 'MTS error: failed to add merge candidate', 520)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(31, 'infrastructure: low temp space (D:)', 521)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(41, 'application CPU idle', 522)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(42, 'application IO idle', 523)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(43, 'application print out idle', 524)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(46, 'application timeout', 525)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(49, 'application hang / was terminated', 526)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(50, 'wrapper application failure', 527)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(219, 'user generated error 219', 528)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(218, 'user generated error 218', 529)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(217, 'user generated error 217', 530)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(216, 'user generated error 216', 531)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(215, 'user generated error 215', 532)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(214, 'user generated error 214', 533)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(213, 'user generated error 213', 534)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(212, 'user generated error 212', 535)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(211, 'user generated error 211', 536)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(210, 'user generated error 210', 537)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(209, 'user generated error 209', 538)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(208, 'user generated error 208', 539)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(207, 'user generated error 207', 540)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(206, 'user generated error 206', 541)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(205, 'user generated error 205', 542)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(204, 'user generated error 204', 543)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(203, 'user generated error 203', 544)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(202, 'user generated error 202', 545)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(201, 'user generated error 201', 546)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(200, 'user generic error', 547)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(145, 'MTS: no error log available', 548)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(141, 'MTS info: output generated successfully', 549)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(112, 'simulation BSIG corrupt', 550)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(113, 'duration of recording and BSIG differ', 551)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(114, 'BSIG has too many time jumps', 552)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(115, 'no BSIGs at all produced', 553)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(47, 'application IPv4 retransmit rate too high', 554)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(48, 'application IPv6 retransmit rate too high', 555)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(51, 'application low virtual memory', 557)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(52, 'application low CPU power', 558)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(53, 'application high memory usage', 559)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(54, 'application fatal message', 560)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(60, 'floating point exception: invalid operation', 561)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(61, 'floating point exception: division by zero', 562)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(62, 'floating point exception: overflow', 563)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(63, 'floating point exception: underflow', 564)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(64, 'floating point exception: inexact operation', 565)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(65, 'floating point exception: denormal operation', 566)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(66, 'floating point exception: stack check', 567)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(70, 'MTS crash: access violation', 568)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(71, 'MTS crash: invalid parameter', 569)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(72, 'MTS crash: array bounds exceeded', 570)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(73, 'MTS crash: breakpoint', 571)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(74, 'MTS crash: float divide by zero', 572)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(75, 'MTS crash: invalid operation', 573)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(76, 'MTS crash: guard page', 574)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(77, 'MTS crash: illegal instruction', 575)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(78, 'MTS crash: integer division by zero', 576)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(79, 'MTS crash: integer overflow', 577)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(80, 'MTS crash: invalid handle', 578)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(81, 'MTS crash: privileged instruction', 579)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(82, 'MTS crash: single step', 580)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(83, 'MTS crash: stack buffer overrun', 581)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(84, 'MTS crash: fatal app exit', 582)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(85, 'MTS crash: thread activation context', 583)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(90, 'MTS exception: near scan peak error', 584)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(91, 'MTS exception: far scan peak error', 585)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(92, 'MTS exception: peak error at position x', 586)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(93, 'MTS exception: access violation', 587)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(94, 'MTS exception: inconsistent data structure', 588)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(95, 'MTS exception: config of MO missing', 589)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(96, 'MTS exception: MO code error', 590)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(97, 'MTS exception: BMW radome correction', 591)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(98, 'MTS exception: unknown exception', 592)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(99, 'MTS exception: unhandled exception', 593)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(110, 'MTS error: network unavailable', 594)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(111, 'MTS error: recording corrupt', 595)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(100, 'MTS unknown exception', 596)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(120, 'MTS error: unspecified', 597)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(121, 'MTS error: crash dump', 598)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(122, 'MTS error: xlog is corrupt', 599)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(123, 'MTS error: block terminated caching thread found', 600)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(124, 'MTS error: application error', 601)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(142, 'MTS error: GPU server execution', 602)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(143, 'MTS error: invalid MDF block', 603)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(125, 'MTS error: unknown error', 605)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(126, 'MTS log: exception found', 606)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(128, 'MTS log: alert found', 607)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(127, 'MTS log: error found', 608)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(129, 'MTS log: warning found', 609)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(130, 'MTS log: info found', 610)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(131, 'MTS log: debug found', 611)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(132, 'MTS log: corrupt crash log found', 612)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(133, 'MTS error: too old DLL detected / used', 613)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(144, 'MTS error: low on memory', 614)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(134, 'MTS error: too much memory in use', 615)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(135, 'MTS xlog not available', 616)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(136, 'MTS error: side-by-side configuration is incorrect', 617)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(138, 'MTS error: cannot open or read configuration', 618)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(137, 'MTS error: reading recording failed', 619)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(139, 'MTS error: recovering data', 620)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(140, 'MTS error: error reported', 621)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(40, 'application unspecified error', 622)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(20, 'unspecified HPC error', 623)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(21, 'application is not local', 624)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(22, 'wrong argument', 625)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(23, 'user canceled task', 626)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(24, 'general database error', 627)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(25, 'reading from DB failed', 628)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(26, 'invalid PID', 629)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(27, 'internal error', 630)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(28, 'cyclic admin job failed', 631)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(29, 'application not found', 632)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(30, 'script malfunction', 633)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(158, 'infrastructure: failed to create task output folders', 635)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(1, 'unspecified', 636)
insert into HPC_EXITCODES(EXITCODE, DESCR, PRIO) values(0, 'OK', 999)
"""


# - functions ----------------------------------------------------------------------------------------------------------
def create_sqlite(filename, statements=SQLITE_DEF, clear=False):
    """
    create an sqlite file by using given statements

    :param ``str`` filename: path and name of sqlite file to create
    :param ``str`` statements: optional sql commands to create tables and fill first values,
                               default: definitions compatible with Oracle HPC DB
    :param ``bool`` clear: delete existing sqlite file in any case, default: use existing if available
    :returns: path and name of created file
    :rtype: str
    """
    if clear and exists(filename):
        unlink(filename)

    if not exists(filename):
        with BaseDB(filename, create=True, autocommit=False) as bdb:
            update_stmts(bdb, statements)

    return filename


def update_stmts(dbase, statements=SQLITE_DEF):
    r"""
    update / insert statements

    :param BaseDb dbase: database connection
    :param str statements: sql statements (\n separated)
    """
    for i in statements.split('\n'):
        if i and not i.startswith("--"):
            dbase(i)
    dbase.commit()
