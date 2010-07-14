#!/bin/csh
########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################


setenv PYTHON /APSshare/bin/python
setenv DIR    /home/beams/S15USAXS/Documents/eclipse/USAXS/tools
setenv TOOL   ${DIR}/scanTimeCalc.py

$PYTHON $TOOL &
