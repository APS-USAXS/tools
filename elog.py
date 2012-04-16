#!/usr/bin/env python

'''
write current instrument conditions to the elog
'''

########### SVN repository information ###################
# $Date$
# $Author$
# $Revision$
# $URL$
# $Id$
########### SVN repository information ###################


import setup_PyEpics_uc2
from epics import PV
from epics import caget
import sys, epics, time, string, os

# Create global variables with lists of PVs for various groups of information 

#			PV name[0]		   PV name[1]			    Message[2]             Use?[3]
undulator = 	[	('15IDA:ID15_gap',     '15IDA:ID15_gap',	  'Undulator gap (mm)',	 	    'Y'),
	                ('15IDA:ID15_energy',  '15IDA:ID15_energy',       'Undulator energy (keV)',         'Y')]

HHL_Slits = 	[   	('15IDA:m17.RBV',     '15IDA:m17.DRBV',  	  '(m17) HHL-Hor-Slit-Up (mm)',      'Y'),
       			('15IDA:m18.RBV',     '15IDA:m18.DRBV',	          '(m18) HHL-Vert-Slit-Up(mm)',      'Y'),
       			('15IDA:m19.RBV',     '15IDA:m19.DRBV',	          '(m19) HHL-Hor-Slit-Dwr(mm)',      'Y'),
       			('15IDA:m20.RBV',     '15IDA:m20.DRBV',	          '(m20) HHL-Vert-Slit-Dwr(mm)',     'Y')]

Monochromator = [	('15IDA:BraggERdbkAO','15IDA:BraggERdbkAO',  	  'Monochromator energy (keV)',      'Y'),
       			('15IDA:m10.RBV',     '15IDA:m10.DRBV',           '(m10) Bragg-Angle(degrees)',      'Y'),
      			('15IDA:m11.RBV',     '15IDA:m11.DRBV',           '(m11) Xtal-Gap(mm)',              'Y'),
       			('15IDA:m30.RBV',     '15IDA:m30.DRBV',  	  '(m30) 1st-Xtal-Roll(degrees)',    'Y'),
       			('15IDA:m31.RBV',     '15IDA:m31.DRBV',	          '(m31) 2nd-Xtal-Roll(degrees)',    'Y'),
       			('15IDA:m32.RBV',     '15IDA:m32.DRBV', 	  '(m32) 2nd-Xtal-Pitch(degrees)',   'Y')]

ADC_Slits = 	[	('15IDA:m25.RBV',     '15IDA:m25.DRBV',           '(m25) UHV-Slit-top(mm)',          'Y'),
       			('15IDA:m26.RBV',     '15IDA:m26.DRBV',	          '(m26) UHV-Slit-Bot(mm)',          'Y'),
       			('15IDA:m27.RBV',     '15IDA:m27.DRBV', 	  '(m27) UHV-Slit-InB(mm)',          'Y'),
       			('15IDA:m28.RBV',     '15IDA:m28.DRBV',	          '(m28) UHV-Slit-OutB(mm)',         'Y')]

bpm_up =	[	('15IDA:m21.RBV',     '15IDA:m21.DRBV', 	  '(m21) Upstream-BPM-Foil(mm)',     'Y')]
 
bpm_down = 	[       ('15IDA:m22.RBV',     '15IDA:m22.DRBV', 	  '(m22) Downstream-BPM-Foil(mm)',   'Y')]

Mirrors = 	[	('15IDA:m4.RBV',      '15IDA:m4.DRBV',   	  '(m4) VFM-Translation(mm)',        'Y'),
       			('15IDA:m5.RBV',      '15IDA:m5.DRBV',	          '(m5) VFM-VDM-Stripe(mm)',         'Y'),
       			('15IDA:m6.RBV',      '15IDA:m6.DRBV', 	          '(m6) VFM-Pitch    (mrad)',        'Y'),
       			('15IDA:m7.RBV',      '15IDA:m7.DRBV',	          '(m7) VDM-Translation(mm)',        'Y'),
       			('15IDA:m8.RBV',      '15IDA:m8.DRBV', 	          '(m8) VDM-Pitch  (mrad)',          'Y')]

