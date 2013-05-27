import serial, sys, datetime, time, re, threading

typedict = {
    'unread':'REC UNREAD',
    'read' : 'REC READ',
    'all' : 'ALL'
}

balanceFile = 'balance'
msgLogFile = 'msgLog'
initialBalance = 0.0

grm_port = '/dev/ttyUSB0'
gsm_port = '/dev/ttyUSB1'

pesaToSeconds = 20

timerObj = None

def turnSwitch(port=grm_port,key='f'):
    port = serial.Serial(port, 57600, timeout=5)
    port.flushInput()
    port.flushOutput()
    port.write(key)

def switchOn(port=grm_port):
    print 'Turning power on!\n'
    turnSwitch(port=port,key='n')

def switchOff(port=grm_port):
    print 'Turning power off!\n'
    turnSwitch(port=port,key='f')

def readsms(port,a):
    smslist = []
    port = serial.Serial(port, 115200, timeout=5)
    port.flushInput()
    port.flushOutput()
    port.write('AT\r\n')
    print 1,port.readline()
    print 2,port.readline()
    port.write('AT+CMGF=1\r\n')
    print 1,port.readline()
    print 2,port.readline()
    port.flushOutput()
    port.flushInput()
    port.write('AT+CMGL="%s"\r\n'%(typedict[a]))  #get all messages 
    inside_cmgl_output = False
    while(1):
        line = port.readline()
        print 'debug:',line
        if line.startswith('BOOT'):
            print 'ignoring crap'
            break
        if line.startswith('MODE'):
            print 'ignoreing crap'
            break
        if line.startswith('^BOOT'):
            print 'ignoring crap'
            break
        if line.startswith('^MODE'):
            print 'ignoreing crap'
            break

        if line.startswith('AT+CMGL='):
            inside_cmgl_output = True
            continue
        if line.startswith('+CMGL'):
            info = line.split(',')
            index = info[0].split(':')[1]
            customer = info[2]
            date = info[5]
            time = info[4]
            msg = port.readline()
            print 'message#%s from %s date %s time %s %s'     \
                %(index,customer,date,time,msg)
            a = (index,customer,date,time,msg)
            smslist.append(a)
            gotmsg = True
        if line.startswith('OK'):
            break
    return smslist


def parseSMSforMPESA(a):
    msgTxt = a[4]
    pp = re.compile('received Ksh[0-9]+\.[0-9][0-9] from')
    qq = re.compile('[0-9]+\.[0-9][0-9]')
    a = pp.search(msgTxt)
    if a is not None:
        b = a.group(0)
        c = qq.search(b)
        if c is not None:
            return float(c.group(0))
    return None


def goSMS(port=gsm_port,msgclass='unread'):
    switchOff();
    try:
        with open(balanceFile,'r'):
            balFile = open(balanceFile,'r')
            balText = balFile.readline()
            balFile.close()
            initialBalance = float(balText)
            switchOn();
            timerObj = threading.Timer((initialBalance*pesaToSeconds),switchOff)
            timerObj.start()
    except IOError:
        print 'Balance file not found, initializing with 0.00'
        bFil = open(balanceFile,'w')
        bFil.write('%f\n'%(0.0,))
        bFil.close()
        switchOff();
        timerObj = threading.Timer((0.0*pesaToSeconds),switchOff)
        timerObj.start()

    msgLogFil = open(msgLogFile,'a')

    while(1):
        a = readsms(port,msgclass)
        for i in a:
            msgLogFil.write('\n')
            msgLogFil.write(i.__str__())
            msgLogFil.write('\n')

            newTransfer = parseSMSforMPESA(i)
            if newTransfer is not None:
                print '\nNew MPESA Credit Received! %f\n'%(newTransfer,)
                balFile = open(balanceFile,'r')
                balText = balFile.readline()
                balFile.close()
                oldBalance = float(balText)
                print 'Old Balance %f\n'%(oldBalance,)
                newBalance = oldBalance + newTransfer
                print 'New Balance %f\n'%(newBalance,)
                balFile = open(balanceFile,'w')
                balFile.write('%f\n'%(newBalance))
                timerObj.cancel()
                timerObj = threading.Timer((newBalance*pesaToSeconds))
                switchOn();
                timerObj.start()
        time.sleep(1)

