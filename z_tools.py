#!/usr/bin/env python3
# coding: utf-8 -*-
#
# Author: zaraki673 & pipiche38
#
"""
    Module : z_tools.py

    Description: Zigate toolbox
"""
import binascii
import time
import datetime
import struct
import json

import Domoticz
import z_var
import z_output

def returnlen(taille , value) :
    while len(value)<taille:
        value="0"+value
    return str(value)


def Hex_Format(taille, value):
    value = hex(int(value))[2:]
    if len(value) > taille:
        return 'f' * taille
    while len(value)<taille:
        value="0"+value
    return str(value)

def IEEEExist(self, IEEE) :
    #check in ListOfDevices for an existing IEEE
    if IEEE :
        if IEEE in self.ListOfDevices and IEEE != '' :
            return True
        else:
            return False

def getSaddrfromIEEE(self, IEEE) :
    # Return Short Address if IEEE found.

    if IEEE != '' :
        for sAddr in self.ListOfDevices :
            if self.ListOfDevices[sAddr]['IEEE'] == IEEE :
                return sAddr

    Domoticz.Log("getSaddrfromIEEE no IEEE found " )

    return ''

def getEPforClusterType( self, NWKID, ClusterType ) :

    EPlist = []
    for EPout in self.ListOfDevices[NWKID]['Ep'] :
        if 'ClusterType' in self.ListOfDevices[NWKID]['Ep'][EPout]:
            for key in self.ListOfDevices[NWKID]['Ep'][EPout]['ClusterType'] :
                if self.ListOfDevices[NWKID]['Ep'][EPout]['ClusterType'][key].find(ClusterType) >= 0 :
                    EPlist.append(str(EPout))
                    Domoticz.Debug("We found " + ClusterType +  " in " + str(self.ListOfDevices[NWKID]['Ep'][EPout]['ClusterType']) )    
                    break
    return EPlist

def getClusterListforEP( self, NWKID, Ep ) :

    ClusterList = []
    if self.ListOfDevices[NWKID]['Ep'][Ep] :
        for cluster in self.ListOfDevices[NWKID]['Ep'][Ep] :
            if cluster != "ClusterType" :
                ClusterList.append(cluster)
    return ClusterList


def DeviceExist(self, newNWKID , IEEE = ''):

    #Validity check
    if newNWKID == '':
        return False

    found = 0

    #check in ListOfDevices
    if newNWKID in self.ListOfDevices:
        if 'Status' in self.ListOfDevices[newNWKID] :
            found = 1
            Domoticz.Debug("DeviceExist - Found in ListOfDevices with status = " +str(self.ListOfDevices[newNWKID]['Status']) )
            if not IEEE :
                return True

    #If given, let's check if the IEEE is already existing. In such we have a device communicating with a new Saddr
    if IEEE:
        for existingIEEEkey in self.IEEE2NWK :
            if existingIEEEkey == IEEE :
                # This device is already in Domoticz 
                existingNWKkey = self.IEEE2NWK[IEEE]

                if existingNWKkey == newNWKID :        #Check that I'm not myself
                    continue
                Domoticz.Debug("DeviceExist - given NWKID/IEEE = " + newNWKID + "/" + IEEE + " found as " +str(existingNWKkey) + " status " + str(self.ListOfDevices[existingNWKkey]['Status']) )

                # Make sure this device is valid 
                if self.ListOfDevices[existingNWKkey]['Status'] != 'inDB' and self.ListOfDevices[existingNWKkey]['Status'] != "Left" :
                    continue

                # Updating process by :
                # - mapping the information to the new newNWKID

                Domoticz.Debug("DeviceExist - update self.ListOfDevices[" + newNWKID + "] with " + str(existingIEEEkey) )
                self.ListOfDevices[newNWKID] = dict(self.ListOfDevices[existingNWKkey])

                Domoticz.Debug("DeviceExist - update self.IEEE2NWK[" + IEEE + "] from " +str(existingIEEEkey) + " to " + str(newNWKID) )
                self.IEEE2NWK[IEEE] = newNWKID

                Domoticz.Debug("DeviceExist - new device " +str(newNWKID) +" : " + str(self.ListOfDevices[newNWKID]) )
                Domoticz.Debug("DeviceExist - device " +str(IEEE) +" mapped to  " + str(newNWKID) )
                Domoticz.Debug("DeviceExist - old device " +str(existingNWKkey) +" : " + str(self.ListOfDevices[existingNWKkey]) )

                Domoticz.Status("NetworkID : " +str(newNWKID) + " is replacing " +str(existingNWKkey) + " and is attached to IEEE : " +str(IEEE) )

                # MostLikely exitsingKey is not needed any more
                removeNwkInList( self, existingNWKkey )    

                if self.ListOfDevices[newNWKID]['Status'] == 'Left' :
                    Domoticz.Log("DeviceExist - Update Status from 'Left' to 'inDB' for NetworkID : " +str(newNWKID) )
                    self.ListOfDevices[newNWKID]['Status'] = 'inDB'
                    self.ListOfDevices[newNWKID]['Hearbeat'] = 0
                found = 1

    if found == 1 :
        return True
    else :
        return False

