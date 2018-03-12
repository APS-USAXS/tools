#!/usr/bin/env python

'''
write current instrument conditions to the elog
'''


#import setup_PyEpics_uc2	# remove dependency until needed
from epics import PV
from epics import caget
import sys, epics, time, string, os

# Create global variables with lists of PVs for various groups of information

#			PV name[0]		   PV name[1]			    Message[2]             Use?[3]
undulator = 	[	('ID09ds:GapSet.VAL',       'ID09ds:Gap.VAL',	         'Undulator gap (mm)',	 	    'Y'),
                        ('ID09ds:EnergySet.VAL',    'ID09ds:Energy.VAL',          'Undulator ds energy [keV]',      'Y'),
                        ('ID09us:GapSet.VAL',       'ID09us:Gap.VAL',             'Undulator us gap (mm)',          'Y'),
	                ('ID09us:EnergySet.VAL',    'ID09us:Energy.VAL',          'Undulator energy (keV)',         'Y')]

HHL_Slits = 	[   	('9ida:wbsupX.VAL',     '9ida:wbsupXRBV.VAL',  	  'HHL-Upstr-X (mm)',      'Y'),
       			('9ida:wbsupY.VAL',     '9ida:wbsupYRBV.VAL',	  'HHL-Upstr-Y(mm)',      'Y'),
       			('9ida:wbsdnX.VAL',     '9ida:wbsdnXRBV.VAL',	  'HHL-Dwnst-X(mm)',      'Y'),
       			('9ida:wbsdnY.VAL',     '9ida:wbsdnYRBV.VAL',	  'HHL-Dwnst-Y(mm)',     'Y')]

Monochromator = [	('9ida:BraggERdbkAO','9ida:BraggERdbkAO',  	  'Monochromator energy (keV)',      'Y'),
       			('9ida:m11.RBV',     '9ida:m11.DRBV',             '(m11) Bragg-Angle(degrees)',      'Y'),
      			('9ida:m12.RBV',     '9ida:m12.DRBV',             '(m12) Xtal-Gap(mm)',              'Y'),
       			('9ida:m16.RBV',     '9ida:m16.DRBV',  	          '(m16) 2st-Xtal-Chi(degrees)',    'Y'),
      			('9ida:m15.RBV',     '9ida:m15.DRBV', 	           '(m15) 2nd-Xtal-Theta2(degrees)',   'Y')]

#ADC_Slits = 	[	('9ida:m25.RBV',     '9ida:m25.DRBV',           '(m25) UHV-Slit-top(mm)',          'Y'),
#       			('9ida:m26.RBV',     '9ida:m26.DRBV',	          '(m26) UHV-Slit-Bot(mm)',          'Y'),
#       			('9ida:m27.RBV',     '9ida:m27.DRBV', 	  '(m27) UHV-Slit-InB(mm)',          'Y'),
#       			('9ida:m28.RBV',     '9ida:m28.DRBV',	          '(m28) UHV-Slit-OutB(mm)',         'Y')]

#bpm_up =	[	('9ida:m21.RBV',     '9ida:m21.DRBV', 	  '(m21) Upstream-BPM-Foil(mm)',     'Y')]

#bpm_down = 	[       ('9ida:m22.RBV',     '9ida:m22.DRBV', 	  '(m22) Downstream-BPM-Foil(mm)',   'Y')]

USAXS_Slits = 	[	('9idcLAX:m58:c2:m5.RBV',     '9idcLAX:m58:c2:m5.DRBV',        'USAXS Slit vert center(mm)',          'Y'),
       			('9idcLAX:m58:c2:m6.RBV',     '9idcLAX:m58:c2:m6.DRBV',	       'USAXS Slit hor  center(mm)',          'Y'),
       			('9idcLAX:m58:c2:m7.RBV',     '9idcLAX:m58:c2:m7.DRBV', 	 'USAXS Slit vert aperture(mm)',        'Y'),
       			('9idcLAX:m58:c2:m8.RBV',     '9idcLAX:m58:c2:m8.DRBV',        'USAXS Slit hor  aperture(mm)',	'Y')]