USAXS_Slits = 	[	('15iddLAX:m58:c2:m5.RBV',     '15iddLAX:m58:c2:m5.DRBV',        'USAXS Slit vert center(mm)',          'Y'),
       			('15iddLAX:m58:c2:m6.RBV',     '15iddLAX:m58:c2:m6.DRBV',	 'USAXS Slit hor  center(mm)',          'Y'),
       			('15iddLAX:m58:c2:m7.RBV',     '15iddLAX:m58:c2:m7.DRBV', 	 'USAXS Slit vert aperture(mm)',        'Y'),
       			('15iddLAX:m58:c2:m8.RBV',     '15iddLAX:m58:c2:m8.DRBV',        'USAXS Slit hor  aperture(mm)',	'Y')]


M_stage = 	[	('15iddLAX:xps:c0:m1.RBV',     '15iddLAX:xps:c0:m1.DRBV',        'USAXS MR (degrees)',                    'Y'),
       			('15iddLAX:m58:c0:m2.RBV',     '15iddLAX:m58:c0:m2.DRBV',	 'USAXS mx (mm)',		          'Y'),
       			('15iddLAX:m58:c0:m3.RBV',     '15iddLAX:m58:c0:m3.DRBV', 	 'USAXS my (mm)',		          'Y'),
       			('15iddLAX:m58:c0:m4.RBV',     '15iddLAX:m58:c0:m4.DRBV',        'USAXS m1y(mm)',		       	  'Y'),
			('15iddLAX:USAXS:MRcenter',    '15iddLAX:USAXS:MRcenter',        'USAXS MR center',		          'Y')]

MS_stage = 	[	('15iddLAX:xps:c0:m5.RBV',     '15iddLAX:xps:c0:m5.DRBV',        'USAXS MS stage angle(degrees)',         'Y'),
       			('15iddLAX:m58:c1:m1.RBV',     '15iddLAX:m58:c1:m1.DRBV',	 'USAXS msx (mm)',		          'Y'),
       			('15iddLAX:m58:c1:m2.RBV',     '15iddLAX:m58:c1:m2.DRBV', 	 'USAXS msy (mm)',		          'Y'),
       			('15iddLAX:xps:c0:m3.RBV',     '15iddLAX:xps:c0:m3.DRBV',        'USAXS mst (deg)',		       	  'Y'),
			('15iddLAX:USAXS:MSRcenter',    '15iddLAX:USAXS:MSRcenter',        'USAXS MSR center',		          'Y')]


AS_stage = 	[	('15iddLAX:xps:c0:m6.RBV',     '15iddLAX:xps:c0:m6.DRBV',        'USAXS AS stage angle(degrees)',         'Y'),
       			('15iddLAX:m58:c1:m3.RBV',     '15iddLAX:m58:c1:m3.DRBV',	 'USAXS asx (mm)',		          'Y'),
       			('15iddLAX:m58:c1:m4.RBV',     '15iddLAX:m58:c1:m4.DRBV', 	 'USAXS asy (mm)',		          'Y'),
       			('15iddLAX:xps:c0:m4.RBV',     '15iddLAX:xps:c0:m4.DRBV',        'USAXS ast (deg)',		       	  'Y'),
 			('15iddLAX:USAXS:ASRcenter',    '15iddLAX:USAXS:ASRcenter',      'USAXS ASR center',		          'Y')]

A_stage = 	[	('15iddLAX:aero:c0:m1.RBV',     '15iddLAX:aero:c0:m1.DRBV',      'USAXS AR (degrees)',                    'Y'),
       			('15iddLAX:m58:c0:m5.RBV',     '15iddLAX:m58:c0:m5.DRBV',	 'USAXS ax (mm)',		          'Y'),
       			('15iddLAX:m58:c0:m6.RBV',     '15iddLAX:m58:c0:m6.DRBV', 	 'USAXS ay (mm)',		          'Y'),
       			('15iddLAX:m58:c0:m7.RBV',     '15iddLAX:m58:c0:m7.DRBV',        'USAXS az (mm)',		       	  'Y'),
			('15iddLAX:USAXS:ARcenter',    '15iddLAX:USAXS:ARcenter',        'USAXS AR center',		          'Y')]