def removeNwkInList( self, NWKID) :

    Domoticz.Debug("removeNwkInList - remove " +str(NWKID) + " => " +str( self.ListOfDevices[NWKID] ) ) 
    del self.ListOfDevices[NWKID]



def removeDeviceInList( self, Devices, IEEE, Unit ) :
    # Most likely call when a Device is removed from Domoticz
    # This is a tricky one, as you might have several Domoticz devices attached to this IoT and so you must remove only the corredpoing part.
    # Must seach in the NwkID dictionnary and remove only the corresponding device entry in the ClusterType.
    # In case there is no more ClusterType , then the full entry can be removed

    if IEEE in self.IEEE2NWK :
        key = self.IEEE2NWK[IEEE]
        ID = Devices[Unit].ID

        Domoticz.Log("removeDeviceInList - request to remove Device: %s with IEEE: %s " %(key, IEEE))

        if 'ClusterTye' in self.ListOfDevices[key]:               # We are in the old fasho V. 3.0.x Where ClusterType has been migrated from Domoticz
            if  str(ID) in self.ListOfDevices[key]['ClusterType']  :
                Domoticz.Log("removeDeviceInList - removing : "+str(ID) +" in "+str(self.ListOfDevices[key]['ClusterType']) )
                del self.ListOfDevices[key]['ClusterType'][ID] # Let's remove that entry
        else :
            for tmpEp in self.ListOfDevices[key]['Ep'] : 
                Domoticz.Log("removeDeviceInList - searching Ep " +str(tmpEp) )
                # Search this DeviceID in ClusterType
                if 'ClusterType' in self.ListOfDevices[key]['Ep'][tmpEp]:
                    Domoticz.Log("removeDeviceInList - searching ClusterType " +str(self.ListOfDevices[key]['Ep'][tmpEp]['ClusterType']) )
                    if str(ID) in self.ListOfDevices[key]['Ep'][tmpEp]['ClusterType'] :
                        Domoticz.Log("removeDeviceInList - removing : "+str(ID) +" in " +str(tmpEp) + " - " +str(self.ListOfDevices[key]['Ep'][tmpEp]['ClusterType']) )
                        del self.ListOfDevices[key]['Ep'][tmpEp]['ClusterType'][str(ID)]

        # Finaly let's see if there is any Devices left in this .
        emptyCT = 1
        if 'ClusterType' in self.ListOfDevices[key]: # Empty or Doesn't exist
            Domoticz.Log("removeDeviceInList - exitsing Global 'ClusterTpe'")
            if self.ListOfDevices[key]['ClusterType'] != {}:
                Domoticz.Log("removeDeviceInList - exitsing Global 'ClusterTpe' not empty")
                emptyCT = 0
        for tmpEp in self.ListOfDevices[key]['Ep'] : 
            if 'ClusterType' in self.ListOfDevices[key]['Ep'][tmpEp]:
                Domoticz.Log("removeDeviceInList - exitsing Ep 'ClusterTpe'")
                if self.ListOfDevices[key]['Ep'][tmpEp]['ClusterType'] != {}:
                    Domoticz.Log("removeDeviceInList - exitsing Ep 'ClusterTpe' not empty")
                    emptyCT = 0
        
        if emptyCT == 1 :     # There is still something in the ClusterType either Global or at Ep level
            Domoticz.Log("removeDeviceInList - removing ListOfDevices["+str(key)+"] : "+str(self.ListOfDevices[key]) )
            del self.ListOfDevices[key]

            Domoticz.Log("removeDeviceInList - removing IEEE2NWK ["+str(IEEE)+"] : "+str(self.IEEE2NWK[IEEE]) )
            del self.IEEE2NWK[IEEE]

            if self.pluginconf.allowRemoveZigateDevice == 1:
                Domoticz.Log("removeDeviceInList - removing Device in Zigate")
                z_output.removeZigateDevice( self, IEEE )


