
########### SVN repository information ###################
# $Date: 2010-08-09 16:57:57 -0500 (Mon, 09 Aug 2010) $
# $Author: jemian $
# $Revision: 391 $
# $URL: https://subversion.xor.aps.anl.gov/small_angle/USAXS/livedata/Makefile $
# $Id: Makefile 391 2010-08-09 21:57:57Z jemian $
########### SVN repository information ###################

DATE_STRING   = `date '+%Y%m%d-%H%M%S'`

clean :: $(TARLIST)
	./manage.csh stop
	/bin/echo "`/bin/date`: restarted usaxs livedata ..." > log.txt
	./manage.csh start

start :: $(TARLIST)
	./manage.csh start

stop :: $(TARLIST)
	./manage.csh stop

restart :: $(TARLIST)
	./manage.csh restart

all :: clean
