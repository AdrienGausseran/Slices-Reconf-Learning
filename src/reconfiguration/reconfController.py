import time
from multiprocessing import Process, Manager
from random import shuffle
from copy import copy
from collections import deque

from reconfiguration import master as reconfMaster
from allocation import subProbLP as subLP
from allocation import subProbILP as subILP
from Util import Util
import param

class reconfController(object):
    
    def __init__(self, topology, functions, listSlice, nbStepsReconf, beta, useLP = True, stableStop = True, timeLimit = 1000):
        
        self.verbose = param.verbose
        self.checkSolution = param.checkSolution
        
        self.integerPath = param.integerPath
        
        self.topology = topology
        self.functions = functions
        self.listSlice = listSlice
        self.beta = beta
        self.nbStepsReconf = nbStepsReconf
        self.useLP = useLP
        self.stableStop = stableStop
        
        self.timeLimit = timeLimit
        
        self.nbIteration = 0
        self.nbColumn = 0
        
        self.timeTotal = 0
        self.timeSubs = 0
        self.timeMaster = 0
        self.timeOptimal = 0
        
        self.objRelax = 0
        self.obj = 0
        self.bwUsed = 0
        self.objVnf = 0
        
        self.subs = []
        self.master = None
        
        self.oldObj = deque()
        
    def initialise(self, dictPath):
        tStart = time.time()
        #Creation des subProbs Reconfiguration
        if self.useLP:
            for s in self.listSlice:
                self.subs.append(subLP.SubProb(self.topology, self.functions, s, self.beta, self.nbStepsReconf))
        else:
            self.subs = [subILP.SubProb(self.topology, self.functions, s, self.beta, self.nbStepsReconf) for s in self.listSlice] 

        for sub in self.subs:
            sub.cost = 0
            sub.addPath(dictPath[sub.slice.id])
        self.timeSubs += time.time() - tStart
        
        #Creation du master reconf
        self.master = reconfMaster.Master(self.topology, self.functions, self.listSlice, self.nbStepsReconf, self.beta, dictPath, self.integerPath)
        self.timeTotal += time.time() - tStart
        
        
        
        
    def solve(self, filterVector = [0,0,0,0,0], nbThread = 1):
        
        if nbThread > 1:
            return self.solveMultiThread(nbThread, filterVector)
        
        tStart = time.time()
        
        opt = False
        while not opt:
            self.nbIteration += 1
            opt = True
            t = time.time()
            self.objRelax = self.master.solve(self.verbose)
            if self.nbIteration == param.nbIterationMaxFoCG or (time.time()-tStart) > (self.timeLimit*0.80):
                break
            duals, constraintOnePath, constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed = self.master.getDuals()
            self.timeMaster += time.time() - t
    
            t = time.time()
            for sub in self.subs:
                listPath = []
                for step in range(self.nbStepsReconf, 0, -1):
                    sub.updateObjective(duals, constraintOnePath[sub.slice.id][step], constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed, step)
                    reduceCost, path = sub.solve(step)
                    if reduceCost < 0:
                        listPath.append(path)
                        self.nbColumn +=1
                        opt = False
                        #print(path.alloc)
                for path in listPath :
                    self.master.addPath(path, sub.slice)
            self.timeSubs += time.time() - t
            
            if self.stableStop :
                stableCycle = param.stableCycle
                self.oldObj.append(self.objRelax)
                if len(self.oldObj) > stableCycle:
                    oldObj = self.oldObj.popleft()
                    if (oldObj- self.objRelax)/float(oldObj)*100 < 0.1:
                        opt = True
                
                
        t = time.time()
        if(filterVector[0]):
            self.master.reduceNumberOfPath1()
            if(self.verbose):
                print("Filtre reduceNumberOfPath1")
        elif(filterVector[1]):
            self.master.reduceNumberOfPath2()
            if(self.verbose):
                print("Filtre reduceNumberOfPath2")
        elif(filterVector[2]):
            self.master.reduceNumberOfPath3()
            if(self.verbose):
                print("Filtre reduceNumberOfPath3")
        elif(filterVector[3]):
            self.master.reduceNumberOfPath4()
            if(self.verbose):
                print("Filtre reduceNumberOfPath4")
        elif(filterVector[4]):
            self.master.reduceNumberOfPath5()
            if(self.verbose):
                print("Filtre reduceNumberOfPath5")


        limit = max(self.timeLimit*0.2, time.time()-tStart)
        limit = max(limit, 5)

        self.master.solveOpt(limit)
        self.timeOptimal = time.time() - t
        self.timeTotal += time.time() - tStart
        res_Reconf, NumPathUsed_Reconf, pathUsed_Reconf = self.master.getResult(checkSolution=self.checkSolution)
        self.obj, self.bwUsed, self.objVnf = Util.objective(self.nodes, self.listSlice, res_Reconf, self.beta)
        
        self.master.terminate()
        for sub in self.subs:
            sub.terminate()
        
        return res_Reconf, pathUsed_Reconf
    
    

    def solveMultiThread(self, nbThreadSub, filterVector = [0,0,0,0,0]):

        def doYourJobYouUselessThread(listSub, duals, constraintOnePath, constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed, nbStepsReconf, dictPath):
            for sub in listSub:
                listPath = []
                for step in range(nbStepsReconf, 0, -1):
                    sub.updateObjective(duals, constraintOnePath[sub.slice.id][step], constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed, step)
                    reduceCost, path = sub.solve(step)
                    if reduceCost < 0:
                        listPath.append(path)
                dictPath[sub.slice.id] = listPath

        tStart = time.time()
        
        #On creer les lists pour le partage dessubs parmis les threads
        listSubThread = [[] for i in range(nbThreadSub)]
        listSubTmp = copy(self.subs)
        shuffle(listSubTmp)
        nbSubByHtread = len(listSubTmp)//nbThreadSub
        dictSubThread = Manager().dict()
        it = 0
        #On remplit les listes
        for i in range(nbSubByHtread):
            for subThread in listSubThread:
                subThread.append(listSubTmp[it])
                dictSubThread[listSubTmp[it].slice.id] = []
                it += 1
        for i in range(len(listSubTmp) % len(listSubThread)):
            listSubThread[i].append(listSubTmp[it])
            dictSubThread[listSubTmp[it].slice.id] = []
            it += 1
        
        opt = False
        while not opt:
            self.nbIteration += 1
            opt = True
            t = time.time()
            self.objRelax = self.master.solve(self.verbose)
            if self.nbIteration == 150 or (time.time()-tStart) > (self.timeLimit*0.80):
                break
            duals, constraintOnePath, constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed = self.master.getDuals()
            self.timeMaster += time.time() - t
    
            t = time.time()
            
            #We launch all the threads
            listProcess = []
            for listSub in listSubThread:
                p = Process(target=doYourJobYouUselessThread, args=(listSub, duals, constraintOnePath, constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed, self.nbStepsReconf, dictSubThread))
                p.start()
                listProcess.append(p)
            #We wait for the ends of the threads
            for p in listProcess:
                p.join()
            #We add the new paths
            for sub in self.subs:
                listPath = dictSubThread[sub.slice.id]
                if len(listPath) > 0 :
                    opt = False
                    self.nbColumn += len(listPath)
                    for path in listPath :
                        self.master.addPath(path, sub.slice)
            self.timeSubs += time.time() - t
            
            for p in listProcess:
                p.terminate()
            
            if self.stableStop :
                stableCycle = param.stableCycle
                self.oldObj.append(self.objRelax)
                if len(self.oldObj) > stableCycle:
                    oldObj = self.oldObj.popleft()
                    if (oldObj- self.objRelax)/float(oldObj)*100 < 0.1:
                        opt = True
                
        #print("Reconfiguration GC subs Ok")
        t = time.time()
        if(filterVector[0]):
            self.master.reduceNumberOfPath1()
            if(self.verbose):
                print("Filtre reduceNumberOfPath1")
        elif(filterVector[1]):
            self.master.reduceNumberOfPath2()
            if(self.verbose):
                print("Filtre reduceNumberOfPath2")
        elif(filterVector[2]):
            self.master.reduceNumberOfPath3()
            if(self.verbose):
                print("Filtre reduceNumberOfPath3")
        elif(filterVector[3]):
            self.master.reduceNumberOfPath4()
            if(self.verbose):
                print("Filtre reduceNumberOfPath4")
        elif(filterVector[4]):
            self.master.reduceNumberOfPath5()
            if(self.verbose):
                print("Filtre reduceNumberOfPath5")
        else:
            if(self.verbose):
                print("Pas de Filtre")
        #limit = max(self.timeLimit - time.time()-tStart + 5, 5)
        limit = min(self.timeLimit*0.2, (time.time()-tStart)*0.25)
        limit = max(limit, 5)
        self.master.solveOpt(limit)
        self.timeOptimal = time.time() - t
        self.timeTotal += time.time() - tStart
        res_Reconf, NumPathUsed_Reconf, pathUsed_Reconf = self.master.getResult(checkSolution=self.checkSolution)
        self.bwUsed, self.objVnf = Util.objective(self.topology.listAllDC, self.listSlice, self.functions, res_Reconf)
        
        self.obj = self.bwUsed + (self.objVnf* self.beta)
        
        self.master.terminate()
        for sub in self.subs:
            sub.terminate()
            
        
        return res_Reconf, pathUsed_Reconf