def initDeviceInList(self, Nwkid) :
    if Nwkid != '' :
        self.ListOfDevices[Nwkid]={}
        self.ListOfDevices[Nwkid]['Version']="3"
        self.ListOfDevices[Nwkid]['Status']="004d"
        self.ListOfDevices[Nwkid]['SQN']={}
        self.ListOfDevices[Nwkid]['Ep']={}
        self.ListOfDevices[Nwkid]['Heartbeat']="0"
        self.ListOfDevices[Nwkid]['RIA']="0"
        self.ListOfDevices[Nwkid]['RSSI']={}
        self.ListOfDevices[Nwkid]['Battery']={}
        self.ListOfDevices[Nwkid]['Model']={}
        self.ListOfDevices[Nwkid]['MacCapa']={}
        self.ListOfDevices[Nwkid]['IEEE']={}
        self.ListOfDevices[Nwkid]['Type']={}
        self.ListOfDevices[Nwkid]['ProfileID']={}
        self.ListOfDevices[Nwkid]['ZDeviceID']={}
        


def CheckDeviceList(self, key, val) :
    '''
        This function is call during DeviceList load
    '''
    import random

    Domoticz.Debug("CheckDeviceList - Address search : " + str(key))
    Domoticz.Debug("CheckDeviceList - with value : " + str(val))

    DeviceListVal=eval(val)
    if DeviceExist(self, key, DeviceListVal.get('IEEE','')) == False :
        initDeviceInList(self, key)
        self.ListOfDevices[key]['RIA']="10"
        if 'Ep' in DeviceListVal :
            self.ListOfDevices[key]['Ep']=DeviceListVal['Ep']
        if 'NbEp' in DeviceListVal :
            self.ListOfDevices[key]['NbEp']=DeviceListVal['NbEp']
        if 'Type' in DeviceListVal :
            self.ListOfDevices[key]['Type']=DeviceListVal['Type']
        if 'Model' in DeviceListVal :
            self.ListOfDevices[key]['Model']=DeviceListVal['Model']
        if 'MacCapa' in DeviceListVal :
            self.ListOfDevices[key]['MacCapa']=DeviceListVal['MacCapa']
        if 'IEEE' in DeviceListVal :
            self.ListOfDevices[key]['IEEE']=DeviceListVal['IEEE']
            Domoticz.Log("CheckDeviceList - DeviceID (IEEE)  = " + str(DeviceListVal['IEEE']) + " for NetworkID = " +str(key) )
            if  DeviceListVal['IEEE'] :
                IEEE = DeviceListVal['IEEE']
                self.IEEE2NWK[IEEE] = key
            else :
                Domoticz.Log("CheckDeviceList - IEEE = " + str(DeviceListVal['IEEE']) + " for NWKID = " +str(key) )
        if 'ProfileID' in DeviceListVal :
            self.ListOfDevices[key]['ProfileID']=DeviceListVal['ProfileID']
        if 'ZDeviceID' in DeviceListVal :
            self.ListOfDevices[key]['ZDeviceID']=DeviceListVal['ZDeviceID']
        if 'Manufacturer' in DeviceListVal :
            self.ListOfDevices[key]['Manufacturer']=DeviceListVal['Manufacturer']
        if 'DeviceType' in DeviceListVal :
            self.ListOfDevices[key]['DeviceType']=DeviceListVal['DeviceType']
        if 'LogicalType' in DeviceListVal :
            self.ListOfDevices[key]['LogicalType']=DeviceListVal['LogicalType']
        if 'PowerSource' in DeviceListVal :
            self.ListOfDevices[key]['PowerSource']=DeviceListVal['PowerSource']
        if 'ReceiveOnIdle' in DeviceListVal :
            self.ListOfDevices[key]['ReceiveOnIdle']=DeviceListVal['ReceiveOnIdle']
        if 'App Version' in DeviceListVal :
            self.ListOfDevices[key]['App Version']=DeviceListVal['App Version']
        if 'Stack Version' in DeviceListVal :
            self.ListOfDevices[key]['Stack Version']=DeviceListVal['Stack Version']
        if 'HW Version' in DeviceListVal :
            self.ListOfDevices[key]['HW Version']=DeviceListVal['HW Version']
        if 'Status' in DeviceListVal :
            self.ListOfDevices[key]['Status']=DeviceListVal['Status']
        if 'Battery' in DeviceListVal :
            self.ListOfDevices[key]['Battery']=DeviceListVal['Battery']
        if 'RSSI' in DeviceListVal :
            self.ListOfDevices[key]['RSSI']=DeviceListVal['RSSI']
        if 'SQN' in DeviceListVal :
            self.ListOfDevices[key]['SQN']=DeviceListVal['SQN']
        if 'ClusterType' in DeviceListVal :
            self.ListOfDevices[key]['ClusterType']=DeviceListVal['ClusterType']
        if 'RIA' in DeviceListVal :
            self.ListOfDevices[key]['RIA']=DeviceListVal['RIA']
        if 'Version' in DeviceListVal :
            self.ListOfDevices[key]['Version']=DeviceListVal['Version']
        if 'Stamp' in DeviceListVal :
            self.ListOfDevices[key]['Stamp']=DeviceListVal['Stamp']
        if 'ColorInfos' in DeviceListVal :
            self.ListOfDevices[key]['ColorInfos']=DeviceListVal['ColorInfos']
        if 'ConfigureReporting' in DeviceListVal :
            self.ListOfDevices[key]['ConfigureReporting']=DeviceListVal['ConfigureReporting']
        if 'ReadAttributes' in DeviceListVal :
            self.ListOfDevices[key]['ReadAttributes']=DeviceListVal['ReadAttributes']

        # We will initialize Hearbeat with a random value between 0 to 12 in order to distribute the load when triggering action based on the Hearbeat value
        # 12 is equivalent to 12 Heartbeat cycle ==> 2 minutes
        self.ListOfDevices[key]['Heartbeat']=random.randint(0, 12)


