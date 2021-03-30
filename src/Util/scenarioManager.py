from random import randint, shuffle, choice
import os.path
import math
import collections

import numpy

"""
import Slice
import readWritter
import TopologyManager"""


from . import Slice
from . import readWritter
from . import TopologyManager

from src import param


class Scenario(object):
    
    '''
    classdocs
    '''

    def __init__(self, topoName, topo, instanceName, listOfArrival, functions):
        self.topoName = topoName
        self.topo = topo
        self.instanceName = instanceName
        self.listOfArrival = listOfArrival  #A list : at each i there is a list of slices that contains the slices arriving at this time-steps
        self.iteratorArrival = 0            #Iterator used to know at witch timestep we are
        self.nbTimeStep = len(listOfArrival)
        
        for listSlices in listOfArrival:
            for slice in listSlices:
                slice.setRevenu(functions)
        
    def getNewSlices(self):
        if self.iteratorArrival == self.nbTimeStep:
            return None
        tmp = self.listOfArrival[self.iteratorArrival]
        self.iteratorArrival += 1
        return tmp
        

def readFunctions(path, addName = None):
    functions = {}
    fileToOpen = os.path.join(path, "instances")
    if addName == None:
        fileToOpen = os.path.join(fileToOpen, "function")
    else:
        fileToOpen = os.path.join(fileToOpen, "function{}".format(addName))
    with open(fileToOpen, "r") as f:
        for line in f :
            if(line[0] == "#"):
                continue
            tmp = line.replace("\n","")
            tmp = tmp.split(" ")
            conso = float(tmp[1])
            price = float(tmp[2])
            profit = float(tmp[3])
            functions[tmp[0]] = (conso, price, profit)
    f.close()
    return functions

def readSliceConfiguration(path, file):
    configuration = collections.OrderedDict()
    probaTotal = 0
    fileToOpen = os.path.join(path, "instances")
    fileToOpen = os.path.join(fileToOpen, file)
    #SFCType SliceType [FunctionsComposition] debit LatencyMax Destination(BS/Server/Service) probaOfDemands
    with open(fileToOpen, "r") as f:
        for line in f :
            if(line[0] == "#"):
                continue
            tmp = line.replace("\n","")
            tmp = tmp.split(" ")
            sfcType = tmp[0]
            sliceType = tmp[1]
            capacityDemand = float(tmp[3])
            latency = float(tmp[4])
            destinationType = tmp[5]
            nbDemand = float(tmp[6])
            
            tmp = tmp[2].replace("[","")
            tmp = tmp.replace("]","")
            functions = tmp.split(",")
            probaTotal += nbDemand
            configuration[sfcType] = [sliceType, functions, capacityDemand, latency, destinationType, probaTotal]
    f.close()
    return configuration

def readTopologySettings(path, file):
    configuration = collections.OrderedDict()
    probaTotal = 0
    fileToOpen = os.path.join(path, "instances")
    fileToOpen = os.path.join(fileToOpen, file)
    #SFCType SliceType [FunctionsComposition] debit LatencyMax Destination(BS/Server/Service) probaOfDemands
    with open(fileToOpen, "r") as f:
        for line in f :
            if(line[0] == "#"):
                continue
            tmp = line.replace("\n","")
            tmp = tmp.split(" = ")
            if tmp[0] == "capacityCoreLinks":
                capacityCoreLinks = float(tmp[1])
            elif tmp[0] == "capacityEdgeLinks":
                capacityEdgeLinks = float(tmp[1])
            elif tmp[0] == "capacityConnectivityLinks":
                capacityConnectivityLinks = float(tmp[1])
            elif tmp[0] == "capacityCoreDC":
                capacityCoreDC = float(tmp[1])
            elif tmp[0] == "capacityEdgeDC":
                capacityEdgeDC = float(tmp[1])
            elif tmp[0] == "latencyCoreLinks":
                latencyCoreLinks = float(tmp[1])
            elif tmp[0] == "latencyEdgeLinks":
                latencyEdgeLinks = float(tmp[1])
            elif tmp[0] == "latencyConnectivityLinks":
                latencyConnectivityLinks = float(tmp[1])

    f.close()

    return capacityCoreLinks, capacityEdgeLinks, capacityConnectivityLinks, capacityCoreDC, capacityEdgeDC, latencyCoreLinks, latencyEdgeLinks, latencyConnectivityLinks

    
