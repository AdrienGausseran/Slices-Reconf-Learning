import copy
from tf_agents.environments import py_environment
from tf_agents.specs import array_spec
from tf_agents.trajectories import time_step as ts

import numpy as np

class ReconfigurationEnvironement(py_environment.PyEnvironment):


    def __init__(self, nbState):
        
        self._action_spec = array_spec.BoundedArraySpec(shape=(), dtype=np.int32, minimum=0, maximum=1, name='action')
        self._observation_spec = array_spec.ArraySpec(shape=(1,nbState), dtype=np.int32 , name='observation')
        self._state = [0 for _ in range(nbState)]
        

    def setState(self, state):
        self._state = state
        
    def _reset(self):
        return ts.restart(np.array([self._state], dtype=np.int32))
    
    
    def _step(self, action):        
        return ts.transition(np.array([self._state], dtype=np.int32), reward=0, discount=0)
    
    
    def action_spec(self):
        return self._action_spec

    def observation_spec(self):
        return self._observation_spec
    """
    def get_state(self):
        return [self.topoName, self.TopologySettings, self.SliceDistrib, self.nbSteps, self._episode_ended, self.listInstanceFiles[:], self.listInstanceAlreadyTrained[:], self.betaInit, self.beta, self.ratioBeta, self.costMaxVnf, self.gammaDiscount, self.timeStep, self.listSlicesCurrentlyAllocated[:], copy.deepcopy(self.currentAlloc), copy.deepcopy(self.currentPaths), self.nbSlicesAddSinceLastReconf, self.nbSlicesRemoveSinceLastReconf, self.nbSlicesRejectSinceLastReconf, self.nbMinutesSinceLastReconf]
       
    def set_state(self, state):
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
        
        self.betaInit = state[7]
        self.beta = state[8]
        self.ratioBeta = state[9]
        self.gammaDiscount = state[10]
        
        self.costMaxVnf = state[11]
        self.timeStep = state[12]
        
        self.listSlicesCurrentlyAllocated = state[13]
        self.nbSlicesAllocated = len(self.listSlicesCurrentlyAllocated)
        self.currentAlloc = state[14]
        self.currentPaths = state[15]
        
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
        