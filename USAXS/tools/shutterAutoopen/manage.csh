#!/bin/tcsh

# description: 15ID USAXS shutter auto open tool, P. Beaucage
#
# processname: usaxs_update

setenv SCRIPT_DIR	 /home/beams/S15USAXS/Documents/eclipse/USAXS/shutterAutoopen
setenv MANAGE		 ${SCRIPT_DIR}/manage.csh
setenv SCRIPT		 ${SCRIPT_DIR}/shutterAutoopen.py
setenv LOGFILE		 ${SCRIPT_DIR}/log.txt
setenv PIDFILE		 ${SCRIPT_DIR}/pid.txt
setenv PYTHON		 /APSshare/bin/python

switch ($1)
  case "start":
       cd ${SCRIPT_DIR}
       ${PYTHON} ${SCRIPT} >>& ${LOGFILE} &
       setenv PID $!
       /bin/echo ${PID} >! ${PIDFILE}
       /bin/echo "# started ${PID}: ${SCRIPT}"
       breaksw
  case "stop":
       cd ${SCRIPT_DIR}
       setenv PID `/bin/cat ${PIDFILE}`
       # get the full list of PID children
       # this line trolls pstree and strips non-numbers
       set pidlist=`pstree -p $PID | tr -c "[:digit:]"  " " `
       /bin/ps ${PID} >! /dev/null
       setenv NOT_EXISTS $?
       if (${NOT_EXISTS}) then
            /bin/echo "# not running ${PID}: ${SCRIPT}" >>& ${LOGFILE} &
       else
            kill ${PID}
            /bin/echo "# stopped ${PID}: ${SCRIPT}" >>& ${LOGFILE} &
            /bin/echo "# stopped ${PID}: ${SCRIPT}"
       endif
       # the python code starts a 2nd PID which also needs to be stopped
       setenv PID `expr "${pidlist}" : '[0-9]*\( [0-9]*\)'`
       /bin/ps ${PID} >! /dev/null
       setenv NOT_EXISTS $?
       if (${NOT_EXISTS}) then
            /bin/echo "not running ${PID}: ${SCRIPT}" >>& ${LOGFILE} &
       else
            if (${PID} != "") then
		 kill ${PID}
 		 /bin/echo "# stopped ${PID}: ${SCRIPT}" >>& ${LOGFILE} &
 		 /bin/echo "# stopped ${PID}: ${SCRIPT}"
	    endif
       endif
       breaksw
  case "restart":
       $0 stop
       $0 start
       breaksw
  case "checkup":
       #=====================
       # call peridiocally (every 5 minutes) to see if livedata is running
       #=====================
       #	field	       allowed values
       #      -----	     --------------
       #      minute	     0-59
       #      hour	     0-23
       #      day of month   1-31
       #      month	     1-12 (or names, see below)
       #      day of week    0-7 (0 or 7 is Sun, or use names)
       #
       # */5 * * * * /home/beams/S15USAXS/Documents/eclipse/USAXS/livedata/manage.csh checkup 2>&1 /dev/null
       #
       set pid = `/bin/cat ${PIDFILE}`
       setenv RESPONSE `ps -p ${pid} -o comm=`
       if (${RESPONSE} != "python") then
          echo "# `/bin/date` could not identify running process ${pid}, restarting" >>& ${LOGFILE}
	  # swallow up any console output
          echo `${MANAGE} restart` >& /dev/null
       endif
       breaksw
  default:
       /bin/echo "Usage: $0 {start|stop|restart|checkup}"
       breaksw
endsw