#write all the sfc in the file "fileName" in the folder "map" in instances
def writeInstance(path, topoName, fileName, scenario):
    file_to_open = os.path.join(topoName, "expe")
    file_to_open = os.path.join(file_to_open, fileName)
    file_to_open = os.path.join("topology", file_to_open)
    file_to_open = os.path.join("instances", file_to_open)
    file_to_open = os.path.join(path, file_to_open)
    file = open(file_to_open+".txt", 'w')
    
    numTimeStep = 1
    listSlice = scenario.getNewSlices()
    while(not listSlice == None):
        file.write("({}\n".format(numTimeStep))
        for slice in listSlice:
            tmp = ""
            if not slice.dst == None:
                tmp = slice.dst
            file.write("    {}\n".format(str(slice)))
        file.write(")\n")
        listSlice = scenario.getNewSlices()
        numTimeStep += 1

    file.close()
    print("    Instance {}-{} created".format(topoName, fileName))

#Load all the slices in the file "fileName" in the folder "map" in instances
def loadInstance(path, topoName, fileName):
    file_to_open = os.path.join(topoName, "expe")
    file_to_open = os.path.join(file_to_open, fileName)
    file_to_open = os.path.join("topology", file_to_open)
    file_to_open = os.path.join("instances", file_to_open)
    file_to_open = os.path.join(path, file_to_open)
    listOfArrival, listOfSliceCurrentTime = [], []
    
    timeStep = 0
    with open(file_to_open+".txt") as f:
        for line in f :
            line = line.replace("\n", "")
            
            #TimeStep part
            if line[0] == "(":
                listOfSliceCurrentTime = []
            elif line[0] == ")":
                listOfArrival.append(listOfSliceCurrentTime)
                timeStep += 1
            #Slice part
            else :
                line = line.replace("    ", "")
                tmp = line.split(":")
                id = tmp[0]
                sliceType = tmp[1]
                bd = float(tmp[2])
                src = tmp[3]
                dst = tmp[4]
                if dst == '':
                    dst = None
                listFunctions = tmp[5].split(",")
                maxLatency = float(tmp[6])
                timeOfDeath = int(float(tmp[7]))
                sliceTmp = Slice.Slice(id,sliceType,bd,src,dst,listFunctions, maxLatency, timeOfDeath)
                sliceTmp.setDuration(timeStep)
                listOfSliceCurrentTime.append(sliceTmp)
    f.close()
    return listOfArrival

#Load all the sfc in the file "fileName" in the folder "map" in instances
def loadInstanceOld(path, map, fileName):
    file_to_open = os.path.join(map, "expe")
    file_to_open = os.path.join(file_to_open, fileName)
    file_to_open = os.path.join("topologyOld", file_to_open)
    file_to_open = os.path.join("instances", file_to_open)
    file_to_open = os.path.join(path, file_to_open)
    listOfArrival, listOfSliceCurrentTime = [], []
    timeStep = 0
    with open(file_to_open+".txt") as f:
        for line in f :
            line = line.replace("\n", "")
            if line[0] == "(":
                listOfSliceCurrentTime = []
            elif line[0] == ")":
                listOfArrival.append(listOfSliceCurrentTime)
                timeStep += 1
            else:
                line = line.replace("    ", "")
                tmp = line.split(":")
                id = tmp[0]
                tmp = tmp[1].split(" ")
                bd = int(float(tmp[0]))
                functions = tmp[2].split(",")
                maxLatency = float(tmp[3])
                timeOfDeath = int(float(tmp[4]))
                tmp = tmp[1].split(",")                
                sliceTmp = Slice.Slice(id,"eMBB",bd,tmp[0],tmp[1],functions, maxLatency, timeOfDeath)
                sliceTmp.setDuration(timeStep)
                listOfSliceCurrentTime.append(sliceTmp)
    f.close()
    return listOfArrival