def timeStamped( self, key, Type ):
    if key in self.ListOfDevices:
        if 'Stamp' not in self.ListOfDevices[key]:
            self.ListOfDevices[key]['Stamp'] = {}
            self.ListOfDevices[key]['Stamp']['Time'] = {}
            self.ListOfDevices[key]['Stamp']['MsgType'] = {}
        self.ListOfDevices[key]['Stamp']['Time'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
        self.ListOfDevices[key]['Stamp']['MsgType'] = "%4d" %(Type)

def updSQN( self, key, newSQN) :

    try:
        if not self.ListOfDevices[key] :
            # Seems that the structutre is not yet initialized
            return
    except:
        return

    if newSQN == '' or newSQN is None:
            return

    # For now, we are simply updating the SQN. When ready we will be able to implement a cross-check in SQN sequence
    Domoticz.Debug("Device : " + key + " MacCapa : " + self.ListOfDevices[key]['MacCapa'] + " updating SQN to " + str(newSQN) )

    if newSQN == '' or newSQN is None or newSQN == {}:
        return

    if self.ListOfDevices[key]['MacCapa'] != '8e' :         # So far we have a good understanding on how SQN is managed for battery powered devices
        if 'SQN' in self.ListOfDevices[key]:
            oldSQN = self.ListOfDevices[key]['SQN']
            if oldSQN == '' or oldSQN is None or oldSQN == {} :
                oldSQN='00'
        else :
            oldSQN='00'

        try:
            if int(oldSQN,16) != int(newSQN,16) :
                Domoticz.Debug("updSQN - Device : " + key + " updating SQN to " + str(newSQN) )
                self.ListOfDevices[key]['SQN'] = newSQN
                if ( int(oldSQN,16)+1 != int(newSQN,16) ) and newSQN != "00" :
                    Domoticz.Log("Out of sequence for Device: " + str(key) + " SQN move from " +str(oldSQN) + " to " 
                                    + str(newSQN) + " gap of : " + str(int(newSQN,16) - int(oldSQN,16)))
        except:
            Domoticz.Log("updSQN - Device:  %s oldSQN: %s newSQN: %s" %(key, oldSQN, newSQN))
            return
    else :
        self.ListOfDevices[key]['SQN'] = {}


#### Those functions will be use with the new DeviceConf structutre

def getTypebyCluster( self, Cluster ) :
    clustersType = { '0405' : 'Humi',
                    '0406' : 'Motion',
                    '0400' : 'Lux',
                    '0403' : 'Baro',
                    '0402' : 'Temp',
                    '0006' : 'Switch',
                    '0500' : 'Door',
                    '0012' : 'XCube',
                    '000c' : 'XCube',
                    '0008' : 'LvlControl',
                    '0300' : 'ColorControl'
            }

    if Cluster == '' or Cluster is None :
        return ''
    if Cluster in clustersType :
        return clustersType[Cluster]
    else :
        return ''

def getListofClusterbyModel( self, Model , InOut ) :
    """
    Provide the list of clusters attached to Ep In
    """
    listofCluster = list()
    if InOut == '' or InOut is None :
        return listofCluster
    if InOut != 'Epin' and InOut != 'Epout' :
        Domoticz.Error( "getListofClusterbyModel - Argument error : " +Model + " " +InOut )
        return ''

    if Model in self.DeviceConf :
        if InOut in self.DeviceConf[Model]:
            for ep in self.DeviceConf[Model][InOut] :
                seen = ''
                for cluster in sorted(self.DeviceConf[Model][InOut][ep]) :
                    if cluster == 'Type' or  cluster == seen :
                        continue
                    listofCluster.append( cluster )
                    seen = cluster
    return listofCluster


def getListofInClusterbyModel( self, Model ) :
    return getListofClusterbyModel( self, Model, 'Epin' )

def getListofOutClusterbyModel( self, Model ) :
    return getListofClusterbyModel( self, Model, 'Epout' )

    
def getListofTypebyModel( self, Model ) :
    """
    Provide a list of Tuple ( Ep, Type ) for a given Model name if found. Else return an empty list
        Type is provided as a list of Type already.
    """
    EpType = list()
    if Model in self.DeviceConf :
        for ep in self.DeviceConf[Model]['Epin'] :
            if 'Type' in self.DeviceConf[Model]['Epin'][ep]:
                EpinType = ( ep, getListofType( self.DeviceConf[Model]['Epin'][ep]['Type']) )
                EpType.append(EpinType)
    return EpType
    
def getModelbyZDeviceIDProfileID( self, ZDeviceID, ProfileID):
    """
    Provide a Model for a given ZdeviceID, ProfileID
    """
    for model in self.DeviceConf :
        if self.DeviceConf[model]['ProfileID'] == ProfileID and self.DeviceConf[model]['ZDeviceID'] == ZDeviceID :
            return model
    return ''


def getListofType( self, Type ) :
    """
    For a given DeviceConf Type "Plug/Power/Meters" return a list of Type [ 'Plug', 'Power', 'Meters' ]
    """

    if Type == '' or Type is None :
        return ''
    retList = list()
    retList= Type.split("/")
    return retList

def hex_to_rgb(value):
    """Return (red, green, blue) for the color given as #rrggbb."""
    value = value.lstrip('#')
    lv = len(value)
    return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

def hex_to_xy(h):
    ''' convert hex color to xy tuple '''
    return rgb_to_xy(hex_to_rgb(h))

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def rgb_to_xy(rgb):
    ''' convert rgb tuple to xy tuple '''
    red, green, blue = rgb
    r = ((red + 0.055) / (1.0 + 0.055))**2.4 if (red > 0.04045) else (red / 12.92)
    g = ((green + 0.055) / (1.0 + 0.055))**2.4 if (green > 0.04045) else (green / 12.92)
    b = ((blue + 0.055) / (1.0 + 0.055))**2.4 if (blue > 0.04045) else (blue / 12.92)
    X = r * 0.664511 + g * 0.154324 + b * 0.162028
    Y = r * 0.283881 + g * 0.668433 + b * 0.047685
    Z = r * 0.000088 + g * 0.072310 + b * 0.986039
    cx = 0
    cy = 0
    if (X + Y + Z) != 0:
        cx = X / (X + Y + Z)
        cy = Y / (X + Y + Z)
    return (cx, cy)

def rgb_to_hsl(rgb):
    ''' convert rgb tuple to hls tuple '''
    r, g, b = rgb
    r = float(r/255)
    g = float(g/255)
    b = float(b/255)
    high = max(r, g, b)
    low = min(r, g, b)
    h, s, l = ((high + low) / 2,)*3

    if high == low:
        h = 0.0
        s = 0.0
    else:
        d = high - low
        s = d / (2 - high - low) if l > 0.5 else d / (high + low)
        h = {
            r: (g - b) / d + (6 if g < b else 0),
            g: (b - r) / d + 2,
            b: (r - g) / d + 4,
        }[high]
        h /= 6

    return h, s, l
