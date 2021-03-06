import serial, time
from parse import parse
import numpy as np, numpy.linalg as linalg

def parseOutput(a):
    sensor = a[0:2]

    #Here we convert the output of the fast track xyz measurements into milimeters.

    x = 10*float(a[5:11])
    y = 10*float(a[13:19])
    z = 10*float(a[21:27])

    q1 = float(a[27:34])
    q2 = float(a[34:41])
    q3 = float(a[41:48])
    q4 = float(a[48:56])
    return [x,y,z,q1,q2,q3,q4]

class Quaternion(object):
    def __init__(self,q0,q1,q2,q3):
        self.q0 = q0
        self.q1 = q1
        self.q2 = q2
        self.q3 = q3        

    def rotationMatrix(self):
        q0 = self.q0
        q1 = self.q1
        q2 = self.q2
        q3 = self.q3

        rotationMatrix = np.zeros((3,3))
        
        #First row
        rotationMatrix[0,0] = 1.0-(2.0*q2*q2)-(2.0*q3*q3)
        rotationMatrix[0,1] = 2.0*((q1*q2)+(q0*q3))
        rotationMatrix[0,2] = 2.0*((q1*q3)-(q0*q2))
        
        #Second row
        rotationMatrix[1,0] = 2.0*((q1*q2)-(q0*q3))
        rotationMatrix[1,1] = 1.0-(2.0*q1*q1)-(2.0*q3*q3)
        rotationMatrix[1,2] = 2.0*((q2*q3)+(q0*q1))
        
        #Third row
        rotationMatrix[2,0] = 2.0*((q1*q3)+(q0*q2))
        rotationMatrix[2,1] = 2.0*((q2*q3)-(q0*q1))
        rotationMatrix[2,2] = 1.0-(2.0*q1*q1)-(2.0*q2*q2)

        self.rotMat = rotationMatrix
        self.invRotMat = linalg.inv(self.rotMat)
        return rotationMatrix

    def rotateVector(self,vector):
        self.rotationMatrix()
        return np.dot(self.rotMat,vector)
    
    def normSquared(self):
        self.normSqr = (self.q0*self.q0)+(self.q1*self.q1)+(self.q2*self.q2)+(self.q3*self.q3) 
        return self.normSqr

    def invert(self):
        q0 = self.q0
        q1 = self.q1
        q2 = self.q2
        q3 = self.q3

        normSqr = self.normSquared()
        return Quaternion(q0/normSqr,-q1/normSqr,-q2/normSqr,-q3/normSqr)


class Fastrak(object):
    def __init__(self,logFile='fastrak.log',serialPort='/dev/ttyUSB0',fixedPoints=None, sensor=1):
        if serialPort == None:
            self.logFile = open(logFile,'r')
            self.mode = 'playBackLog'
            print 'No serial port specified. Running in playback mode'
        
        if serialPort != None:
            self.serialPortName = serialPort
            self.serial = serial.Serial(serialPort,115200,timeout=1)
            self.logFile = open(logFile,'w')
            self.mode = 'useRealDevice'

        self.fixedPoints = fixedPoints
        self.sensor = sensor
        self.sensorTxt = '%d'%(sensor,)

    def usingRealDevice(self):
        return self.mode== 'useRealDevice'

    def setup(self,reset=True):
        if self.usingRealDevice():
            self.stopContinuous()
            time.sleep(1.0)
            print 'Resetting the tracking system...'
            if reset == True:
                self.serial.write('\x19')
                time.sleep(15)
                print 'Waiting for the device to wake up...'
                while(1):
                    self.serial.write('\r')
                    a = self.serial.readline()
                    if a == '':
                        print '...'
                    else:
                        print 'alright! we\'re on the roll!!'
                        break

            self.stopContinuous()
            time.sleep(1.0)
            self.serial.flushInput()

            print 'Finding out which sensors are active...'
            cmd = 'l'+self.sensorTxt+'\r'
            self.serial.write(cmd)
            time.sleep(1.0)
            print self.serial.readline()

            print 'Turning off all sensors except the ones used...'
            for i in ['1','2','3','4']:
                if i != self.sensorTxt:
                    print 'self sensor',self.sensor
                    print 'Sensor %s..'%(i,)
                    cmd = 'l'+i+',0\r'
                    self.serial.write(cmd)
                    time.sleep(0.4)
            
            cmd = 'l'+self.sensorTxt+',1\r'
            self.serial.write(cmd)
            time.sleep(0.4)

            
            print 'Finding out which sensors are active...'
            cmd = 'l'+self.sensorTxt+'\r'
            self.serial.write(cmd)
            time.sleep(1.0)
            print self.serial.readline()
            
            print 'Finding out which hemisphere for the sensor...'
            cmd = 'H'+self.sensorTxt+'\r'
            self.serial.write(cmd)
            time.sleep(0.5)
            print self.serial.readline()
            
            print 'Setting top hemishpere for sensor..'
            cmd = 'H'+self.sensorTxt+',0,0,1\r'
            self.serial.write(cmd)
            time.sleep(0.5)

            cmd = 'H'+self.sensorTxt+'\r'
            self.serial.write(cmd)
            time.sleep(0.5)
            print self.serial.readline()
            
            cmd = 'O'+self.sensorTxt+',0,2,0,0,11,1\r'
            print 'Setting output to cartesian and quaternion..'
            self.serial.write(cmd)
            time.sleep(0.5)

            cmd = 'O'+self.sensorTxt+'\r'
            self.serial.write(cmd)
            time.sleep(0.5)
            print self.serial.readline()

            print 'Setting the output unit to centimeters..'
            self.serial.write('u\r')
            time.sleep(0.5)
            print self.serial.readline()


        if self.mode == 'playBackLog':
            #nothing to do
            pass

    def setContinuous(self):
        if self.usingRealDevice():
            self.serial.write('C')
            self.serial.flushOutput()

    def stopContinuous(self):
        if self.usingRealDevice():
            self.serial.write('c')
            self.serial.flushOutput()

    def readData(self):
        a = None
        if self.usingRealDevice():
            a = self.serial.readline()
            #print a
            self.logFile.write(a)
        else:
            a = self.logFile.readline()
            print a
            if a == 0:
                print 'End of log reached.. quitting...'
                sys.exit(0)

        try:
            v = parseOutput(a)
        except:
            print 'Error parsing\n'
            print a
            return None
        #print v
        #print a,l,v
        xyzRx = [v[0],v[1],v[2]]
        qRx = [v[3],v[4],v[5],v[6]]

        fixedPointPositions = []
        if self.fixedPoints is not None:
            xyzRxTxTx = np.transpose(np.array(xyzRx,ndmin=2))
            quat = Quaternion(*qRx)
            quatInv = quat.invert()
            for fp in self.fixedPoints:                
                xyzFpRxTx = quatInv.rotateVector(fp)
                xyzFpTxTx = xyzFpRxTx + xyzRxTxTx
                tmp = [xyzFpTxTx[k,0] for k in [0,1,2]]
                fixedPointPositions.append(tmp)
        retval = []
        retval.append(xyzRx)
        retval.append(qRx)
        for fPP in fixedPointPositions:
            retval.append(fPP)
        return retval