def chooseSFC(distribSFC):
    
    listKey = list(distribSFC.keys())
    borneMax_distribSFC = distribSFC[listKey[len(distribSFC)-1]][5]
    currentSFCType = listKey[len(distribSFC)-1]
    numSFC = randint(1, borneMax_distribSFC)
    for s in distribSFC:
        if numSFC <= distribSFC[s][5]:
            currentSFCType = s
            break

    return distribSFC[currentSFCType][0], distribSFC[currentSFCType][1], distribSFC[currentSFCType][2], distribSFC[currentSFCType][3], distribSFC[currentSFCType][4]

    
#destination type can be : BS or Server or Service
#    BS : A Base Station
#    Server : A Core Node
#    Service : A function (Any DataCenter)
def chooseSrcDst(listBS, listNodesCore, destinationType):
    dst = None
    src = choice(listBS)
    
    if destinationType == "BS":
        dst = choice(listBS)
    elif destinationType == "Server":
        dst = choice(listNodesCore)
    elif destinationType == "Service":
        pass
    else:
        print("destinationType '{}' does not exist".format(destinationType))
    return src, dst



#Take the set of nodes and return the set of all to all demands
def createDemandsStatic(topology, distribSFC, nbdemands):

    listOfArrival = []
    listBS = []
    for i in range(len(topology.listBaseStation)):
        for bs in topology.listBaseStation[i]:
            listBS.append(bs)
    for iteratorTime in range(1, nbdemands+1):     #We don't iterate on the last one because it represents the end

        sliceType, listFunctions, bandwidth, latency, destinationType = chooseSFC(distribSFC)
        src, dst = chooseSrcDst(listBS, topology.listNodesCore, destinationType)
        timeOfDeath = iteratorTime + round(numpy.random.exponential(param.avgLifeTime - 15 )) + 15    #The slice last t least 10 minutes
        #timeOfDeath = iteratorTime + round(numpy.random(param.avgLifeTime - 15 )) + 15    #The slice last t least 10 minutes
        id = "{}_{}_{}".format(iteratorTime, 0, src)
        listOfArrival.append([Slice.Slice(id,sliceType,bandwidth,src,dst,listFunctions, latency, timeOfDeath)])
    
    return listOfArrival


#Take the set of nodes and return the set of all to all demands
def createDemandsDynamic(topology, distribSFC, avgNbSlicesPerMinute = 1):

    listOfArrival = []
    listBS = []
    for i in range(len(topology.listBaseStation)):
        for bs in topology.listBaseStation[i]:
            listBS.append(bs)
    iteratorTime = 1
    #For each different time period we add the arrival
    #    The first 150 are for initialization only (Initialization is made in D3 period)
    listPeriode = list(param.timePeriodeDynamic)    #We get all the period
    listPeriode.append(listPeriode[len(listPeriode)-1] + (1440 - listPeriode[len(listPeriode)-1] +param.startDynamic))    #We add a last period just to know when to stop
    for itPeriode in range(len(listPeriode)-1):     #We don't iterate on the last one because it represents the end
        periodeName = param.timePeriodeDynamic[listPeriode[itPeriode]]
        lengthOfPeriode = listPeriode[itPeriode+1]-listPeriode[itPeriode]
        listTmp = list(numpy.random.poisson(param.numberOfSlicesPerMinute*avgNbSlicesPerMinute*param.scale_factors[periodeName], lengthOfPeriode))
        
        for minute in range(len(listTmp)):
            nbDemands = listTmp[minute]
            listSlicesTmp = []
            
            for demand in range(nbDemands):
                sliceType, listFunctions, bandwidth, latency, destinationType = chooseSFC(distribSFC)
                src, dst = chooseSrcDst(listBS, topology.listNodesCore, destinationType)
                lifetime = round(numpy.random.exponential(param.avgLifeTime - 15 )) + 15    #The slice last at least 15 minutes
                timeOfDeath = iteratorTime + lifetime
                id = "{}_{}_{}".format(iteratorTime, demand, src)
                listSlicesTmp.append(Slice.Slice(id,sliceType,bandwidth,src,dst,listFunctions, latency, timeOfDeath))
            listOfArrival.append(listSlicesTmp)
            iteratorTime += 1
    
    return listOfArrival