User_Info = 	[	('15iddLAX:RunCycle',          '15iddLAX:RunCycle',              'Run cycle',                             'Y'),
       			('15iddLAX:UserName',          '15iddLAX:Username',    	         'User name',		                  'Y'),
       			('15iddLAX:GUPNumber',         '15iddLAX:GUPNumber', 	         'GUP number',		                  'Y')]

Amplifiers = 	[	('15iddUSX:fem03:seq01:gain',  '15iddUSX:fem03:seq01:gain',      'I00 Gain',                              'Y'),
       			('15iddUSX:fem02:seq01:gain',  '15iddUSX:fem02:seq01:gain',      'I0 Gain',		                  'Y'),
       			('15iddLAX:m58:c1:m5.RBV',     '15iddLAX:m58:c1:m5.DRBV', 	 'I0 stage (mm)',	                  'Y')]

SD_stages = 	[	('15iddLAX:m58:c2:m1.RBV',     '15iddLAX:m58:c2:m1.DRBV',        'USAXS sx (mm)',                         'Y'),
       			('15iddLAX:m58:c0:m2.RBV',     '15iddLAX:m58:c0:m2.DRBV',	 'USAXS sy (mm)',		          'Y'),
       			('15iddLAX:m58:c0:m3.RBV',     '15iddLAX:m58:c0:m3.DRBV', 	 'USAXS dx (mm)',		          'Y'),
       			('15iddLAX:m58:c0:m4.RBV',     '15iddLAX:m58:c0:m4.DRBV',        'USAXS dy (mm)',		       	  'Y')]

PinSAXS = 	[	('15iddLAX:mxv:c0:m1.RBV',     '15iddLAX:mxv:c0:m1.DRBV',        'USAXS pin_x (mm)',                      'Y'),
       			('15iddLAX:mxv:c0:m2.RBV',     '15iddLAX:mxv:c0:m2.DRBV', 	 'USAXS pin_z (mm)',		          'Y'),
       			('15iddLAX:mxv:c0:m8.RBV',     '15iddLAX:mxv:c0:m8.DRBV',        'USAXS pin_y (mm)',		       	  'Y')]

USAXS_Params = 	[	('15iddLAX:USAXS:CountTime',   		'15iddLAX:USAXS:CountTime',    			'USAXS Count Time',           	'Y'),
			('15iddLAX:USAXS:NumPoints',   		'15iddLAX:USAXS:NumPoints',    			'USAXS Num Points',             'Y'),
			('15iddLAX:USAXS:Finish',    		'15iddLAX:USAXS:Finish',    			'USAXS Q max',                 	'Y'),
			('15iddLAX:USAXS:StartOffset',  	'15iddLAX:USAXS:StartOffset',    		'USAXS Start Offset',          	'Y'),
			('15iddLAX:USAXS:Sample_Y_Step',  	'15iddLAX:USAXS:Sample_Y_Step',    		'USAXS Sample Y Step',         	'Y'),
			('15iddLAX:USAXS_Pin:ax_in',	   	'15iddLAX:USAXS_Pin:ax_in',   			'USAXS ax in',                	'Y'),
			('15iddLAX:USAXS_Pin:Pin_y_out',	   	'15iddLAX:USAXS_Pin:Pin_y_out',   	'USAXS pin_y out',             	'Y'),
			('15iddLAX:USAXS_Pin:Pin_z_out',	   	'15iddLAX:USAXS_Pin:Pin_z_out',   	'USAXS pin_z out',             	'Y'),		
			('15iddLAX:USAXS_Pin:USAXS_hslit_ap',   	'15iddLAX:USAXS_Pin:USAXS_hslit_ap',    'USAXS hor slit',               'Y'),
       			('15iddLAX:USAXS_Pin:USAXS_vslit_ap',   	'15iddLAX:USAXS_Pin:USAXS_hslit_ap',    'USAXS vert slit',              'Y'),
       			('15iddLAX:USAXS_Pin:USAXS_hgslit_ap',   	'15iddLAX:USAXS_Pin:USAXS_hgslit_ap',   'USAXS Guard vert slit',      	'Y'),
       			('15iddLAX:USAXS_Pin:USAXS_vgslit_ap',   	'15iddLAX:USAXS_Pin:USAXS_vgslit_ap',   'USAXS Guard vert slit',      	'Y')]
			
