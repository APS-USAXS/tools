#test5.py changed to a single line span
#! /usr/local/bin/python

import setup_PyEpics_uc2
from epics import PV
from epics import caget
import sys, epics, time, string, os

# Create global variables with lists of PVs for various groups of information 

#			PV name[0]		   PV name[1]			    Message[2]             Use?[3]
undulator = 	[	('15IDA:ID15_gap',     '15IDA:ID15_gap',	  'Undulator gap (mm)',	 	    'Y'),
	                ('15IDA:ID15_energy',  '15IDA:ID15_energy',       'Undulator energy (keV)',         'Y')]

HHL_Slits = 	[   	('15IDA:m17.RBV',     '15IDA:m17.DRBV',  	  '(m17) HHL-Hor-Slit-Up(mm)',       'Y'),
       			('15IDA:m18.RBV',     '15IDA:m18.DRBV',	          '(m18) HHL-Vert-Slit-Up(mm)',      'Y'),
       			('15IDA:m19.RBV',     '15IDA:m19.DRBV',	          '(m19) HHL-Hor-Slit-Dwr(mm)',      'Y'),
       			('15IDA:m20.RBV',     '15IDA:m20.DRBV',	          '(m20) HHL-Vert-Slit-Dwr(mm)',     'Y')]

Monochromator = [	('15IDA:m10.RBV',     '15IDA:m10.DRBV',           '(m10) Bragg-Angle(degrees)',      'Y'),
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
createCategory("Undulator")
numCheck(undulator)
createCategory("HHL Slits")
numCheck(HHL_Slits)
createCategory("Monochromator")
numCheck(Monochromator)
createCategory("ADC slits")
numCheck(ADC_Slits)
createCategory("OXFORD BPM (upstream)")
numCheck(bpm_up)
createCategory("OXFORD BPM (downstream)")
numCheck(bpm_down)
createCategory("Mirrors")
numCheck(Mirrors)
f.close()

#Run elog client to add to logbook. Have to add as an attachment. Table is messed up if it is sent as text.

os.system('elog -h 164.54.162.133 -p 8081 -l 15-ID-D -a Author=SYSTEM -a Type=Routine -a Subject="System snapshot" -f /share1/Elog/ID_elog_data " "')

os.system('elog -h 15id.xor.aps.anl.gov -d elog -l controls_discussion -a Author="Peter Beaucage" -a Type=Configuration -a Subject="Instrument/PV Snapshot" -f /share1/Elog/ID_elog_data " "')