M_stage = 	[	('9idcLAX:xps:c0:m1.RBV',     '9idcLAX:xps:c0:m1.DRBV',        'USAXS MR (degrees)',                    'Y'),
       			('9idcLAX:m58:c0:m2.RBV',     '9idcLAX:m58:c0:m2.DRBV',	 	'USAXS mx (mm)',		          'Y'),
       			('9idcLAX:m58:c0:m3.RBV',     '9idcLAX:m58:c0:m3.DRBV', 	 'USAXS my (mm)',		          'Y'),
       			('9idcLAX:m58:c0:m4.RBV',     '9idcLAX:m58:c0:m4.DRBV',        'USAXS m1y(mm)',		       		  'Y'),
			('9idcLAX:USAXS:MRcenter',    '9idcLAX:USAXS:MRcenter',        'USAXS MR center',		          'Y')]

MS_stage = 	[	('9idcLAX:xps:c0:m5.RBV',     '9idcLAX:xps:c0:m5.DRBV',        'USAXS MS stage angle(degrees)',         'Y'),
       			('9idcLAX:m58:c1:m1.RBV',     '9idcLAX:m58:c1:m1.DRBV',	 	'USAXS msx (mm)',		          'Y'),
       			('9idcLAX:m58:c1:m2.RBV',     '9idcLAX:m58:c1:m2.DRBV', 	 'USAXS msy (mm)',		          'Y'),
       			('9idcLAX:xps:c0:m3.RBV',     '9idcLAX:xps:c0:m3.DRBV',        'USAXS mst (deg)',		       	  'Y'),
			('9idcLAX:USAXS:MSRcenter',    '9idcLAX:USAXS:MSRcenter',        'USAXS MSR center',		          'Y')]


AS_stage = 	[	('9idcLAX:xps:c0:m6.RBV',     '9idcLAX:xps:c0:m6.DRBV',        'USAXS AS stage angle(degrees)',         'Y'),
       			('9idcLAX:m58:c1:m3.RBV',     '9idcLAX:m58:c1:m3.DRBV',	 	'USAXS asx (mm)',		          'Y'),
       			('9idcLAX:m58:c1:m4.RBV',     '9idcLAX:m58:c1:m4.DRBV', 	 'USAXS asy (mm)',		          'Y'),
       			('9idcLAX:xps:c0:m4.RBV',     '9idcLAX:xps:c0:m4.DRBV',        'USAXS ast (deg)',		       	  'Y'),
 			('9idcLAX:USAXS:ASRcenter',    '9idcLAX:USAXS:ASRcenter',      'USAXS ASR center',		          'Y')]

A_stage = 	[	('9idcLAX:aero:c0:m1.RBV',     '9idcLAX:aero:c0:m1.DRBV',      'USAXS AR (degrees)',                    'Y'),
       			('9idcLAX:m58:c0:m5.RBV',     '9idcLAX:m58:c0:m5.DRBV',	 	'USAXS ax (mm)',		          'Y'),
       			('9idcLAX:m58:c0:m6.RBV',     '9idcLAX:m58:c0:m6.DRBV', 	 'USAXS ay (mm)',		          'Y'),
       			('9idcLAX:m58:c0:m7.RBV',     '9idcLAX:m58:c0:m7.DRBV',        'USAXS az (mm)',		       		  'Y'),
			('9idcLAX:USAXS:ARcenter',    '9idcLAX:USAXS:ARcenter',        'USAXS AR center',		          'Y')]

User_Info = 	[	('9idcLAX:RunCycle',          '9idcLAX:RunCycle',              'Run cycle',                             'Y'),
       			('9idcLAX:UserName',          '9idcLAX:Username',    	         'User name',		                  'Y'),
       			('9idcLAX:GUPNumber',         '9idcLAX:GUPNumber', 	         'GUP number',		                  'Y')]

