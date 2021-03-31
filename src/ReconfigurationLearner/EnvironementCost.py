import copy
from tf_agents.environments import py_environment
from tf_agents.specs import array_spec
from tf_agents.trajectories import time_step as ts

import numpy as np
import os
import csv

from Util import Util
from Util import scenarioManager
from Util import TopologyManager
from Util import readWritter
from Util import DynamicTopologyDrawer

from allocation import allocILP
from reconfiguration import reconfController
from Chooser import ObjectifChooser

import AllocateurDynamic
import initializeNetworkDynamic

import param

class ReconfigurationEnvironement(py_environment.PyEnvironment):


    def __init__(self, realEnv, newTopo, topoName, SliceDistrib, TopologySettings, listInstanceFiles, stateVersion, rewardVersion, nbStepsReconf = 3, ratioPriceSeuilReconf = 8, betaInit = 1, numberOfStepsByState = 1, numberOfStepsForCost = 1, evaluation = False, dossierToSave = None):
        
        self.numberOfStepsByState = numberOfStepsByState
        self.numberOfStepsForCost = numberOfStepsForCost
        self.stateVersion = stateVersion
        self.rewardVersion = rewardVersion
        self.evaluation = evaluation
        self.dossierToSave = dossierToSave
        self.newTopo = newTopo
        
        
        self._action_spec = array_spec.BoundedArraySpec(shape=(), dtype=np.int32, minimum=0, maximum=1, name='action')
            
        #Version 1
        if self.stateVersion == 1:
            self._observation_spec = array_spec.ArraySpec(shape=(1,6), dtype=np.float32 , name='observation')
            self._state = [0, 0, 0, 0, 0, 0]
            
        #Version 2
        elif self.stateVersion == 2 or self.stateVersion == 4 :
            self._observation_spec = array_spec.ArraySpec(shape=(1,4), dtype=np.float32, name='observation')
            self._state = [0, 0, 0, 0]
            
        #Version 3
        elif self.stateVersion == 3:
            self._observation_spec = array_spec.ArraySpec(shape=(1,2), dtype=np.float32, name='observation')
            self._state = [0, 0]
        #Version 5
        elif self.stateVersion == 5 :
            self._observation_spec = array_spec.ArraySpec(shape=(1,5), dtype=np.float32, name='observation')
            self._state = [0, 0, 0, 0, 0]
        #Version 6
        elif self.stateVersion == 6 :
            self._observation_spec = array_spec.ArraySpec(shape=(1,3), dtype=np.float32, name='observation')
            self._state = [0, 0, 0]
        else :
            print("Bad version {}".format(stateVersion))
            exit()
            
        
        if not realEnv:
            return
        
        
        self.topoName = topoName

        self.nbSteps = nbStepsReconf
        self.reconfsDone = []
        
        self.listInstanceFiles = listInstanceFiles
        self.listInstanceAlreadyTrained = []
        self.evaluation = evaluation
        
        self.TopologySettings = TopologySettings
        self.SliceDistrib = SliceDistrib
        self.timeStep = 0
        
        self.ratioPriceSeuilReconf = ratioPriceSeuilReconf
        self.costReconf = 0
       
        self.betaInit = betaInit
        self.beta = self.betaInit
       
        if self.newTopo:
            self.functions = scenarioManager.readFunctions("..","2")
            param.startDynamic = param.startDynamicNew
            param.timePeriodeDynamic = param.timePeriodeDynamicNew
            self.topology = TopologyManager.loadTopologyNew("..", topoName, self.functions)
            capacityCoreLinks, capacityEdgeLinks, capacityConnectivityLinks, capacityCoreDC, capacityEdgeDC, latencyCoreLinks, latencyEdgeLinks, latencyConnectivityLinks = scenarioManager.readTopologySettings("..", "TopologySettings_{}".format(TopologySettings))
            self.topology.setSettings(capacityCoreLinks, capacityEdgeLinks, capacityConnectivityLinks, capacityCoreDC, capacityEdgeDC, latencyCoreLinks, latencyEdgeLinks, latencyConnectivityLinks)
            self.nbVnf = (len(self.topology.listDCCore) + len(self.topology.listDCEdge)) * len(self.functions)
            
            capaLink = self.topology.linksCapacity
        
            self.costMaxVnf = 0
            for f in self.functions:
                self.costMaxVnf +=  self.functions[f][1]
            self.costMaxVnf = self.costMaxVnf * (len(self.topology.listDCCore) + len(self.topology.listDCEdge))
            
            
            self.ratioBeta = (capaLink/float(self.costMaxVnf))
            
        else:
            self.functions = scenarioManager.readFunctions("..")
            param.startDynamic = param.startDynamicOld
            param.timePeriodeDynamic = param.timePeriodeDynamicOld
        
        
        self._episode_ended = False
        self.gammaDiscount = 0.9
        
        
    def setGammaDiscount(self, gamma):
        self.gammaDiscount = gamma
        
    def setSeuilReconf(self, seuilReconf):
        self.ratioPriceSeuilReconf = seuilReconf
        
    def loadInstanceAlreadyTrained(self, listInstanceAlreadyTrained):
        self.listInstanceAlreadyTrained=listInstanceAlreadyTrained
        j = 0
        while j < len(self.listInstanceFiles):
            if self.listInstanceFiles[j] in listInstanceAlreadyTrained:
                del(self.listInstanceFiles[j])
                continue
            else:
                j += 1
        
    def doEpisodeEnded(self):
        return self._episode_ended

        
    def doStillRunning(self):
        if self._episode_ended and len(self.listInstanceFiles) == 0:
            return False
        return True
        
    def setBeta(self,beta):
        self.beta = beta
        
        
    def readCSV(self,file):
        result = {}
        with open(file, 'r') as csvFile:
            reader = csv.reader(csvFile)
            listName = next(reader)
            for name in listName:
                result[name] = []
                
            for row in reader:
                #tmpList = list(map(float, row))
                for i in range(len(row)):
                    tmp = row[i].replace("[","")
                    tmp = tmp.replace("]","")
                    tmp = tmp.replace(" ","")
                    tmp = tmp.split(",")
                    result[listName[i]].append(float(tmp[0]))
        csvFile.close()
        return result
        
        
    def loadSolutionCompare(self):
        
        dossier = os.path.join("..", "resultsCSV")
        dossier = os.path.join(dossier, "Dynamic")
        dossier = os.path.join(dossier, self.topoName)
        dossier = os.path.join(dossier, self.instanceName)
        dossier = os.path.join(dossier, str(self.instanceNum))
        pathNoreconf = os.path.join(dossier, "NoReconf_Beta-1")
        pathReconf = os.path.join(dossier, "Reconf_Beta-1_Freq-15")
        
        """tmp = self.readCSV(os.path.join(pathNoreconf, "global.csv"))
        profitNoReconf = tmp["profit"][0]
        tmp = self.readCSV(os.path.join(pathReconf, "global.csv"))
        profitReconf = tmp["profit"][0]
        nbReconf = tmp["nbReconf"][0]"""
        """tmp = self.readCSV(os.path.join(pathReconf, "local.csv"))
        maxProfitReconf = max(tmp["profit"])"""
        tmp = self.readCSV(os.path.join(pathNoreconf, "local.csv"))
        listProfitNoReconf = tmp["profit"]
    
        #costReconf = max(profitReconf - profitNoReconf, 0) / nbReconf
        
        costReconf = 1
        maxProfitReconf = 1
        
        return costReconf, listProfitNoReconf, maxProfitReconf
        
        

        
    def _reset(self):
        
        if not self.doStillRunning():
            print("ReconfigurationEnvironement : I can't reset, there is no more instances, I'm empty :'(")
            return False
        
        """self.dictReward = {}
        self.listCostReconf = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
        self.listVersionReward = [1,2]
        for i in self.listVersionReward:
            for j in self.listCostReconf:
                self.dictReward["Reward-{}_Cost-{}".format(i,j)] = []"""
        
        self.instanceNum = self.listInstanceFiles[0].split("-")[-1:][0]
        self.instanceName = "{}-S{}".format(self.listInstanceFiles[0][:-(1+len(self.instanceNum))], self.TopologySettings)
        
        if True :
            self.costReconf = 1
            self.listProfitNoReconf =[0 for _ in range(2000)]
            self.maxProfitReconf = 0
        else:
            self.costReconf, self.listProfitNoReconf, self.maxProfitReconf = self.loadSolutionCompare()
        #self.costReconf = 1
        self.costReconf = self.ratioPriceSeuilReconf*self.costReconf
        
        self.rewardTotal = 0
        #print("Debug Env : Reset Start")
        self._episode_ended = False
        
        if self.newTopo:
            listOfArrival = scenarioManager.loadInstance("..",self.topoName, self.listInstanceFiles[0])
        else:
            param.startDynamic = param.startDynamicOld
            param.timePeriodeDynamic = param.timePeriodeDynamicOld
            listOfArrival = scenarioManager.loadInstanceOld("..",self.topoName, self.listInstanceFiles[0])
            links, nodes, DC, capaLink, capaNode, nbVnf = initializeNetworkDynamic.avgCapa(self.topoName, self.functions, listOfArrival, 3)
            self.topology = TopologyManager.Topology(nodes, links)
            self.nbVnf = (len(self.topology.listDCCore) + len(self.topology.listDCEdge)) * len(self.functions)
            capaLink = self.topology.linksCapacity
        
            self.costMaxVnf = 0
            for f in self.functions:
                self.costMaxVnf +=  self.functions[f][1]
            self.costMaxVnf = self.costMaxVnf * (len(self.topology.listDCCore) + len(self.topology.listDCEdge))
            
            self.ratioBeta = (capaLink/float(self.costMaxVnf))
        
        
        
        """                     AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA               *******************************************************************    """
        #listOfArrival = listOfArrival[:250]
        """                     AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA               *******************************************************************    """
        
        self.scenario = scenarioManager.Scenario(self.topoName, self.topology, self.listInstanceFiles[0], listOfArrival, self.functions)
        
        listSlicesAccepted = []
        listSlicesCurrentlyAllocated = []
        currentAlloc = {}
        currentPaths = {}
        self.doIReconfigureNow = False
        
        
        if self.evaluation:
            self.listTimeStepReconf = []
            self.listPeriodeReconf = []
            self.listReward = []
            self.listImprovVnf = []
            self.listImprovCostMb = []
            self.listImprovVnfVsFake = []
            self.listImprovCostMbVsFake = []
            self.listNbSlicesAddSinceLastReconf = []
            self.listNbSlicesRemoveSinceLastReconf = []
            self.listNbMinutesSinceLastReconf = []
            self.listPercBandwidthUsed = []
            self.listPercVnfUsed = []
            self.listPercBandwidthAllocated = []
            self.listNbSlicesAllocated = []
        
        self.nbSlicesAddSinceLastReconf = 0
        self.nbSlicesRemoveSinceLastReconf = 0
        self.nbSlicesRejectSinceLastReconf = 0
        self.nbMinutesSinceLastReconf = 0
        self.timeStep = 0
        self.reconfsDone = []
        
        
        """    #################################################################################################################    """
        """                                          Initialising the Network                                                       """
        """    #################################################################################################################    """ 
        
        for i in range(param.startDynamic):
            
            nodeFunction = {}
            linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, listSlicesCurrentlyAllocated, currentAlloc, roundNumber = 8)
            #We allocate a new one
            slices = self.scenario.getNewSlices()        
            
            
            for s in slices:
                allocPossible, dictPathTMP, currentAllocTMP = allocILP.findAllocation(self.topology, nodesUsage, linksUsage, [s], self.functions, nodeFunction, self.ratioBeta*self.betaInit)
                if allocPossible :
                    listSlicesAccepted.append(s)
                    listSlicesCurrentlyAllocated.append(s)
                    currentAlloc[s.id] = currentAllocTMP[s.id]
                    currentPaths[s.id] = dictPathTMP[s.id]
                    linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, listSlicesCurrentlyAllocated, currentAlloc, roundNumber = 8)
                    
                    self.nbSlicesAddSinceLastReconf += 1
                else:
                    self.nbSlicesRejectSinceLastReconf += 1
            self.nbMinutesSinceLastReconf += 1
            
            #We remove the dead sfc
            j = 0
            while j < len(listSlicesCurrentlyAllocated):
                if listSlicesCurrentlyAllocated[j].timeOfDeath == i:
                    del(currentPaths[listSlicesCurrentlyAllocated[j].id])
                    del(currentAlloc[listSlicesCurrentlyAllocated[j].id])
                    del(listSlicesCurrentlyAllocated[j])
                    self.nbSlicesRemoveSinceLastReconf += 1
                    continue
                else:
                    j += 1
                    
            
        
    

        bwUsed = Util.bandwithUsed(listSlicesCurrentlyAllocated, currentAlloc)
        
        capaLink = self.topology.linksCapacity
        capaDC = self.topology.DCCapacity
        
        name = "Reconf_Beta-1_Freq-LR"
        objectifChooser = ObjectifChooser.ObjectifChooser([1])
        reconfChooser = self
        self.allocateur = AllocateurDynamic.AllocateurDynamic(name, self.topology, self.nbVnf, self.costMaxVnf, capaDC, capaLink, self.functions, currentAlloc, currentPaths, listSlicesCurrentlyAllocated, objectifChooser, reconfChooser, True, self.nbSteps)


        #self.nbSlicesAddSinceLastReconf = len(listSlicesAccepted)
        #self.nbSlicesDeadSinceReconf = len(listSlicesCurrentlyAllocated)
        
        self.timeStep = param.startDynamic
        self.nbMinutesSinceLastReconf = param.startDynamic

        
        slices = self.scenario.getNewSlices() 
        for s in slices:
            self.allocateur.addSlice(s, self.timeStep)
            if len(self.allocateur.listSlicesAccepted)>0:
                if self.allocateur.listSlicesAccepted[-1].id == s.id:
                    self.nbSlicesAddSinceLastReconf+=1
                else:
                    self.nbSlicesRejectSinceLastReconf
            else:
                    self.nbSlicesRejectSinceLastReconf
            
        #self.nbMinutesSinceLastReconf +=1
            
        nbSlices = len(self.allocateur.listSlicesCurrentlyAllocated)

        self.allocateur.removeSlices(self.timeStep)
        self.nbSlicesRemoveSinceLastReconf += nbSlices-len(self.allocateur.listSlicesCurrentlyAllocated)
        
        self._state = self.makeState()

        #print("Debug Env : Reset Stop")
        return ts.restart(np.array([self._state], dtype=np.float32))
    
    
    def fakeAlloc(self, listListSlices):
        
        listSlicesAdd = []
        listSlicesAllocated = self.allocateur.listSlicesCurrentlyAllocated.copy()
        timeStep = self.timeStep
        
        linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, listSlicesAllocated, self.allocateur.currentAlloc, roundNumber = 8)
        
        bwAllocated = []
        CostVnfsUsed = []
        profit = []
        
        for i in range(len(listListSlices)):
            timeStep += 1
            listSlices = listListSlices[i]
            if listSlices == None:
                break
            for s in listSlices:
                    
                
                allocPossible, dictPathTMP, currentAllocTMP = allocILP.findAllocation(self.topology, nodesUsage, linksUsage, [s], self.functions, nodeFunction, self.ratioBeta*self.beta)
                if allocPossible :
                    listSlicesAdd.append(s)
                    listSlicesAllocated.append(s)
                    self.allocateur.currentAlloc[s.id] = currentAllocTMP[s.id]
                    self.allocateur.currentPaths[s.id] = dictPathTMP[s.id]
                    linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, listSlicesAllocated, self.allocateur.currentAlloc, roundNumber = 8)
             

                
            j = 0
            while j < len(listSlicesAllocated):
                if listSlicesAllocated[j].timeOfDeath == timeStep:
                    del(listSlicesAllocated[j])
                    continue
                else:
                    j += 1
                    
            tmp = 0
            tmp2 = 0  
            for s in listSlicesAllocated:
                tmp += s.bd
                tmp2 += s.revenuPerTimeStep
            bwAllocated.append(tmp)
                    
            linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, listSlicesAllocated, self.allocateur.currentAlloc, roundNumber = 8)
            tmp = 0
            for u in nodesUsage:
                for f in nodeFunction[u]:
                    tmp += self.functions[f][1]
            CostVnfsUsed.append(tmp)
            profit.append(tmp2 - tmp)
            

        for s in listSlicesAdd:
            if s.id in self.allocateur.currentPaths:
                del(self.allocateur.currentPaths[s.id])
            if s.id in self.allocateur.currentAlloc:
                del(self.allocateur.currentAlloc[s.id])
                
        return CostVnfsUsed, bwAllocated, profit
    
    
    
    
    def _step(self, action):        
        if self._episode_ended:
            return self._reset()
        self.reconfsDone.append(action.item(0))


        """    #################################################################################################################    """
        """                               We first reconfigure to see if we have an improvement                                     """
        """    #################################################################################################################    """     
        
        #print("Debug Env : Step {}".format(self.timeStep))
        
        listListSlicesState = []
        listListSlicesFakeAlloc = []
        listListSlicesCost = []
        for _ in range(self.numberOfStepsByState):
    
            listSlices = self.scenario.getNewSlices()
            if listSlices == None:
                listListSlicesState.append(None)
                listListSlicesFakeAlloc.append(None)
                break
            else:
                listListSlicesState.append(listSlices)
                listListSlicesFakeAlloc.append(listSlices)
                
        iteratorTmp = self.scenario.iteratorArrival
        for _ in range(self.numberOfStepsByState, self.numberOfStepsForCost):
            
            if iteratorTmp == self.scenario.nbTimeStep:
                listListSlicesCost.append(None)
                listListSlicesFakeAlloc.append(None)
                break
            else:
                listListSlicesCost.append(self.scenario.listOfArrival[iteratorTmp])
                listListSlicesFakeAlloc.append(self.scenario.listOfArrival[iteratorTmp])
                iteratorTmp+=1


        listProfit = []
        listCostVnfUsed = []
        listProfitNoReconf = []
        listCostVnfNoReconf = []
        
        #I the action is to reconfigure
        if action == 1:
            
            listCostVnfNoReconf, listBwAllocatedNoReconf, listProfitNoReconf = self.fakeAlloc(listListSlicesFakeAlloc) 
            
            if self.evaluation:
                self.listTimeStepReconf.append(self.timeStep)
                periodeList = param.timePeriodeDynamic
                periode = "D3"
                for i in periodeList:
                    if self.timeStep >= i:
                        periode = periodeList[i]
                self.listPeriodeReconf.append(periode)
                self.listNbSlicesAddSinceLastReconf.append(self.nbSlicesAddSinceLastReconf)
                self.listNbSlicesRemoveSinceLastReconf.append(self.nbSlicesRemoveSinceLastReconf)
                self.listNbMinutesSinceLastReconf.append(self.nbMinutesSinceLastReconf)
                bwUsed, nbVnfUsed = Util.bandwithAndVnfUsed(self.allocateur.listSlicesCurrentlyAllocated, self.allocateur.currentAlloc)
                self.listPercBandwidthUsed.append(float(bwUsed)/self.topology.linksCapacity*100)
                self.listPercVnfUsed.append(float(nbVnfUsed)/self.nbVnf*100)
                maxBwServed = 0
                if len(self.topology.listBaseStation) > 0:
                    for (u,v) in self.topology.links:
                        if u in self.topology.listBaseStation:
                            maxBwServed += self.topology.links[0]
                else : 
                    maxBwServed = 1
                bwAllocated = 0
                for s in self.allocateur.listSlicesCurrentlyAllocated:
                    bwAllocated += s.bd
                self.listPercBandwidthAllocated.append(float(bwAllocated)/maxBwServed*100)
                self.listNbSlicesAllocated.append(len(self.allocateur.listSlicesCurrentlyAllocated))
                
                bwAllocated = 0   
                for s in self.allocateur.listSlicesCurrentlyAllocated:
                    bwAllocated += s.bd
                linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, self.allocateur.listSlicesCurrentlyAllocated, self.allocateur.currentAlloc, roundNumber = 8)
                CostVnfsUsed = 0
                for u in nodesUsage:
                    for f in nodeFunction[u]:
                        CostVnfsUsed += self.functions[f][1]
                costByMb = CostVnfsUsed/float(bwAllocated)
                        
        
            
            
            
            self.doIReconfigureNow = True
            self.allocateur.update(self.timeStep, remove = False)
            self.doIReconfigureNow = False
            
            listProfit.append(self.allocateur.profit[int(self.timeStep - param.startDynamic)])
            listCostVnfUsed.append(self.allocateur.CostVnfsUsed[int(self.timeStep - param.startDynamic)])
            
            if self.evaluation:
                
                newBwAllocated = 0   
                for s in self.allocateur.listSlicesCurrentlyAllocated:
                    newBwAllocated += s.bd
                linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, self.allocateur.listSlicesCurrentlyAllocated, self.allocateur.currentAlloc, roundNumber = 8)
                newCostVnfsUsed = 0
                for u in nodesUsage:
                    for f in nodeFunction[u]:
                        newCostVnfsUsed += self.functions[f][1]
                newCostByMb = newCostVnfsUsed/float(newBwAllocated)
                
                self.listImprovVnf.append((CostVnfsUsed - newCostVnfsUsed)/float(CostVnfsUsed)*100)
                self.listImprovCostMb.append((costByMb - newCostByMb)/float(costByMb)*100)
                
            
            
        else:
            
            self.allocateur.update(self.timeStep, remove = False)
            listProfit.append(self.allocateur.profit[int(self.timeStep - param.startDynamic)])
            listCostVnfUsed.append(self.allocateur.CostVnfsUsed[int(self.timeStep - param.startDynamic)])
            
        
        
        #print("{}    {}    {}".format(self.timeStep, self._state, action))
        
        """    #################################################################################################################    """
        """                               We add the new slices before the new reconfiguration                                      """
        """    #################################################################################################################    """   
        for i in range(self.numberOfStepsByState):
            self.timeStep += 1
    
            listSlices = listListSlicesState[i]
            if listSlices == None:
                
                if action == 1:
                    bwAllocated = 0   
                    for s in self.allocateur.listSlicesCurrentlyAllocated:
                        bwAllocated += s.bd
                    linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, self.allocateur.listSlicesCurrentlyAllocated, self.allocateur.currentAlloc, roundNumber = 8)
                    CostVnfsUsed = 0
                    for u in nodesUsage:
                        for f in nodeFunction[u]:
                            CostVnfsUsed += self.functions[f][1]
                

                reward = self.makeReward(listProfit, listProfitNoReconf, listCostVnfUsed, listCostVnfNoReconf, action)
                    
                if self.evaluation and action == 1:
                    bwAllocated = 0   
                    for s in self.allocateur.listSlicesCurrentlyAllocated:
                        bwAllocated += s.bd
                    linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, self.allocateur.listSlicesCurrentlyAllocated, self.allocateur.currentAlloc, roundNumber = 8)
                    CostVnfsUsed = 0
                    for u in nodesUsage:
                        for f in nodeFunction[u]:
                            CostVnfsUsed += self.functions[f][1]
                    #fakeCostByMb = fakeCostVnfsUsed/float(fakeBwAllocated)
                    costByMb = CostVnfsUsed/float(bwAllocated)
                    self.listReward.append(reward)
                    #self.listImprovVnfVsFake.append((fakeCostVnfsUsed - CostVnfsUsed)/float(fakeCostVnfsUsed)*100)
                    #self.listImprovCostMbVsFake.append((fakeCostByMb - costByMb)/float(fakeCostByMb)*100)

                self.rewardTotal += reward
                
                self._episode_ended = True
                
                self.listInstanceAlreadyTrained.append(self.listInstanceFiles[0])
                #self.saveTest()
                if self.evaluation:
                    self.saveEvaluation()
                del(self.listInstanceFiles[0])
                print("Number reconf done {}".format(sum(self.reconfsDone)))
                print("Reward : {}".format(self.rewardTotal))
                

    
                self._state = self.makeState()
                
            
        
                return ts.termination(np.array([self._state], dtype=np.float32), reward=reward)
                
            else:
                for s in listSlices:
                    self.allocateur.addSlice(s, self.timeStep)
                    if self.allocateur.listSlicesAccepted[-1].id == s.id:
                        self.nbSlicesAddSinceLastReconf+=1
                    else:
                        self.nbSlicesRejectSinceLastReconf
                    
                self.nbMinutesSinceLastReconf +=1
                    
                nbSlices = len(self.allocateur.listSlicesCurrentlyAllocated)
                #We do not do the update for the last, it will be done at the next step
                if i < self.numberOfStepsByState-1:
                    self.allocateur.update(self.timeStep)
                    listProfit.append(self.allocateur.profit[int(self.timeStep - param.startDynamic)])
                    listCostVnfUsed.append(self.allocateur.CostVnfsUsed[int(self.timeStep - param.startDynamic)])
                    #listProfitNoReconf.append(self.listProfitNoReconf[self.timeStep - param.startDynamic])
                else:
                    self.allocateur.removeSlices(self.timeStep)
                self.nbSlicesRemoveSinceLastReconf += nbSlices-len(self.allocateur.listSlicesCurrentlyAllocated)
                    
        listCostVnfAdditionnal, listBwAllocatedAdditionnal, listProfitAdditionnal = listCostVnfUsed, [], listProfit     
        if action == 1:
            bwAllocated = 0   
            for s in self.allocateur.listSlicesCurrentlyAllocated:
                bwAllocated += s.bd
            linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, self.allocateur.listSlicesCurrentlyAllocated, self.allocateur.currentAlloc, roundNumber = 8)
            CostVnfsUsed = 0
            for u in nodesUsage:
                for f in nodeFunction[u]:
                    CostVnfsUsed += self.functions[f][1]
        
        

            #We complete by a knew fake alloc to compare with more step (numberOfStepsForCost) than just numberOfStepsByState
            listCostVnfAdditionnal, listBwAllocatedAdditionnal, listProfitAdditionnal = self.fakeAlloc(listListSlicesCost) 
            for i in range(len(listProfit)):
                listProfitAdditionnal.append(listProfit[i])
                #listBwAllocatedAdditionnal.append(aaaaa[i])
                listCostVnfAdditionnal.append(listCostVnfUsed[i])
        reward = self.makeReward(listProfitAdditionnal, listProfitNoReconf, listCostVnfAdditionnal, listCostVnfNoReconf, action)
        
        
        if self.evaluation and action == 1:
            bwAllocated = 0   
            for s in self.allocateur.listSlicesCurrentlyAllocated:
                bwAllocated += s.bd
            linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, self.allocateur.listSlicesCurrentlyAllocated, self.allocateur.currentAlloc, roundNumber = 8)
            CostVnfsUsed = 0
            for u in nodesUsage:
                for f in nodeFunction[u]:
                    CostVnfsUsed += self.functions[f][1]
            #fakeCostByMb = fakeCostVnfsUsed/float(fakeBwAllocated)
            costByMb = CostVnfsUsed/float(bwAllocated)
            self.listReward.append(reward)
            #self.listImprovVnfVsFake.append((fakeCostVnfsUsed - CostVnfsUsed)/float(fakeCostVnfsUsed)*100)
            #self.listImprovCostMbVsFake.append((fakeCostByMb - costByMb)/float(fakeCostByMb)*100)

        
        
        
        self.rewardTotal += reward

        
        self._state = self.makeState()
        
        #print("{} {}".format(reward, self._state))
    
        return ts.transition(np.array([self._state], dtype=np.float32), reward=reward, discount=self.gammaDiscount)
    
    
    
    def makeReward(self, profit, profitNoNeconf, costVnfUsed, costVnfUsedNoNeconf, reconfDone):
        if self.rewardVersion == 2:
            if reconfDone:  
                reward = sum(costVnfUsedNoNeconf) - sum(costVnfUsed) - (self.costReconf*len(costVnfUsed))
            else:
                reward = 0
        elif self.rewardVersion == 1:
            if reconfDone:
                cost = sum(costVnfUsed) + (self.costReconf*len(costVnfUsed))
                if cost >= sum(costVnfUsedNoNeconf):
                    reward = -1
                else:
                    cost = sum(costVnfUsedNoNeconf) - cost
                    reward = 1+float(cost)/sum(costVnfUsedNoNeconf)
            else:
                reward = 0
                
        elif self.rewardVersion == 3:
            if reconfDone:  
                reward = sum(profit) - sum(profitNoNeconf) - (self.costReconf*len(profit))
            else:
                reward = 0
            
                
        return reward
        
        
        
    def doIReconfigureNowMBB(self, timeStep, nbSlicesAccepted, nbSlicesRejected, nbSlicesAllocated, topology, functions, listSlicesCurrentlyAllocated, currentAlloc, currentPaths, nbSteps, beta, useLP, stableStop, timeLimit):
        
        if self.doIReconfigureNow:
            objBW, objVNF = Util.objective(topology.listAllDC, listSlicesCurrentlyAllocated, functions, currentAlloc)
            lastObj = objBW + (objVNF*beta)
            
            reconfManager = reconfController.reconfController(self.topology, self.functions, listSlicesCurrentlyAllocated, self.nbSteps, self.ratioBeta*self.beta, useLP = True, stableStop = param.stableStopGC, timeLimit = param.timeLimitReconf)
            reconfManager.initialise(currentPaths)
            res_Reconf, pathUsed_Reconf = reconfManager.solve([0,0,0,0,0], param.nbThreadSub)
            timeTotal = reconfManager.timeTotal
    
            objBW, objVNF = Util.objective(topology.listAllDC, listSlicesCurrentlyAllocated, functions, res_Reconf)
            obj = objBW + (objVNF*beta)
            
            #We update the state
            self.nbMinutesSinceLastReconf = 0
            self.nbSlicesAddSinceLastReconf = 0
            self.nbSlicesRejectSinceLastReconf = 0
            self.nbSlicesRemoveSinceLastReconf = 0
    
            return True, res_Reconf, pathUsed_Reconf, lastObj, obj, timeTotal
        else:

            return False, None, None, None, None, None
        
    
    def makeState(self):
        #Version 1
        if self.stateVersion == 1:
            bwUsed = Util.bandwithUsed(self.allocateur.listSlicesCurrentlyAllocated, self.allocateur.currentAlloc)
            return [self.nbSlicesAddSinceLastReconf, self.nbSlicesRejectSinceLastReconf, self.nbSlicesRemoveSinceLastReconf, self.nbMinutesSinceLastReconf, float(bwUsed)/self.topology.linksCapacity, float(self.timeStep)/len(self.scenario.listOfArrival)]
        
        #Version 2
        elif self.stateVersion == 2:
            print("Version make state NOOOO")
            exit()
            bwUsed, nbVnfUsed = Util.bandwithAndVnfUsed(self.allocateur.listSlicesCurrentlyAllocated, self.allocateur.currentAlloc)
            maxBwServed = self.topology.numberLinksToBaseStations * self.topology.capacityEdgeLinks
            bwServed = 0
            for s in self.allocateur.listSlicesCurrentlyAllocated:
                bwServed += s.bd
            return [ float(bwServed)/maxBwServed, float(nbVnfUsed)/self.nbVnf, float(bwUsed)/self.topology.linksCapacity, float(self.timeStep)/len(self.scenario.listOfArrival)]
        
        #Version 3
        elif self.stateVersion == 3:
            return [float(self.nbMinutesSinceLastReconf)/len(self.scenario.listOfArrival), float(self.timeStep)/len(self.scenario.listOfArrival)]
        
        #Version 4
        elif self.stateVersion == 4:
            return [float(self.nbSlicesAddSinceLastReconf)/len(self.scenario.listOfArrival), float(self.nbSlicesRemoveSinceLastReconf)/len(self.scenario.listOfArrival), float(self.nbMinutesSinceLastReconf)/len(self.scenario.listOfArrival), float(self.timeStep)/len(self.scenario.listOfArrival)]
        #Version 5
        elif self.stateVersion == 5:
            linksUsage, nodesUsage, nodeFunction =  Util.utilisationAndVnfUsed(self.functions, self.allocateur.listSlicesCurrentlyAllocated, self.allocateur.currentAlloc, roundNumber = 8)
            newCostVnfsUsed = 0
            for u in nodesUsage:
                for f in nodeFunction[u]:
                    newCostVnfsUsed += self.functions[f][1]
            return [float(self.nbSlicesAddSinceLastReconf)/len(self.scenario.listOfArrival), float(self.nbSlicesRemoveSinceLastReconf)/len(self.scenario.listOfArrival), float(self.nbMinutesSinceLastReconf)/len(self.scenario.listOfArrival), float(self.timeStep)/len(self.scenario.listOfArrival), newCostVnfsUsed]
        #Version 6
        elif self.stateVersion == 6:
            return [float(self.nbSlicesAddSinceLastReconf)/len(self.scenario.listOfArrival), float(self.nbSlicesRemoveSinceLastReconf)/len(self.scenario.listOfArrival), float(self.nbMinutesSinceLastReconf)/len(self.scenario.listOfArrival)]
        
    def saveTest(self):
        tmp = "TestSolution-{}".format(self.topoName)
        if not os.path.exists(tmp):
            os.mkdir(tmp)
        fileName = os.path.join(tmp, "reward-{}-{}.csv".format(self.instanceName, self.instanceNum))
        listName = []
        listData = []
        for i in self.dictReward:
            self.dictReward[i].append(sum(self.dictReward[i]))
            listName.append(i)
            listData.append(self.dictReward[i])
            
        readWritter.writeCSV(fileName, listName, listData)
        
        
    def saveEvaluation(self):
        tmp = os.path.join(os.path.join(self.dossierToSave, self.instanceName),self.instanceNum)
        self.allocateur.writeResults(tmp)
        """
        fileName = os.path.join(tmp, "infoReconf.csv")
        listName = []
        listData = []
        
        listName.append("timeStep")
        listData.append(self.listTimeStepReconf)
        listName.append("periode")
        listData.append(self.listPeriodeReconf)
        listName.append("reward")
        listData.append(self.listReward)
        listName.append("percImprovVnf")
        listData.append(self.listImprovVnf)
        listName.append("percImprovCostMb")
        listData.append(self.listImprovCostMb)
        listName.append("NbSlicesAddSinceLastReconf")
        listData.append(self.listNbSlicesAddSinceLastReconf)
        listName.append("NbSlicesRemoveSinceLastReconf")
        listData.append(self.listNbSlicesRemoveSinceLastReconf)
        listName.append("NbMinutesSinceLastReconf")
        listData.append(self.listNbMinutesSinceLastReconf)
        listName.append("PercBandwidthUsed")
        listData.append(self.listPercBandwidthUsed)
        listName.append("PercVnfUsed")
        listData.append(self.listPercVnfUsed)
        listName.append("PercBandwidthAllocated")
        listData.append(self.listPercBandwidthAllocated)
        listName.append("NbSlicesAllocated")
        listData.append(self.listNbSlicesAllocated)
    
        readWritter.writeCSV(fileName, listName, listData)
    """
        
        
    def action_spec(self):
        return self._action_spec

    def observation_spec(self):
        return self._observation_spec
        
    
    def get_state(self):
        print("get_state")
        exit()
        #return [self.topoName, self.TopologySettings, self.SliceDistrib, self.nbSteps, self._episode_ended, self.listInstanceFiles[:], self.listInstanceAlreadyTrained[:], self.betaInit, self.beta, self.ratioBeta, self.costMaxVnf, self.gammaDiscount, self.timeStep, listSlicesCurrentlyAllocated[:], copy.deepcopy(currentAlloc), copy.deepcopy(currentPaths), self.nbSlicesAddSinceLastReconf, self.nbSlicesRemoveSinceLastReconf, self.nbSlicesRejectSinceLastReconf, self.nbMinutesSinceLastReconf]
       
    def set_state(self, state):
        
        print("set_state")
        exit()
        
        """
        self.topoName = state[0]
        self.TopologySettings = state[1]
        self.SliceDistrib = state[2]
        self.functions = scenarioManager.readFunctions("..")
        self.nbSteps = state[3]
        self._episode_ended = state[4]
        self.reconfsDone = []
        
        self.listInstanceFiles = state[5]
        self.listInstanceAlreadyTrained = state[6]
       
        self.topology = TopologyManager.loadTopology("..", self.topoName)
        capacityCoreLinks, capacityEdgeLinks, capacityConnectivityLinks, capacityCoreDC, capacityEdgeDC, latencyCoreLinks, latencyEdgeLinks, latencyConnectivityLinks = scenarioManager.readTopologySettings("..", "TopologySettings_{}".format(self.TopologySettings))
        self.topology.setSettings(capacityCoreLinks, capacityEdgeLinks, capacityConnectivityLinks, capacityCoreDC, capacityEdgeDC, latencyCoreLinks, latencyEdgeLinks, latencyConnectivityLinks)
        self.nbVnf = (self.topology.nbDCCore + self.topology.nbDCEdge) * len(self.functions)
        
        self.betaInit = state[7]
        self.beta = state[8]
        self.ratioBeta = state[9]
        self.gammaDiscount = state[10]
        
        self.costMaxVnf = state[11]
        self.timeStep = state[12]
        
        listSlicesCurrentlyAllocated = state[13]
        currentAlloc = state[14]
        currentPaths = state[15]
        
        if self.doStillRunning():
            
            self.nbSlicesAddSinceLastReconf = state[16]
            self.nbSlicesRemoveSinceLastReconf = state[17]
            self.nbSlicesRejectSinceLastReconf = state[18]
            self.nbMinutesSinceLastReconf = state[19]
            
            listOfArrival = scenarioManager.loadInstance("..",self.topoName, self.listInstanceFiles[0])
            self.scenario = scenarioManager.Scenario(self.topoName, self.topology, self.listInstanceFiles[0], listOfArrival, self.functions)
            
            for i in range(self.timeStep+1):
                slices = self.scenario.getNewSlices()
        """
        