#Take the set of nodes and return the set of all to all demands
def createMiniDemandsDynamic(topology, distribSFC, avgNbSlicesPerMinute = 1):

    listOfArrival = []
    listBS = []
    for i in range(len(topology.listBaseStation)):
        for bs in topology.listBaseStation[i]:
            listBS.append(bs)
    iteratorTime = 1
    #For each different time period we add the arrival
    #    The first 150 are for initialization only (Initialization is made in D3 period)
    listPeriode = list(param.timePeriodeDynamicMini)    #We get all the period
    listPeriode.append(listPeriode[len(listPeriode)-1] + (720 - listPeriode[len(listPeriode)-1] +param.startDynamic))    #We add a last period just to know when to stop
    for itPeriode in range(len(listPeriode)-1):     #We don't iterate on the last one because it represents the end
        periodeName = param.timePeriodeDynamicMini[listPeriode[itPeriode]]
        lengthOfPeriode = listPeriode[itPeriode+1]-listPeriode[itPeriode]
        listTmp = list(numpy.random.poisson(param.numberOfSlicesPerMinute*avgNbSlicesPerMinute*param.scale_factors[periodeName], lengthOfPeriode))
        
        for minute in range(len(listTmp)):
            nbDemands = listTmp[minute]
            listSlicesTmp = []
            
            for demand in range(nbDemands):
                sliceType, listFunctions, bandwidth, latency, destinationType = chooseSFC(distribSFC)
                src, dst = chooseSrcDst(listBS, topology.listNodesCore, destinationType)
                timeOfDeath = iteratorTime + round(numpy.random.exponential(param.avgLifeTime - 15 )) + 15    #The slice last at least 15 minutes
                id = "{}_{}_{}".format(iteratorTime, demand, src)
                listSlicesTmp.append(Slice.Slice(id,sliceType,bandwidth,src,dst,listFunctions, latency, timeOfDeath))
            listOfArrival.append(listSlicesTmp)
            iteratorTime += 1
    
    return listOfArrival


"""    **********************************************************
                        DEBUG
        ********************************************************** """
        
def listDensity(listOfArrival, nbMinutes = 1440, avgNbSlicesPerMinute = None):
    slicesPresent = []
    listToPlot = []
    numberOfSlice = 0
    for i in range(len(listOfArrival)):
        j = 0
        while j < len(slicesPresent):
            if slicesPresent[j].timeOfDeath == i:
                del(slicesPresent[j])
            else:
                j += 1
                
        for slice in listOfArrival[i]:
            slicesPresent.append(slice)
            
        if i > param.startDynamic:
            numberOfSlice += len(listOfArrival[i])
            
            
        listToPlot.append(len(slicesPresent))
        
    if avgNbSlicesPerMinute == None:
        print("There is {} slices to place in the scenario".format(numberOfSlice))
    else:
        print("There is {} slices to place in the scenario instead of {}".format(numberOfSlice, round(nbMinutes*avgNbSlicesPerMinute,0)))
        
    return listToPlot
        
        
        
import matplotlib.pyplot as plt
   
def plotDensity(listToPlot, avgNbSlicesPerMinute = 1, newTopo = True):
    if newTopo:
        param.startDynamic = param.startDynamicNew
        param.timePeriodeDynamic = param.timePeriodeDynamicNew
    else:
        param.startDynamic = param.startDynamicOld
        param.timePeriodeDynamic = param.timePeriodeDynamicOld
    
    plt.plot(listToPlot[param.startDynamic:], 'b')
    
    listToAchieve=[]
    
    listPeriode = list(param.timePeriodeDynamic)    #We get all the period
    listPeriode.append(listPeriode[len(listPeriode)-1] + (1400 - listPeriode[len(listPeriode)-1] +param.startDynamic))    #We add a last period just to know when to stop
    for itPeriode in range(1,len(listPeriode)-1):     #We don't iterate on the last one because it represents the end
        periodeName = param.timePeriodeDynamic[listPeriode[itPeriode]]
        lengthOfPeriode = listPeriode[itPeriode+1]-listPeriode[itPeriode]
        scale = param.scale_factors[periodeName]
        for i in range(lengthOfPeriode):
            listToAchieve.append(param.numberOfSlicesPerMinute*avgNbSlicesPerMinute*scale*param.avgLifeTime)

    
    plt.plot(listToAchieve, 'r')
    
    plt.show()
    
