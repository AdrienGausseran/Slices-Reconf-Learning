import time
import os

import logging
from datetime import datetime

from allocation import allocILP
#from allocation import allocILPImprov as allocILP
#from allocation import allocILPMinMax as allocILP

from reconfiguration import reconfController


from Util import Util
from Util import scenarioManager
from Util import TopologyManager
from Util import readWritter
import AllocateurDynamic

import param

"""
def createlogLR(topoName, instanceName, beta, name):
    log_path = os.path.join("..", "logLR")
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    log_path = os.path.join(log_path, topoName)
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    log_path = os.path.join(log_path, instanceName)
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    log_path = os.path.join(log_path, "beta_{}".format(beta))
    if not os.path.exists(log_path):
        os.mkdir(log_path)
    log_path = os.path.join(log_path, "{}_%d%b%Y_%H_%M_%S.log".format(name))
    log_name = datetime.now().strftime("_%H_%M_%S_%d%b%Y")
    logger = logging.getLogger(log_name)
    log_path = datetime.now().strftime(log_path)

    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger"""


#Controls the progress of a dynamic allocation with regular make-beofre-break reconfigurations
class AllocateurDynamic(object):
    
    #Beta can be = 0, 1, "flexible"
    #reconf can be None, 0, 1    If None : no reconf, if 0 reconf with ILP pricing, if 1 reconf with LP pricing
    def __init__(self, name, topology, nbVnf, costMaxVnf, capaDC, capaLink, functions, allocInit, dictPath, slicesCurrentlyAllocated, objectifChooser, reconfigurationChooser, useMBB, nbSteps = 3, saveWhyReject = False):
        self.name = name
        self.topology = topology
        self.nbVnf = nbVnf
        self.costMaxVnf = costMaxVnf
        self.capaLink = capaLink
        self.capaCpu = capaDC
        self.functions = functions
        self.currentAlloc = allocInit.copy()
        self.currentPaths = dictPath.copy()
        self.listSlicesAccepted = []
        self.listSlicesRejected = []
        self.listSlicesCurrentlyAllocated = [s for s in slicesCurrentlyAllocated]
        self.objectifChooser = objectifChooser
        self.reconfigurationChooser = reconfigurationChooser
        self.nbSteps = nbSteps
        self.useMBB = useMBB
        self.beta = 1 * (self.capaLink/float(self.costMaxVnf))
        
        """
            All the variables for the print
        """
        self.profit = []
        self.accprofit = []
        
        #Acceptation Variables
        self.nbSlicesAccepted = []
        self.nbSlicesRejected = []
        self.nbSlicesAllocated = []
        self.bandwidthAccepted = []
        self.bandwidthRejected = []
        self.bandwidthAllocated = []
        self.revenuAccepted = []
        self.revenuRejected = []
        self.revenuAllocated = []
        
        #Cost Variables
        self.bandwidthUsed = []
        self.CpuUsed = []
        self.nbVnfsUsed = []
        self.CostVnfsUsed = []
        self.percLinksMoreThan80 = []
        self.percLinksLessThan20 = []
        self.percCpuMoreThan80 = []
        self.percCpuLessThan20 = []
        
        self.bandwidthUsedCore = []
        self.CpuUsedCore = []
        self.nbVnfsUsedCore = []
        self.percLinksMoreThan80Core = []
        self.percLinksLessThan20Core = []
        self.percCpuMoreThan80Core = []
        self.percCpuLessThan20Core = []
        
        self.bandwidthUsedEdge = []
        self.CpuUsedEdge = []
        self.nbVnfsUsedEdge = []
        self.percLinksMoreThan80Edge = []
        self.percLinksLessThan20Edge = []
        self.percCpuMoreThan80Edge = []
        self.percCpuLessThan20Edge = []
        
        #Latency Variables
        self.avgLatency = []
        self.avgLatencyeMBB = []
        self.avgLatencymMTC = []
        self.avgLatencyuRLLC = []
        
        #Reconfiguration Variables
        self.nbReconf = 0
        self.reconfDone = []
        self.timeReconf = []
        self.percSlicesReconf = []
        self.percImprovementReconf = []
        
        self.saveWhyReject = saveWhyReject
        if saveWhyReject:
            #statsReject = [ (step, periode, idSlice, SliceType why), ...]
            #    why = [becauseOfLinksCapa, becauseOfCpusCapa, becauseOfLatency, MultipleCauses]
            self.statsReject = []
        
        
    #Reconfiguration function
    #Launch the reconfiguration of the network by initializing a reconfController
    def reconfigure(self, timeStep):
        
        doReconf = False
        
        if self.useMBB:
            doReconf, res_Reconf, pathUsed_Reconf, lastObj, obj, timeTotal = self.reconfigurationChooser.doIReconfigureNowMBB(timeStep, len(self.listSlicesAccepted), len(self.listSlicesRejected), len(self.listSlicesCurrentlyAllocated), self.topology, self.functions, self.listSlicesCurrentlyAllocated, self.currentAlloc, self.currentPaths, self.nbSteps, self.beta, useLP = True, stableStop = param.stableStopGC, timeLimit = param.timeLimitReconf)
            
        else:
            doReconf, res_Reconf, pathUsed_Reconf, lastObj, obj, timeTotal = self.reconfigurationChooser.doIReconfigureNowBBM(timeStep, len(self.listSlicesAccepted), len(self.listSlicesRejected), len(self.listSlicesCurrentlyAllocated), self.topology, self.functions, self.listSlicesCurrentlyAllocated, self.currentAlloc, self.currentPaths, self.beta, timeLimit = param.timeLimitReconf, optimalNeeded = False)

 
        if doReconf:
            self.reconfDone.append(1)
            self.nbReconf += 1
            self.timeReconf.append(timeTotal)
            self.percSlicesReconf.append(Util.percentageSlicesReconf(self.listSlicesCurrentlyAllocated, self.currentAlloc, res_Reconf))
            self.percImprovementReconf.append(round((lastObj-obj)/float(max(1,lastObj))*100 ,2))
            
            self.currentAlloc = res_Reconf
            self.currentPaths = pathUsed_Reconf
            
        else:
            self.reconfDone.append(0)
            self.timeReconf.append(0)
            self.percSlicesReconf.append(0)
            self.percImprovementReconf.append(0)

            
        
    #Update Function : 
    #    Call the reconfiguration function
    #    Removes all the slices at the end of their life
    #    Updates all variables used to record the network status (to write into csv files
    def update(self, timeStep, remove = True):
        
        self.removeSlices(timeStep)
                
        #We MAJ the objective
        self.beta = self.objectifChooser.getObjectif(timeStep) * (self.capaLink/float(self.costMaxVnf))
                
        #We do the reconfiguration
        self.reconfigure(timeStep)
        
        #We save the data
        self.saveData()
        
        
    def removeSlices(self, timeStep):
        j = 0
        while j < len(self.listSlicesCurrentlyAllocated):
            if self.listSlicesCurrentlyAllocated[j].timeOfDeath == timeStep:
                del(self.currentAlloc[self.listSlicesCurrentlyAllocated[j].id])
                del(self.currentPaths[self.listSlicesCurrentlyAllocated[j].id])
                del(self.listSlicesCurrentlyAllocated[j])
            else:
                j += 1
        
    def saveData(self):
        
        #Acceptation Variables
        self.nbSlicesAccepted.append(len(self.listSlicesAccepted))
        self.nbSlicesRejected.append(len(self.listSlicesRejected))
        self.nbSlicesAllocated.append(len(self.listSlicesCurrentlyAllocated))
        tmp, tmp2 = 0, 0
        for s in self.listSlicesAccepted:
            tmp += s.bd*s.duration
            tmp2 += s.revenuPerTimeStep*s.duration
        self.bandwidthAccepted.append(tmp)
        self.revenuAccepted.append(tmp2)
        tmp, tmp2 = 0, 0
        for s in self.listSlicesRejected:
            tmp += s.bd*s.duration
            tmp2 += s.revenuPerTimeStep*s.duration
        self.bandwidthRejected.append(tmp)
        self.revenuRejected.append(tmp2)
        tmp, tmp2 = 0, 0
        for s in self.listSlicesCurrentlyAllocated:
            tmp += s.bd
            tmp2 += s.revenuPerTimeStep
        self.bandwidthAllocated.append(tmp)
        self.revenuAllocated.append(tmp2)
        
        
        
        bandwidthUsed, CpuUsed, nbVnfsUsed, CostVnfsUsed, percLinksMoreThan80, percLinksLessThan20, percCpuMoreThan80, percCpuLessThan20, bandwidthUsedCore, CpuUsedCore, nbVnfsUsedCore, percLinksMoreThan80Core, percLinksLessThan20Core, percCpuMoreThan80Core, percCpuLessThan20Core, bandwidthUsedEdge, CpuUsedEdge, nbVnfsUsedEdge, percLinksMoreThan80Edge, percLinksLessThan20Edge, percCpuMoreThan80Edge, percCpuLessThan20Edge = Util.utilisationTotalCoreEdge(self.topology, self.functions, self.listSlicesCurrentlyAllocated, self.currentAlloc, roundNumber = 8)
        
        """linksResidual, nodesResidual = Util.trueResidual(self.topology, self.functions, self.listSlicesCurrentlyAllocated, self.currentAlloc)
        
        for l in linksResidual:
            if linksResidual[l] < 0:
                print(" {}    {}".format(l, linksResidual[l]))
        for l in nodesResidual:
            if nodesResidual[l] < 0:
                print(" {}    {}".format(l, nodesResidual[l]))
            
        
        
        for s in self.listSlicesCurrentlyAllocated:
            print("{}    {}".format(s, self.currentAlloc[s.id]))
        print(self.beta)
        exit()"""
        

        
        
        self.profit.append(tmp2 - CostVnfsUsed)
        old = 0
        if len(self.accprofit)>0:
            old = self.accprofit[len(self.accprofit)-1]
        self.accprofit.append(old + tmp2 - CostVnfsUsed)
        
        #Cost Variables
        self.bandwidthUsed.append(bandwidthUsed)
        self.CpuUsed.append(CpuUsed)
        self.nbVnfsUsed.append(nbVnfsUsed)
        self.CostVnfsUsed.append(CostVnfsUsed)
        self.percLinksMoreThan80.append(percLinksMoreThan80)
        self.percLinksLessThan20.append(percLinksLessThan20)
        self.percCpuMoreThan80.append(percCpuMoreThan80)
        self.percCpuLessThan20.append(percCpuLessThan20)
        
        self.bandwidthUsedCore.append(bandwidthUsedCore)
        self.CpuUsedCore.append(CpuUsedCore)
        self.nbVnfsUsedCore.append(nbVnfsUsedCore)
        self.percLinksMoreThan80Core.append(percLinksMoreThan80Core)
        self.percLinksLessThan20Core.append(percLinksLessThan20Core)
        self.percCpuMoreThan80Core.append(percCpuMoreThan80Core)
        self.percCpuLessThan20Core.append(percCpuLessThan20Core)
        
        self.bandwidthUsedEdge.append(bandwidthUsedEdge)
        self.CpuUsedEdge.append(CpuUsedEdge)
        self.nbVnfsUsedEdge.append(nbVnfsUsedEdge)
        self.percLinksMoreThan80Edge.append(percLinksMoreThan80Edge)
        self.percLinksLessThan20Edge.append(percLinksLessThan20Edge)
        self.percCpuMoreThan80Edge.append(percCpuMoreThan80Edge)
        self.percCpuLessThan20Edge.append(percCpuLessThan20Edge)
        
        avgLatency, avgLatencyeMBB, avgLatencymMTC, avgLatencyuRLLC = Util.getAvgLatency(self.topology, self.listSlicesCurrentlyAllocated, self.currentAlloc)
        
        #Latency Variables
        self.avgLatency.append(avgLatency)
        self.avgLatencyeMBB.append(avgLatencyeMBB)
        self.avgLatencymMTC.append(avgLatencymMTC)
        self.avgLatencyuRLLC.append(avgLatencyuRLLC)
        
    
    def addSlice(self, newSlice, timeStep):
        
        linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, self.listSlicesCurrentlyAllocated, self.currentAlloc, roundNumber = 8)
        
        """if timeStep == 55 + param.startDynamic - 1:
            for l in linksUsage:
                print("{}    {}".format(l,linksUsage[l]))
                
            exit()"""
        
        """if timeStep < 420:
            
            for u in self.topology.listDCCore:
                if not u in nodeFunction:
                    nodeFunction[u] = {}
                for f in self.functions:
                    if not f in nodeFunction[u]:
                        nodeFunction[u][f] = 1"""
        
        allocPossible, dictPathTMP, allocInitTMP = allocILP.findAllocation(self.topology, nodesUsage, linksUsage, [newSlice], self.functions, nodeFunction, self.beta, timeLimit = param.timeLimitReconf, optimalNeeded = False)

        if allocPossible:
            self.listSlicesAccepted.append(newSlice)
            self.listSlicesCurrentlyAllocated.append(newSlice)
            self.currentPaths[newSlice.id] = dictPathTMP[newSlice.id]
            self.currentAlloc[newSlice.id] = allocInitTMP[newSlice.id]
        else:
            self.listSlicesRejected.append(newSlice)  
            
            
            if self.saveWhyReject:
                #We test first if it's because of links capacities
                allocPossibleLinks, dictPathTMP, allocInitTMP = allocILP.findAllocation(self.topology, nodesUsage, linksUsage, [newSlice], self.functions, nodeFunction, self.beta, timeLimit = param.timeLimitReconf, optimalNeeded = False, infinitLinksCapacity = True)
                #We test then if it's because of cpu capacities
                allocPossibleCpu, dictPathTMP, allocInitTMP = allocILP.findAllocation(self.topology, nodesUsage, linksUsage, [newSlice], self.functions, nodeFunction, self.beta, timeLimit = param.timeLimitReconf, optimalNeeded = False, infinitCpuCapacity = True)
                #We test then if it's because of latency
                allocPossibleLatency, dictPathTMP, allocInitTMP = allocILP.findAllocation(self.topology, nodesUsage, linksUsage, [newSlice], self.functions, nodeFunction, self.beta, timeLimit = param.timeLimitReconf, optimalNeeded = False, infinitLatency = True)
                why = (allocPossibleLinks, allocPossibleCpu, allocPossibleLatency, allocPossibleLinks+allocPossibleCpu+allocPossibleLatency == 0)
                periodeList = param.timePeriodeDynamic
                for i in periodeList:
                    if timeStep >= i:
                        periode = periodeList[i]
                self.statsReject.append([timeStep-param.startDynamic, periode, newSlice.id, newSlice.type, why])
                
                print("        REJECTION !!! {}".format(newSlice))
                print("            Links {}    Cpu {}    Latency {}".format(allocPossibleLinks, allocPossibleCpu, allocPossibleLatency))
                """if timeStep > 850 and timeStep < 1050:
                    self.showUsageStatic(timeStep)"""
            
        
    
        
    #The results are write in a folder (for the allocateur) in 2 files
    #    One file for the global results
    #    One file for the network status at each time step
    def writeResults(self, dossier):
        
        dossier = os.path.join(dossier, self.name)
        if not os.path.exists(dossier):
            os.makedirs(dossier)
            
            
        """
            Local Results
        """
        
        capaCpuCore = 0
        for u in self.topology.listDCCore:
            capaCpuCore += self.topology.nodes[u][0]
        capaCpuEdge = 0
        for u in self.topology.listDCEdge:
            capaCpuEdge += self.topology.nodes[u][0]
        capaLinksCore = 0
        for (u,v) in self.topology.listLinksCore:
            capaLinksCore += self.topology.links[(u,v)][0]
        capaLinksEdge = 0
        for (u,v) in self.topology.listLinksEdge:
            capaLinksEdge += self.topology.links[(u,v)][0]
            
        
        #We first create all the list that we need (percentage lists) and don't have
        perc_nbSlicesAccepted, perc_nbSlicesRejected, perc_bw_Accepted, perc_bw_Rejected, perc_revenu_Accepted, perc_revenu_Rejected, perc_cpuUsed, perc_linkUsed, perc_vnfUsed, perc_vnfCost = [], [], [], [], [], [], [], [], [], []
        perc_cpuUsedCore, perc_linkUsedCore, perc_vnfUsedCore, perc_cpuUsedEdge, perc_linkUsedEdge, perc_vnfUsedEdge = [], [], [], [], [], []
        for i in range(len(self.profit)):
            if(self.nbSlicesAccepted[i]+self.nbSlicesRejected[i] == 0):
                perc_nbSlicesAccepted.append(100)
                perc_nbSlicesRejected.append(0)
                perc_bw_Accepted.append(100)
                perc_bw_Rejected.append(0)
                perc_revenu_Accepted.append(100)
                perc_revenu_Rejected.append(0)
            else:
                perc_nbSlicesAccepted.append(round(self.nbSlicesAccepted[i]/max(1, float(self.nbSlicesAccepted[i]+self.nbSlicesRejected[i]))*100,2))
                perc_nbSlicesRejected.append(round(self.nbSlicesRejected[i]/max(1, float(self.nbSlicesAccepted[i]+self.nbSlicesRejected[i]))*100,2))
                perc_bw_Accepted.append(round(self.bandwidthAccepted[i]/max(1, float(self.bandwidthAccepted[i]+self.bandwidthRejected[i]))*100,2))
                perc_bw_Rejected.append(round(self.bandwidthRejected[i]/max(1, float(self.bandwidthAccepted[i]+self.bandwidthRejected[i]))*100,2))
                perc_revenu_Accepted.append(round(self.revenuAccepted[i]/max(1, float(self.revenuAccepted[i]+self.revenuRejected[i]))*100,2))
                perc_revenu_Rejected.append(round(self.revenuRejected[i]/max(1, float(self.revenuAccepted[i]+self.revenuRejected[i]))*100,2))
            perc_cpuUsed.append(round(self.CpuUsed[i]/max(1, float(self.capaCpu))*100,2))
            perc_linkUsed.append(round(self.bandwidthUsed[i]/max(1, float(self.capaLink))*100,2))
            perc_vnfUsed.append(round(self.nbVnfsUsed[i]/max(1, float(self.nbVnf))*100,2))
            perc_vnfCost.append(round(self.CostVnfsUsed[i]/max(1, float(self.costMaxVnf))*100,2))
            
            perc_cpuUsedCore.append(round(self.CpuUsedCore[i]/max(1, float(capaCpuCore))*100,2))
            perc_linkUsedCore.append(round(self.bandwidthUsedCore[i]/max(1, float(capaLinksCore))*100,2))
            perc_vnfUsedCore.append(round(self.nbVnfsUsedCore[i]/max(1, float(len(self.topology.listDCCore) * len(self.functions)))*100,2))
            perc_cpuUsedEdge.append(round(self.CpuUsedEdge[i]/max(1, float(capaCpuEdge))*100,2))
            perc_linkUsedEdge.append(round(self.bandwidthUsedEdge[i]/max(1, float(capaLinksEdge))*100,2))
            perc_vnfUsedEdge.append(round(self.nbVnfsUsedEdge[i]/max(1, float((len(self.topology.listAllDC)- len(self.topology.listDCCore)) * len(self.functions)))*100,2))
        
        fileName = os.path.join(dossier, "local.csv")
        listName = []
        listData = []
        
        listName.append("profit")
        listData.append(self.profit)
        listName.append("accprofit")
        listData.append(self.accprofit)
        
        listName.append("nbSlicesAllocated")
        listData.append(self.nbSlicesAllocated)
        listName.append("nbSlicesAccepted")
        listData.append(self.nbSlicesAccepted)
        listName.append("nbSlicesRejected")
        listData.append(self.nbSlicesRejected)
        listName.append("perc_nbSlicesAccepted")
        listData.append(perc_nbSlicesAccepted)
        listName.append("perc_nbSlicesRejected")
        listData.append(perc_nbSlicesRejected)

        listName.append("bw_Allocated")
        listData.append(self.bandwidthAllocated)
        listName.append("bw_Accepted")
        listData.append(self.bandwidthAccepted)
        listName.append("bw_Rejected")
        listData.append(self.bandwidthRejected)
        listName.append("perc_bw_Accepted")
        listData.append(perc_bw_Accepted)
        listName.append("perc_bw_Rejected")
        listData.append(perc_bw_Rejected)
        
        listName.append("revenu_Allocated")
        listData.append(self.revenuAllocated)
        listName.append("revenu_Accepted")
        listData.append(self.revenuAccepted)
        listName.append("revenu_Rejected")
        listData.append(self.revenuRejected)
        listName.append("perc_revenu_Accepted")
        listData.append(perc_revenu_Accepted)
        listName.append("perc_revenu_Rejected")
        listData.append(perc_revenu_Rejected)
        
        listName.append("cpuUsed")
        listData.append(self.CpuUsed)
        listName.append("linkUsed")
        listData.append(self.bandwidthUsed)
        listName.append("perc_cpuUsed")
        listData.append(perc_cpuUsed)
        listName.append("perc_linkUsed")
        listData.append(perc_linkUsed)
        listName.append("vnfUsed")
        listData.append(self.nbVnfsUsed)
        listName.append("perc_vnfUsed")
        listData.append(perc_vnfUsed)
        listName.append("vnfCost")
        listData.append(self.CostVnfsUsed)
        listName.append("perc_vnfCost")
        listData.append(perc_vnfCost)
        listName.append("perc_linksMoreThan80")
        listData.append(self.percLinksMoreThan80)
        listName.append("perc_linksLessThan20")
        listData.append(self.percLinksLessThan20)
        listName.append("perc_cpuMoreThan80")
        listData.append(self.percCpuMoreThan80)
        listName.append("perc_cpuLessThan20")
        listData.append(self.percCpuLessThan20)
        
        listName.append("cpuUsedCore")
        listData.append(self.CpuUsedCore)
        listName.append("linkUsedCore")
        listData.append(self.bandwidthUsedCore)
        listName.append("perc_cpuUsedCore")
        listData.append(perc_cpuUsedCore)
        listName.append("perc_linkUsedCore")
        listData.append(perc_linkUsedCore)
        listName.append("vnfUsedCore")
        listData.append(self.nbVnfsUsedCore)
        listName.append("perc_vnfUsedCore")
        listData.append(perc_vnfUsedCore)
        listName.append("perc_linksMoreThan80Core")
        listData.append(self.percLinksMoreThan80Core)
        listName.append("perc_linksLessThan20Core")
        listData.append(self.percLinksLessThan20Core)
        listName.append("perc_cpuMoreThan80Core")
        listData.append(self.percCpuMoreThan80Core)
        listName.append("perc_cpuLessThan20Core")
        listData.append(self.percCpuLessThan20Core)
        
        listName.append("cpuUsedEdge")
        listData.append(self.CpuUsedEdge)
        listName.append("linkUsedEdge")
        listData.append(self.bandwidthUsedEdge)
        listName.append("perc_cpuUsedEdge")
        listData.append(perc_cpuUsedEdge)
        listName.append("perc_linkUsedEdge")
        listData.append(perc_linkUsedEdge)
        listName.append("vnfUsedEdge")
        listData.append(self.nbVnfsUsedEdge)
        listName.append("perc_vnfUsedEdge")
        listData.append(perc_vnfUsedEdge)
        listName.append("perc_linksMoreThan80Edge")
        listData.append(self.percLinksMoreThan80Edge)
        listName.append("perc_linksLessThan20Edge")
        listData.append(self.percLinksLessThan20Edge)
        listName.append("perc_cpuMoreThan80Edge")
        listData.append(self.percCpuMoreThan80Edge)
        listName.append("perc_cpuLessThan20Edge")
        listData.append(self.percCpuLessThan20Edge)
        
        listName.append("avg_latency")
        listData.append(self.avgLatency)
        listName.append("avg_eMMB_latency")
        listData.append(self.avgLatencyeMBB)
        listName.append("avg_mMTC_latency")
        listData.append(self.avgLatencymMTC)
        listName.append("avg_uRLLC_latency")
        listData.append(self.avgLatencyuRLLC)
        
        listName.append("reconfDone")
        listData.append(self.reconfDone)
        listName.append("percSlicesReconf")
        listData.append(self.percSlicesReconf)
        listName.append("percImprovementReconf")
        listData.append(self.percImprovementReconf)
        listName.append("timeReconf")
        listData.append(self.timeReconf)

        
        
        readWritter.writeCSV(fileName, listName, listData)
        
        
        """
            Global Results
        """
               
        fileName = os.path.join(dossier, "global.csv")
        listName = []
        listData = []
        
        nbIt = len(self.profit)
        lastIt = nbIt-1
        
        listName.append("profit")
        listData.append(sum(self.profit))
        listName.append("avg_profit")
        listData.append(sum(self.profit)/nbIt)
        
        listName.append("nbSlices_Accepted")
        listData.append(len(self.listSlicesAccepted))
        listName.append("nbSlices_Rejected")
        listData.append(len(self.listSlicesRejected))
        listName.append("perc_nbSlices_Accepted")
        listData.append(perc_nbSlicesAccepted[lastIt])
        listName.append("perc_nbSlices_Rejected")
        listData.append(perc_nbSlicesRejected[lastIt])
        
        listName.append("bw_Accepted")
        listData.append(self.bandwidthAccepted[lastIt])
        listName.append("bw_Rejected")
        listData.append(self.bandwidthRejected[lastIt])
        listName.append("perc_bw_Accepted")
        listData.append(perc_bw_Accepted[lastIt])
        listName.append("perc_bw_Rejected")
        listData.append(perc_bw_Rejected[lastIt])
        
        listName.append("revenu_Accepted")
        listData.append(self.revenuAccepted[lastIt])
        listName.append("revenu_Rejected")
        listData.append(self.revenuRejected[lastIt])
        listName.append("perc_revenu_Accepted")
        listData.append(perc_revenu_Accepted[lastIt])
        listName.append("perc_revenu_Rejected")
        listData.append(perc_revenu_Rejected[lastIt])
        
        listName.append("avg_cpuUsed")
        listData.append(sum(self.CpuUsed)/nbIt)
        listName.append("avg_linkUsed")
        listData.append(sum(self.bandwidthUsed)/nbIt)
        listName.append("avg_perc_cpuUsed")
        listData.append(sum(perc_cpuUsed)/nbIt)
        listName.append("avg_perc_linkUsed")
        listData.append(sum(perc_linkUsed)/nbIt)
        listName.append("avg_vnfUsed")
        listData.append(sum(self.nbVnfsUsed)/nbIt)
        listName.append("avg_perc_vnfUsed")
        listData.append(sum(perc_vnfUsed)/nbIt)
        listName.append("avg_vnfCost")
        listData.append(sum(self.CostVnfsUsed)/nbIt)
        listName.append("avg_perc_vnfCost")
        listData.append(sum(perc_vnfCost)/nbIt)
        listName.append("avg_perc_linksMoreThan80")
        listData.append(sum(self.percLinksMoreThan80)/nbIt)
        listName.append("avg_perc_linksLessThan20")
        listData.append(sum(self.percLinksLessThan20)/nbIt)
        listName.append("avg_perc_cpuMoreThan80")
        listData.append(sum(self.percCpuMoreThan80)/nbIt)
        listName.append("avg_perc_cpuLessThan20")
        listData.append(sum(self.percCpuLessThan20)/nbIt)
        
        listName.append("avg_cpuUsedCore")
        listData.append(sum(self.CpuUsedCore)/nbIt)
        listName.append("avg_linkUsedCore")
        listData.append(sum(self.bandwidthUsedCore)/nbIt)
        listName.append("avg_perc_cpuUsedCore")
        listData.append(sum(perc_cpuUsedCore)/nbIt)
        listName.append("avg_perc_linkUsedCore")
        listData.append(sum(perc_linkUsedCore)/nbIt)
        listName.append("avg_vnfUsedCore")
        listData.append(sum(self.nbVnfsUsedCore)/nbIt)
        listName.append("avg_perc_vnfUsedCore")
        listData.append(sum(perc_vnfUsedCore)/nbIt)
        listName.append("avg_perc_linksMoreThan80Core")
        listData.append(sum(self.percLinksMoreThan80Core)/nbIt)
        listName.append("avg_perc_linksLessThan20Core")
        listData.append(sum(self.percLinksLessThan20Core)/nbIt)
        listName.append("avg_perc_cpuMoreThan80Core")
        listData.append(sum(self.percCpuMoreThan80Core)/nbIt)
        listName.append("avg_perc_cpuLessThan20Core")
        listData.append(sum(self.percCpuLessThan20Core)/nbIt)
        
        listName.append("avg_cpuUsedEdge")
        listData.append(sum(self.CpuUsedEdge)/nbIt)
        listName.append("avg_linkUsedEdge")
        listData.append(sum(self.bandwidthUsedEdge)/nbIt)
        listName.append("avg_perc_cpuUsedEdge")
        listData.append(sum(perc_cpuUsedEdge)/nbIt)
        listName.append("avg_perc_linkUsedEdge")
        listData.append(sum(perc_linkUsedEdge)/nbIt)
        listName.append("avg_vnfUsedEdge")
        listData.append(sum(self.nbVnfsUsedEdge)/nbIt)
        listName.append("avg_perc_vnfUsedEdge")
        listData.append(sum(perc_vnfUsedEdge)/nbIt)
        listName.append("avg_perc_linksMoreThan80Edge")
        listData.append(sum(self.percLinksMoreThan80Edge)/nbIt)
        listName.append("avg_perc_linksLessThan20Edge")
        listData.append(sum(self.percLinksLessThan20Edge)/nbIt)
        listName.append("avg_perc_cpuMoreThan80Edge")
        listData.append(sum(self.percCpuMoreThan80Edge)/nbIt)
        listName.append("avg_perc_cpuLessThan20Edge")
        listData.append(sum(self.percCpuLessThan20Edge)/nbIt)
        
        listName.append("avg_latency")
        listData.append(sum(self.avgLatency)/nbIt)
        listName.append("avg_eMMB_latency")
        listData.append(sum(self.avgLatencyeMBB)/nbIt)
        listName.append("avg_mMTC_latency")
        listData.append(sum(self.avgLatencyeMBB)/nbIt)
        listName.append("avg_uRLLC_latency")
        listData.append(sum(self.avgLatencyuRLLC)/nbIt)
        
        listName.append("nbReconf")
        listData.append(self.nbReconf)
        listName.append("avg_percSlicesReconf")
        listData.append(sum(self.percSlicesReconf)/float(max(1, self.nbReconf)))
        listName.append("avg_percImprovementReconf")
        listData.append(sum(self.percImprovementReconf)/float(max(1, self.nbReconf)))
        listName.append("avg_timeReconf")
        listData.append(sum(self.timeReconf)/float(max(1, self.nbReconf)))

        readWritter.writeCSV(fileName, listName, listData)
        
        if self.saveWhyReject:
            print("")
            print("    *********************************    ")
            print("    Rejection Statistics for {}".format(self.name))
            print("")
            nbLink, nbCpu, nbLatency, nbNone = 0, 0, 0, 0
            rejectByPeriode={"D1":[0,0,0,0], "D2":[0,0,0,0], "D3":[0,0,0,0], "D4":[0,0,0,0], "D5":[0,0,0,0]}
            nbRejectByPeriode={"D1":0, "D2":0, "D3":0, "D4":0, "D5":0}
            nbRejectByType={"eMBB":0, "mMTC":0, "uRLLC":0}
            for data in self.statsReject:
                why = data[4]
                link, cpu, latency, none = why[0], why[1], why[2], why[3]
                nbLink += link
                nbCpu += cpu
                nbLatency += latency
                nbNone += none
                rejectByPeriode[data[1]][0] += link
                rejectByPeriode[data[1]][1] += cpu
                rejectByPeriode[data[1]][2] += latency
                rejectByPeriode[data[1]][3] += none
                nbRejectByPeriode[data[1]] += 1
                nbRejectByType[data[3]] += 1
                print("        {}    {} : {} {} {} {}    {} {}".format(data[0], data[1], link, cpu, latency, none, data[2], data[3]))
            print("")
            print("    Number of rejection : {}    {}%Links {}%Cpu {}%Latency {}%None".format(len(self.statsReject), round(nbLink/float(max(1,len(self.statsReject)))*100,2), round(nbCpu/float(max(1,len(self.statsReject)))*100,2), round(nbLatency/float(max(1,len(self.statsReject)))*100,2), round(nbNone/float(max(1,len(self.statsReject)))*100,2)))
            for periode in nbRejectByPeriode:
                print("        Number of rejection for {} : {}    {}%Links {}%Cpu {}%Latency {}%None".format(periode, nbRejectByPeriode[periode], round(rejectByPeriode[periode][0]/float(max(1,nbRejectByPeriode[periode]))*100,2), round(rejectByPeriode[periode][1]/float(max(1,nbRejectByPeriode[periode]))*100,2), round(rejectByPeriode[periode][2]/float(max(1,nbRejectByPeriode[periode]))*100,2), round(rejectByPeriode[periode][3]/float(max(1,nbRejectByPeriode[periode]))*100,2)))
            for slicetype in nbRejectByType:
                print("        Number of rejection for {} : {} -> {}%".format(slicetype, nbRejectByType[slicetype], nbRejectByType[slicetype]/max(1, float(len(self.statsReject)))*100))
            print("")
        
        
    def printCurrentStatus(self):
        
        lastIt = len(self.profit)-1
        
        capaCpuCore = len(self.topology.listDCCore)*self.topology.capacityCoreDC
        capaCpuEdge = (len(self.topology.dictAllDC) - len(self.topology.listDCCore))*self.topology.capacityEdgeDC
        capaLinksCore = 2*self.topology.nbLinksCore*self.topology.capacityCoreLinks
        capaLinksEdge = 2*self.topology.nbLinksEdge*self.topology.capacityEdgeLinks
        perc_nbSlicesAccepted = round(self.nbSlicesAccepted[lastIt]/max(1, float(self.nbSlicesAccepted[lastIt]+self.nbSlicesRejected[lastIt]))*100,2)
        perc_nbSlicesRejected = round(self.nbSlicesRejected[lastIt]/max(1, float(self.nbSlicesAccepted[lastIt]+self.nbSlicesRejected[lastIt]))*100,2)
        perc_bw_Accepted = round(self.bandwidthAccepted[lastIt]/max(1, float(self.bandwidthAccepted[lastIt]+self.bandwidthRejected[lastIt]))*100,2)
        perc_bw_Rejected = round(self.bandwidthRejected[lastIt]/max(1, float(self.bandwidthAccepted[lastIt]+self.bandwidthRejected[lastIt]))*100,2)
        perc_revenu_Accepted = round(self.revenuAccepted[lastIt]/max(1, float(self.revenuAccepted[lastIt]+self.revenuRejected[lastIt]))*100,2)
        perc_revenu_Rejected = round(self.revenuRejected[lastIt]/max(1, float(self.revenuAccepted[lastIt]+self.revenuRejected[lastIt]))*100,2)
        perc_cpuUsed = round(self.CpuUsed[lastIt]/max(1, float(self.capaCpu))*100,2)
        perc_linkUsed = round(self.bandwidthUsed[lastIt]/max(1, float(self.capaLink))*100,2)
        perc_vnfUsed = round(self.nbVnfsUsed[lastIt]/max(1, float(self.nbVnf))*100,2)
        perc_vnfCost = round(self.CostVnfsUsed[lastIt]/max(1, float(self.costMaxVnf))*100,2)
        
        perc_cpuUsedCore = round(self.CpuUsedCore[lastIt]/max(1, float(capaCpuCore))*100,2)
        perc_linkUsedCore = round(self.bandwidthUsedCore[lastIt]/max(1, float(capaLinksCore))*100,2)
        perc_vnfUsedCore = round(self.nbVnfsUsedCore[lastIt]/max(1, float(len(self.topology.listDCCore) * len(self.functions)))*100,2)
        perc_cpuUsedEdge = round(self.CpuUsedEdge[lastIt]/max(1, float(capaCpuEdge))*100,2)
        perc_linkUsedEdge = round(self.bandwidthUsedEdge[lastIt]/max(1, float(capaLinksEdge))*100,2)
        perc_vnfUsedEdge = round(self.nbVnfsUsedEdge[lastIt]/max(1, float((len(self.topology.dictAllDC)- len(self.topology.listDCCore)) * len(self.functions)))*100,2)

        
        
        print("    **************************************    ")
        print("            {}".format(self.name))
        print("    **************************************    ")
        print("")
        
        print("    {}    {}".format("profit",self.profit[lastIt]))
        print("    {}    {}".format("nbSlicesAllocated",self.nbSlicesAllocated[lastIt]))
        print("    {}    {}".format("nbSlicesAccepted",self.nbSlicesAccepted[lastIt]))
        print("    {}    {}".format("nbSlicesRejected",self.nbSlicesRejected[lastIt]))
        print("    {}    {}".format("perc_nbSlicesAccepted",perc_nbSlicesAccepted))
        print("    {}    {}".format("perc_nbSlicesRejected",perc_nbSlicesRejected))
        print("    {}    {}".format("bw_Allocated",self.bandwidthAllocated[lastIt]))
        print("    {}    {}".format("bw_Accepted",self.bandwidthAccepted[lastIt]))
        print("    {}    {}".format("bw_Rejected",self.bandwidthRejected[lastIt]))
        print("    {}    {}".format("perc_bw_Accepted",perc_bw_Accepted))
        print("    {}    {}".format("perc_bw_Rejected",perc_bw_Rejected))
        print("    {}    {}".format("revenu_Allocated",self.revenuAllocated[lastIt]))
        print("    {}    {}".format("revenu_Accepted",self.revenuAccepted[lastIt]))
        print("    {}    {}".format("revenu_Rejected",self.revenuRejected[lastIt]))
        print("    {}    {}".format("perc_revenu_Accepted",perc_revenu_Accepted))
        print("    {}    {}".format("perc_revenu_Rejected",perc_revenu_Rejected))
        print("")
        print("    {}    {}".format("cpuUsed",self.CpuUsed[lastIt]))
        print("    {}    {}".format("linkUsed",self.bandwidthUsed[lastIt]))
        print("    {}    {}".format("perc_cpuUsed",perc_cpuUsed))
        print("    {}    {}".format("perc_linkUsed",perc_linkUsed))
        print("    {}    {}".format("vnfUsed",self.nbVnfsUsed[lastIt]))
        print("    {}    {}".format("perc_vnfUsed",perc_vnfUsed))
        print("")
        print("    {}    {}".format("perc_linksMoreThan80",self.percLinksMoreThan80[lastIt]))
        print("    {}    {}".format("perc_linksLessThan20",self.percLinksLessThan20[lastIt]))
        print("    {}    {}".format("perc_cpuMoreThan80",self.percCpuMoreThan80[lastIt]))
        print("    {}    {}".format("perc_cpuLessThan20",self.percCpuLessThan20[lastIt]))
        print("")
        print("    {}    {}".format("cpuUsedCore",self.CpuUsedCore[lastIt]))
        print("    {}    {}".format("linkUsedCore",self.bandwidthUsedCore[lastIt]))
        print("    {}    {}".format("perc_cpuUsedCore",perc_cpuUsedCore))
        print("    {}    {}".format("perc_linkUsedCore",perc_linkUsedCore))
        print("    {}    {}".format("vnfUsedCore",self.nbVnfsUsedCore[lastIt]))
        print("    {}    {}".format("perc_vnfUsedCore",perc_vnfUsedCore))
        print("")
        print("    {}    {}".format("perc_linksMoreThan80Core",self.percLinksMoreThan80Core[lastIt]))
        print("    {}    {}".format("perc_linksLessThan20Core",self.percLinksLessThan20Core[lastIt]))
        print("    {}    {}".format("perc_cpuMoreThan80Core",self.percCpuMoreThan80Core[lastIt]))
        print("    {}    {}".format("perc_cpuLessThan20Core",self.percCpuLessThan20Core[lastIt]))
        print("")
        print("    {}    {}".format("cpuUsedEdge",self.CpuUsedEdge[lastIt]))
        print("    {}    {}".format("linkUsedEdge",self.bandwidthUsedEdge[lastIt]))
        print("    {}    {}".format("perc_cpuUsedEdge",perc_cpuUsedEdge))
        print("    {}    {}".format("perc_linkUsedEdge",perc_linkUsedEdge))
        print("    {}    {}".format("vnfUsedEdge",self.nbVnfsUsedEdge[lastIt]))
        print("    {}    {}".format("perc_vnfUsedEdge",perc_vnfUsedEdge))
        print("")
        print("    {}    {}".format("perc_linksMoreThan80Edge",self.percLinksMoreThan80Edge[lastIt]))
        print("    {}    {}".format("perc_linksLessThan20Edge",self.percLinksLessThan20Edge[lastIt]))
        print("    {}    {}".format("perc_cpuMoreThan80Edge",self.percCpuMoreThan80Edge[lastIt]))
        print("    {}    {}".format("perc_cpuLessThan20Edge",self.percCpuLessThan20Edge[lastIt]))
        print("")
        print("    {}    {}".format("avg_latency",self.avgLatency[lastIt]))
        print("    {}    {}".format("avg_eMMB_latency",self.avgLatencyeMBB[lastIt]))
        print("    {}    {}".format("avg_mMTC_latency",self.avgLatencymMTC[lastIt]))
        print("    {}    {}".format("avg_uRLLC_latency",self.avgLatencyuRLLC[lastIt]))
        print("")
        """print("    Slices Accepted :")
        for s in self.listSlicesAccepted:
            print("        {}".format(s))"""
        print("    Slices Rejected :")
        for s in self.listSlicesRejected:
            print("        {}".format(s))
        """print("    Slices Allocated :")
        for s in self.listSlicesCurrentlyAllocated:
            print("        {}".format(s))"""
        
        
        
    def showUsageStatic(self, timeStep = None):
        linksUsage, nodesUsage, vnfUsed = Util.utilisationAndVnfUsed(self.functions, self.listSlicesCurrentlyAllocated, self.currentAlloc, roundNumber = 8)
        name = self.name
        if not timeStep == None:
            a = timeStep%60
            name = "{}-Step{}-{}H{}min".format(name, timeStep,(timeStep-a)//60 ,a)
        TopologyManager.showTopologyUsage(self.topology, linksUsage, nodesUsage, name)
        
    def showUsageDynamic(self, drawer, timeStep):
        linksUsage, nodesUsage, vnfUsed = Util.utilisationAndVnfUsed(self.functions, self.listSlicesCurrentlyAllocated, self.currentAlloc, roundNumber = 8)
        name = self.name
        if not timeStep == None:
            #timeStep - ((timeStep%60)*60)
            name = "{}-Step{}-{}H{}min".format(name, timeStep,timeStep%60,timeStep - ((timeStep%60)*60))
        drawer.draw(linksUsage, nodesUsage, name)
    

        
        


