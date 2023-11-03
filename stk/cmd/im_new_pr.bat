@ECHO OFF
REM ===============================================================
REM create new Problem Report Issue for STK with some preset fields
REM
REM keep Issue window open for further editing
REM
REM $Revision: 1.1 $
REM $Author: Hospes, Gerd-Joachim (uidv8815) $ (last change)
REM $Date: 2015/04/23 19:03:48CEST $

SET sum=--field="Summary=[STK]  "
SET type=--field="Issue Type=Problem Report"
SET user=--field="Assigned User=uidv8815"
SET prj=--field="Project=/Validation_Tools"
SET struct=--field="Structure Element=STK_ScriptingToolKit - /Validation_Tools"
SET desc=--field="Description=add a detailed description here. Please list the version where you found the issue and don't forget to set urgency!"
SET urgent=--field="Urgency=Low"
SET imprt=--field="Importance=Low"

im createissue --type=Issue %type% %sum% %desc% %prj% %struct% %user% %urgent% %imprt% -g