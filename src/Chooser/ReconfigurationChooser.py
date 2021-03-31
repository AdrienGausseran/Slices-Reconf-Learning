
import time
import os

from allocation import allocILP
#from allocation import allocILPImprov as allocILP
#from allocation import allocILPMinMax as allocILP

from reconfiguration import reconfController
from Util import Util
from Util import readWritter

import param


class ReconfigurationChooser(object):
    def __init__(self, timeStep):
        '''
        Constructor
        '''
        self.timeStepsSinceReconf = 0
        self.nbSlicesAcceptedSinceReconf = 0
        self.nbSlicesRejectedSinceReconf = 0
        
    def initialize(self, nbSlicesAccepted, nbSlicesRejected, nbSlicesAllocated):
        pass
        
    def doIReconfigureNow(self):
        return False
    
    def doIReconfigureNowMBB(self, timeStep, nbSlicesAccepted, nbSlicesRejected, nbSlicesAllocated, topology, functions, listSlicesCurrentlyAllocated, currentAlloc, currentPaths, nbSteps, beta, useLP, stableStop, timeLimit):
        return False, None, None, None, None, None
    
    def doIReconfigureNowBBM(self, timeStep, nbSlicesAccepted, nbSlicesRejected, nbSlicesAllocated, topology, functions, listSlicesCurrentlyAllocated, currentAlloc, currentPaths, beta, timeLimit, optimalNeeded):
        return False, None, None, None, None, None
    
    
class ReconfigurationPeriodiqueTime(ReconfigurationChooser):
    def __init__(self, timeStep, frenquency):
        '''
        Constructor
        '''
        self.timeStepsSinceReconf = 0
        self.nbSlicesAcceptedSinceReconf = 0
        self.nbSlicesRejectedSinceReconf = 0
        self.frenquency = frenquency
        
    def doIReconfigureNow(self, timeStep):
        self.timeStepsSinceReconf += 1
        
        if self.timeStepsSinceReconf == self.frenquency:
            self.timeStepsSinceReconf = 0
            return True
        else:
            return False
        
    def doIReconfigureNowMBB(self, timeStep, nbSlicesAccepted, nbSlicesRejected, nbSlicesAllocated, topology, functions, listSlicesCurrentlyAllocated, currentAlloc, currentPaths, nbSteps, beta, useLP, stableStop, timeLimit):
        if self.doIReconfigureNow(timeStep):
            objBW, objVNF = Util.objective(topology.listAllDC, listSlicesCurrentlyAllocated, functions, currentAlloc)
            lastObj = objBW + (objVNF*beta)
    
            stableStopGC = param.stableStopGC
            reconfManager = reconfController.reconfController(topology, functions, listSlicesCurrentlyAllocated, nbSteps, beta, useLP = useLP, stableStop = stableStop, timeLimit = timeLimit)
            reconfManager.initialise(currentPaths)
            res_Reconf, pathUsed_Reconf = reconfManager.solve([0,0,0,0,0], param.nbThreadSub)
            timeTotal = reconfManager.timeTotal
    
            objBW, objVNF = Util.objective(topology.listAllDC, listSlicesCurrentlyAllocated, functions, res_Reconf)
            obj = objBW + (objVNF*beta)
    
            return True, res_Reconf, pathUsed_Reconf, lastObj, obj, timeTotal
        else:
            return False, None, None, None, None, None
    
    
    
    def doIReconfigureNowBBM(self, timeStep, nbSlicesAccepted, nbSlicesRejected, nbSlicesAllocated, topology, functions, listSlicesCurrentlyAllocated, currentAlloc, currentPaths, beta, timeLimit, optimalNeeded):
        if self.doIReconfigureNow(timeStep):
            objBW, objVNF = Util.objective(topology.listAllDC, listSlicesCurrentlyAllocated, functions, currentAlloc)
            lastObj = objBW + (objVNF*beta)
            
            t = time.time()
            allocPossible, pathUsed_Reconf, res_Reconf = allocILP.findAllocation(topology, {}, {}, listSlicesCurrentlyAllocated, functions, {}, beta, timeLimit = timeLimit, optimalNeeded = optimalNeeded)
            if not allocPossible:
                pathUsed_Reconf = currentPaths
                res_Reconf = currentAlloc
            timeTotal = time.time()-t
            
            objBW, objVNF = Util.objective(topology.listAllDC, listSlicesCurrentlyAllocated, functions, res_Reconf)
            obj = objBW + (objVNF*beta)
            
            return True, res_Reconf, pathUsed_Reconf, lastObj, obj, timeTotal
        else:
            return False, None, None, None, None, None
        
      
