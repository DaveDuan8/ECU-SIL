@ECHO OFF
REM ===============================================
REM taking ownership of a task (assign to me)
REM by opening a task edit window with updated user
REM usage:
REM      im_assign_task.bat <taskid> 
REM or   im_assign_task.bat -> asks for taskid
REM
REM $Revision: 1.1 $
REM $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
REM $Date: 2015/04/23 19:03:47CEST $

IF "%MKSSI_ISSUE0%"=="" GOTO getTask:
ECHO checking issue %MKSSI_ISSUE0%
FOR /f "tokens=*" %%i in ('im viewissue %MKSSI_ISSUE0% ^| findstr "AD_c.o. Task(s):"') DO SET line=%%i
CALL SET line=%%line:*: =%%
CALL SET taskid=%%line:*, =%%
IF "%taskid%"=="" GOTO getTask:
IF "%line%"=="%taskid%" GOTO assignTask:
ECHO several tasks listed: %line%

:getTask
SET taskid=%1

IF %1.==. SET /p taskid="enter task id to take over:"

:assignTask
echo assigning task %taskid% to you...
im editissue --field='Assigned User=%username%' -g %taskid%

pause