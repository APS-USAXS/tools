<?xml version="1.0" encoding="UTF-8"?>
<!-- 
    ########### SVN repository information ###################
    # $Date: 2010-07-24 23:13:42 -0500 (Sat, 24 Jul 2010) $
    # $Author: jemian $
    # $Revision: 386 $
    # $URL: https://subversion.xor.aps.anl.gov/small_angle/USAXS/livedata/pvlist.xsl $
    # $Id: pvlist.xsl 386 2010-07-25 04:13:42Z jemian $
    ########### SVN repository information ###################
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

    <xsl:template match="//PV">
        <xsl:value-of select="@pvname"/>
    </xsl:template>

</xsl:stylesheet>