Amplifiers = 	[	('9idcUSX:fem03:seq01:gain',  '9idcUSX:fem03:seq01:gain',      'I00 Gain',                              'Y'),
       			('9idcUSX:fem02:seq01:gain',  '9idcUSX:fem02:seq01:gain',      'I0 Gain',		                  'Y'),
       			('9idcLAX:m58:c1:m5.RBV',     '9idcLAX:m58:c1:m5.DRBV', 	 'I0 stage (mm)',	                  'Y')]

SD_stages = 	[	('9idcLAX:m58:c2:m1.RBV',     '9idcLAX:m58:c2:m1.DRBV',        'USAXS sx (mm)',                         'Y'),
       			('9idcLAX:m58:c0:m2.RBV',     '9idcLAX:m58:c0:m2.DRBV',	 	'USAXS sy (mm)',		          'Y'),
       			('9idcLAX:m58:c0:m3.RBV',     '9idcLAX:m58:c0:m3.DRBV', 	 'USAXS dx (mm)',		          'Y'),
       			('9idcLAX:m58:c0:m4.RBV',     '9idcLAX:m58:c0:m4.DRBV',        'USAXS dy (mm)',		       		  'Y')]

PinSAXS = 	[	('9idcLAX:mxv:c0:m1.RBV',     '9idcLAX:mxv:c0:m1.DRBV',        'USAXS pin_x (mm)',                      'Y'),
       			('9idcLAX:mxv:c0:m2.RBV',     '9idcLAX:mxv:c0:m2.DRBV', 	 'USAXS pin_z (mm)',		          'Y'),
       			('9idcLAX:mxv:c0:m8.RBV',     '9idcLAX:mxv:c0:m8.DRBV',        'USAXS pin_y (mm)',		       	  'Y')]

USAXS_Params = 	[	('9idcLAX:USAXS:CountTime',   		'9idcLAX:USAXS:CountTime',    			'USAXS Count Time',           	'Y'),
			('9idcLAX:USAXS:NumPoints',   		'9idcLAX:USAXS:NumPoints',    			'USAXS Num Points',             'Y'),
			('9idcLAX:USAXS:Finish',    		'9idcLAX:USAXS:Finish',    			'USAXS Q max',                 	'Y'),
			('9idcLAX:USAXS:StartOffset',     	'9idcLAX:USAXS:StartOffset',    		'USAXS Start Offset',          	'Y'),
			('9idcLAX:USAXS:Sample_Y_Step',  	'9idcLAX:USAXS:Sample_Y_Step',    		'USAXS Sample Y Step',         	'Y'),
			('9idcLAX:USAXS_Pin:ax_in',	   	'9idcLAX:USAXS_Pin:ax_in',   			'USAXS ax in',                	'Y'),
			('9idcLAX:USAXS_Pin:Pin_y_out',	   	'9idcLAX:USAXS_Pin:Pin_y_out',   	    	'USAXS pin_y out',             	'Y'),
			('9idcLAX:USAXS_Pin:Pin_z_out',	   	'9idcLAX:USAXS_Pin:Pin_z_out',   		'USAXS pin_z out',             	'Y'),
			('9idcLAX:USAXS_Pin:USAXS_hslit_ap',   	'9idcLAX:USAXS_Pin:USAXS_hslit_ap',   		 'USAXS hor slit',               'Y'),
       			('9idcLAX:USAXS_Pin:USAXS_vslit_ap',   	'9idcLAX:USAXS_Pin:USAXS_hslit_ap',   		 'USAXS vert slit',              'Y'),
       			('9idcLAX:USAXS_Pin:USAXS_hgslit_ap',   '9idcLAX:USAXS_Pin:USAXS_hgslit_ap',  		 'USAXS Guard vert slit',      	'Y'),
       			('9idcLAX:USAXS_Pin:USAXS_vgslit_ap',   '9idcLAX:USAXS_Pin:USAXS_vgslit_ap',   		'USAXS Guard vert slit',      	'Y')]