Pin_Params = 	[	('15iddLAX:WavelengthSpread',   	'15iddLAX:WavelengthSpread',    		'Wavelength Spread',           	'Y'),
			('15iddLAX:USAXS_Pin:BeamCenterX',	'15iddLAX:USAXS_Pin:BeamCenterX',    		'PinSAXS Beam Center X',        'Y'),
			('15iddLAX:USAXS_Pin:BeamCenterY',    	'15iddLAX:USAXS_Pin:BeamCenterY',    		'PinSAXS Beam Center Y',       	'Y'),
			('15iddLAX:USAXS_Pin:Distance',  	'15iddLAX:USAXS_Pin:Distance',    		'PinSAXS distance (mm)',      	'Y'),
			('15iddLAX:USAXS_Pin:PinPixSizeX',  	'15iddLAX:USAXS_Pin:PinPixSizeX',    		'PinSAXS pixels size X (mm)',  	'Y'),
			('15iddLAX:USAXS_Pin:PinPixSizeY',  	'15iddLAX:USAXS_Pin:PinPixSizeY',    		'PinSAXS pixels size Y (mm)',  	'Y'),
			('15iddLAX:USAXS_Pin:Exp_Al_Filter',  	'15iddLAX:USAXS_Pin:Exp_Al_Filter',    		'PinSAXS Exp Al Filter',  	'Y'),
			('15iddLAX:USAXS_Pin:Exp_Ti_Filter',  	'15iddLAX:USAXS_Pin:Exp_Ti_Filter',    		'PinSAXS Exp Ti Filter',  	'Y'),
			('15iddLAX:USAXS_Pin:directory',  	'15iddLAX:USAXS_Pin:directory',    		'PinSAXS Image bese directory', 'Y'),
			('15iddLAX:USAXS_Pin:ax_out',	   	'15iddLAX:USAXS_Pin:ax_out',   			'PinSAXS ax out',             	'Y'),
			('15iddLAX:USAXS_Pin:dx_out',	   	'15iddLAX:USAXS_Pin:dx_out',   			'PinSAXS dx out',             	'Y'),
			('15iddLAX:USAXS_Pin:Pin_y_in',	   	'15iddLAX:USAXS_Pin:Pin_y_in',   		'PinSAXS pin_y in',           	'Y'),
			('15iddLAX:USAXS_Pin:Pin_z_in',	   	'15iddLAX:USAXS_Pin:Pin_z_in',   		'PinSAXS pin_z in',             'Y'),					
			('15iddLAX:USAXS_Pin:AcquireTime',   	'15iddLAX:USAXS_Pin:AcquireTime',   	 	'PinSAXS acquire time',         'Y'),
			('15iddLAX:USAXS_Pin:Pin_hslit_ap',   	'15iddLAX:USAXS_Pin:Pin_hslit_ap',   	 	'PinSAXS hor slit',             'Y'),
       			('15iddLAX:USAXS_Pin:Pin_vslit_ap',   	'15iddLAX:USAXS_Pin:Pin_hslit_ap',    		'PinSAXS vert slit',            'Y'),
       			('15iddLAX:USAXS_Pin:Pin_hgslit_ap',   	'15iddLAX:USAXS_Pin:Pin_hgslit_ap',    		'PinSAXS Guard vert slit',      'Y'),
       			('15iddLAX:USAXS_Pin:Pin_vgslit_ap',   	'15iddLAX:USAXS_Pin:Pin_vgslit_ap',    		'PinSAXS Guard vert slit',      'Y')]


