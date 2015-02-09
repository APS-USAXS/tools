#!/bin/csh

setenv PYTHON /APSshare/anaconda/x86_64/bin/python
setenv DIR    ${HOME}/Documents/eclipse/USAXS/tools/qToolUsaxs
setenv TOOL   ${DIR}/qToolUsaxs.py

$PYTHON $TOOL &

########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################