def plotDensityMini(listToPlot, avgNbSlicesPerMinute = 1):

    
    plt.plot(listToPlot[param.startDynamic:], 'b')
    
    listToAchieve=[]
    
    listPeriode = list(param.timePeriodeDynamicMini)    #We get all the period
    listPeriode.append(listPeriode[len(listPeriode)-1] + (720 - listPeriode[len(listPeriode)-1] +param.startDynamic))    #We add a last period just to know when to stop
    for itPeriode in range(1,len(listPeriode)-1):     #We don't iterate on the last one because it represents the end
        periodeName = param.timePeriodeDynamicMini[listPeriode[itPeriode]]
        lengthOfPeriode = listPeriode[itPeriode+1]-listPeriode[itPeriode]
        scale = param.scale_factors[periodeName]
        for i in range(lengthOfPeriode):
            listToAchieve.append(param.numberOfSlicesPerMinute*avgNbSlicesPerMinute*scale*param.avgLifeTime)

    
    plt.plot(listToAchieve, 'r')
    
    plt.show()
        
        


if __name__ == '__main__':
    
    path = "../.."
    
    
    topoName = "Topo_5_2_3_4_2_6_7_5_2"
    topoName = "Topo_5_2_3_5_2_6_7_8_2"
    topoName = "TopoTest4"
    topoName = "ta1"
    
    
    """distribFile = "4"
    functions = readFunctions(path)
    SliceConfiguration = readSliceConfiguration(path, "SliceDistrib_{}".format(distribFile))"""
    
    #avgNbSlicesPerMinute = 1
    avgNbSlicesPerMinute = 3
    nodes, links = TopologyManager.loadTopologyOld("../..", "ta1", ["F1"])
    topo = TopologyManager.Topology(nodes, links)
    
    
    instanceFile = "dynamic-DReal-TReal-Eval-{}".format(1)
    listOfArrival = loadInstanceOld("../..",topoName, instanceFile)
    plotDensity(listDensity(listOfArrival, 1440, avgNbSlicesPerMinute), avgNbSlicesPerMinute, False)
    
    
    exit()
    
    #topo = TopologyManager.loadTopology("../..", topoName)
    """
    for i in range(1,4):
        instanceName = "dynamic-D{}".format(distribFile)
        notOk = True
        while notOk:
            listOfArrival = createDemandsDynamic(topo, SliceConfiguration, avgNbSlicesPerMinute)
            plotDensity(listDensity(listOfArrival, 1440, avgNbSlicesPerMinute), avgNbSlicesPerMinute)
            print("y or n")
            input1 = input() 
            if input1 =="y":
                notOk = False
        
        scenario = Scenario(topoName, topo, instanceName, listOfArrival, functions)
        writeInstance(path, topoName,"{}-{}".format(instanceName,i), scenario)
    """
    
    
    for i in range(1,6):
        instanceName = "Train-D{}".format(distribFile)
        #listOfArrival = createMiniDemandsDynamic(topo, SliceConfiguration, avgNbSlicesPerMinute)
        notOk = True
        while notOk:
            listOfArrival = createDemandsDynamic(topo, SliceConfiguration, avgNbSlicesPerMinute)
            plotDensity(listDensity(listOfArrival, 1440, avgNbSlicesPerMinute), avgNbSlicesPerMinute)
            print("y or n")
            input1 = input() 
            if input1 =="y":
                notOk = False
        
        scenario = Scenario(topoName, topo, instanceName, listOfArrival, functions)
        writeInstance(path, topoName,"{}-{}".format(instanceName,i), scenario)
        
    
        