Pin_Params = 	[	('9idcLAX:WavelengthSpread',  	 	'9idcLAX:WavelengthSpread',    			'Wavelength Spread',           	'Y'),
			('9idcLAX:USAXS_Pin:BeamCenterX',	'9idcLAX:USAXS_Pin:BeamCenterX',    		'PinSAXS Beam Center X',        'Y'),
			('9idcLAX:USAXS_Pin:BeamCenterY',    	'9idcLAX:USAXS_Pin:BeamCenterY',    		'PinSAXS Beam Center Y',       	'Y'),
			('9idcLAX:USAXS_Pin:Distance',  	'9idcLAX:USAXS_Pin:Distance',    		'PinSAXS distance (mm)',      	'Y'),
			('9idcLAX:USAXS_Pin:PinPixSizeX',  	'9idcLAX:USAXS_Pin:PinPixSizeX',    		'PinSAXS pixels size X (mm)',  	'Y'),
			('9idcLAX:USAXS_Pin:PinPixSizeY',  	'9idcLAX:USAXS_Pin:PinPixSizeY',    		'PinSAXS pixels size Y (mm)',  	'Y'),
			('9idcLAX:USAXS_Pin:Exp_Al_Filter',  	'9idcLAX:USAXS_Pin:Exp_Al_Filter',    		'PinSAXS Exp Al Filter',  	'Y'),
			('9idcLAX:USAXS_Pin:Exp_Ti_Filter',  	'9idcLAX:USAXS_Pin:Exp_Ti_Filter',    		'PinSAXS Exp Ti Filter',  	'Y'),
			('9idcLAX:USAXS_Pin:directory',  	'9idcLAX:USAXS_Pin:directory',    		'PinSAXS Image bese directory', 'Y'),
			('9idcLAX:USAXS_Pin:ax_out',	   	'9idcLAX:USAXS_Pin:ax_out',   			'PinSAXS ax out',             	'Y'),
			('9idcLAX:USAXS_Pin:dx_out',	   	'9idcLAX:USAXS_Pin:dx_out',   			'PinSAXS dx out',             	'Y'),
			('9idcLAX:USAXS_Pin:Pin_y_in',	   	'9idcLAX:USAXS_Pin:Pin_y_in',   		'PinSAXS pin_y in',           	'Y'),
			('9idcLAX:USAXS_Pin:Pin_z_in',	   	'9idcLAX:USAXS_Pin:Pin_z_in',   		'PinSAXS pin_z in',             'Y'),
			('9idcLAX:USAXS_Pin:AcquireTime',   	'9idcLAX:USAXS_Pin:AcquireTime',   	 	'PinSAXS acquire time',         'Y'),
			('9idcLAX:USAXS_Pin:Pin_hslit_ap',   	'9idcLAX:USAXS_Pin:Pin_hslit_ap',   	 	'PinSAXS hor slit',             'Y'),
       			('9idcLAX:USAXS_Pin:Pin_vslit_ap',   	'9idcLAX:USAXS_Pin:Pin_hslit_ap',    		'PinSAXS vert slit',            'Y'),
       			('9idcLAX:USAXS_Pin:Pin_hgslit_ap',   	'9idcLAX:USAXS_Pin:Pin_hgslit_ap',    		'PinSAXS Guard vert slit',      'Y'),
       			('9idcLAX:USAXS_Pin:Pin_vgslit_ap',   	'9idcLAX:USAXS_Pin:Pin_vgslit_ap',    		'PinSAXS Guard vert slit',      'Y')]


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
#createCategory("ADC slits")
#numCheck(ADC_Slits)
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

os.system('elog -h s9elog.xray.aps.anl.gov -d elog -p 80 -l "9ID Operations" -u "usaxs" "mu8rubo!" -a "Author=USAXS" -a "Category=USAXS_operations" -a "Type=Configuration" -a "Subject=Instrument/PV Snapshot" -f /share1/Elog/ID_elog_data " "')