size2 = 33

# end of global definitions

# create some functions...


def createTitle():
    #space1 = size1 - len('PV Name')+1
    space2 = size2 - len('Description (FOE)')+1
    space3 = 8
    title = 'Description (FOE)'+space2*' '+'User Value' + space3*' ' + 'Dial Value'
    spaces = 15*" "
    f.write(title + '\n')


def writeLines(list):

    #Create lines
    def createLine(i):
        """Returns entries format"""
        getpv1 = PV(pvname=list[i][0])
        time.sleep(.2)
        getpv2 = PV(pvname=list[i][1])
        time.sleep(.2)
        s1 = getpv1.char_value
        s2 = getpv2.char_value
        space1 = size2 - len(list[i][2])+1 
	space2 = size2 - len(str(caget(list[i][0])))-10 
        line = list[i][2]+space1*' '+str(s1) + space2*' ' + str(s2)
        return line 

    #Enter the entries 
    """
    for i in range(len(list)):
    	if (i+1)%2 == 0:
	    line = createLine(i)
            f.write(line + '\n')
    	else:
	    length = len(str(caget(list[i][1])))
	    number = 15 - length
	    spaces = " " * number
	    line = createLine(i)
    	    f.write(line + spaces)
    """
    for i in range(len(list)):
	line = createLine(i)
        f.write(line + '\n')

#Check whether even or odd
def numCheck(list):
    if len(list)%2 == 0:
	writeLines(list)
    else:
        writeLines(list)
        f.write('\n')



#Create categories
def createCategory(title):
    NUMBER = 47 + 14
    halfnum = (NUMBER - len(title))/2
    dashes = halfnum * "-"
    createLine = "\n" + dashes + ">" + title + "<" + dashes + "\n"
    f.write(createLine)


#  End of create functions...

# write the log file.... 
  
    
# and this now gets run when all above was setup....    
# Open file
f=file('/share1/Elog/ID_elog_data','w+')

#Write into respective columns
createTitle()
createCategory("User Information")
numCheck(User_Info)
createCategory("Undulator")
numCheck(undulator)
createCategory("HHL Slits")
numCheck(HHL_Slits)
createCategory("Monochromator")
numCheck(Monochromator)
createCategory("ADC slits")
numCheck(ADC_Slits)
createCategory("Mirrors")
numCheck(Mirrors)
createCategory("USAXS slits positons")
numCheck(USAXS_Slits)
createCategory("USAXS M stage")
numCheck(M_stage)
createCategory("USAXS MS stage")
numCheck(MS_stage)
createCategory("USAXS AS stage")
numCheck(AS_stage)
createCategory("USAXS A stage")
numCheck(A_stage)
createCategory("USAXS Sample and Detector stages")
numCheck(SD_stages)
createCategory("USAXS PinSAXS stage")
numCheck(PinSAXS)
createCategory("USAXS Aplifiers")
numCheck(Amplifiers)
createCategory("USAXS Parameters")
numCheck(USAXS_Params)
createCategory("PinSAXS parameters")
numCheck(Pin_Params)
f.close()

#Run elog client to add to logbook. Have to add as an attachment. Table is messed up if it is sent as text.

#os.system('elog -h 164.54.162.133 -p 8081 -l 15-ID-D -a Author=SYSTEM -a Type=Routine -a Subject="System snapshot" -f /share1/Elog/ID_elog_data " "')

os.system('elog -h 15id.xor.aps.anl.gov -p 8096 -l "15ID Operations" -u "s15usaxs" "mu8rubo!" -a "Author=USAXS" -a "Category=USAXS_operations" -a "Type=Configuration" -a "Subject=Instrument/PV Snapshot" -f /share1/Elog/ID_elog_data " "')
