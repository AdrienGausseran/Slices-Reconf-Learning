from collections import deque
import collections
from Util import pathGC

import copy
import param


#Give the percentage of SFCs that are different between two allocations (or two time steps) 
def percentageSlicesReconf(listSlice, listAlloc1, listAlloc2):
    nbReconf = 0.0
    for slice in listSlice:
        if not sameAlloc(listAlloc1[slice.id], listAlloc2[slice.id]):
            nbReconf += 1.0
            
    return nbReconf / max(1, len(listSlice)) * 100


#Return if the two allocations of a SFC are equal
def sameAlloc(alloc1, alloc2):
    #Verify that the links are the same
    for i in range(len(alloc2["link"])):
        keys1 = alloc1["link"][i].keys()
        sorted(keys1)
        keys2 = alloc2["link"][i].keys()
        sorted(keys2)
        if(keys1 != keys2):
            return False
        else:
            for k in keys2:
                if(alloc1["link"][i][k] != alloc2["link"][i][k]):
                    return False
    #Verify that the nodes are the same
    for i in range(len(alloc2["node"])):
        keys1 = alloc1["node"][i].keys()
        sorted(keys1)
        keys2 = alloc2["node"][i].keys()
        sorted(keys2)
        if(keys1 != keys2):
            return False
        else:
            for k in keys2:
                if(alloc1["node"][i][k] != alloc2["node"][i][k]):
                    return False
    return True



#Return informations about the network
#    capacities used on links
#    capacities used on nodes
#    VNFs used vnf[nodelocation][VNFinstance]
def utilisationAndVnfUsed(functions, listSlices, allocations, roundNumber = -1):
    nodesUsage, linksUsage = {}, {}
    vnfUsed = {}
    
    for s in listSlices:
        for i in range(len(s.functions)+1):
            for (u,v) in allocations[s.id]["link"][i] :
                if not (u,v) in linksUsage:
                    linksUsage[(u,v)] = 0
                linksUsage[(u,v)]+= s.bd*allocations[s.id]["link"][i][(u,v)]
                if(roundNumber>0):
                    linksUsage[(u,v)] = round(linksUsage[(u,v)], roundNumber)
                if (linksUsage[(u,v)]<0):
                    #print("Link < 0 : "+ str(u)+" "+str(v)+"  "+str(linksResidual[(u,v)][0]))
                    linksUsage[(u,v)]=0
        for i in range(len(s.functions)):
            for u in allocations[s.id]["node"][i]:
                f = s.functions[i]
                if not u in vnfUsed:
                    vnfUsed[u] = {}
                    nodesUsage[u] = 0
                if not f in vnfUsed[u]:
                    vnfUsed[u][f] = 1
                nodesUsage[u] += s.bd*functions[f][0]*allocations[s.id]["node"][i][u]
                if(roundNumber>0):
                    nodesUsage[u] = round(nodesUsage[u], roundNumber)
                if (nodesUsage[u]<0):
                    #print("node < 0 : "+ str(u)+"  "+str(nodesResidual[u][0]))
                    nodesUsage[u]=0
            
    return linksUsage, nodesUsage, vnfUsed

def utilisationTotalCoreEdge(topology, functions, listSlices, allocations, roundNumber = -1):
    linksUsage, nodesUsage, vnfUsed = utilisationAndVnfUsed(functions, listSlices, allocations, roundNumber)

    bandwidthUsed = 0
    CpuUsed = 0
    nbVnfsUsed = 0
    CostVnfsUsed = 0
    percLinksMoreThan80 = 0
    percLinksLessThan20 = 0
    percCpuMoreThan80 = 0
    percCpuLessThan20 = 0
    
    bandwidthUsedCore = 0
    CpuUsedCore = 0
    nbVnfsUsedCore = 0
    percLinksMoreThan80Core = 0
    percLinksLessThan20Core = 0
    percCpuMoreThan80Core = 0
    percCpuLessThan20Core = 0
    
    bandwidthUsedEdge = 0
    CpuUsedEdge = 0
    nbVnfsUsedEdge = 0
    percLinksMoreThan80Edge = 0
    percLinksLessThan20Edge = 0
    percCpuMoreThan80Edge = 0
    percCpuLessThan20Edge = 0
    
    for (u,v) in linksUsage:
        bandwidthUsed += linksUsage[(u,v)]
        if topology.links[(u,v)][2] == "Core":
            bandwidthUsedCore += linksUsage[(u,v)]
            if linksUsage[(u,v)] >= topology.links[(u,v)][0]*0.8:
                percLinksMoreThan80Core += 1
                percLinksMoreThan80 += 1
            elif linksUsage[(u,v)] <= topology.links[(u,v)][0]*0.2:
                percLinksLessThan20Core += 1
                percLinksLessThan20 += 1
        elif topology.links[(u,v)][2] == "Edge":
            bandwidthUsedEdge += linksUsage[(u,v)]
            if linksUsage[(u,v)] >= topology.links[(u,v)][0]*0.8:
                percLinksMoreThan80Edge += 1
                percLinksMoreThan80 += 1
            elif linksUsage[(u,v)] <= topology.links[(u,v)][0]*0.2:
                percLinksLessThan20Edge += 1
                percLinksLessThan20 += 1
        else:
            if linksUsage[(u,v)] >= topology.links[(u,v)][0]*0.8:
                percLinksMoreThan80 += 1
            elif linksUsage[(u,v)] <= topology.links[(u,v)][0]*0.2:
                percLinksLessThan20 += 1

    
    percLinksMoreThan80 = percLinksMoreThan80 /float(len(topology.links))*100
    percLinksLessThan20 = percLinksLessThan20 /float(len(topology.links))*100
    percLinksMoreThan80Core = percLinksMoreThan80Core /float(max(1,len(topology.listLinksCore)))*100
    percLinksLessThan20Core = percLinksLessThan20Core /float(max(1,len(topology.listLinksCore)))*100
    percLinksMoreThan80Edge = percLinksMoreThan80Edge /float(max(1,len(topology.listLinksEdge)))*100
    percLinksLessThan20Edge = percLinksLessThan20Edge /float(max(1,len(topology.listLinksEdge)))*100
    
    for u in nodesUsage:
        CpuUsed += nodesUsage[u]
        for f in vnfUsed[u]:
            CostVnfsUsed += functions[f][1]
        if topology.nodes[u][2] == "Core":
            CpuUsedCore += nodesUsage[u]
            nbVnfsUsed += len(vnfUsed[u])
            nbVnfsUsedCore += len(vnfUsed[u])
            if nodesUsage[u] >= topology.nodes[u][0]*0.8:
                percCpuMoreThan80 += 1
                percCpuMoreThan80Core += 1
            elif nodesUsage[u] <= topology.nodes[u][0]*0.2:
                percCpuLessThan20 += 1
                percCpuLessThan20Core += 1
        
        elif topology.nodes[u][2] == "Edge":
            CpuUsedEdge += nodesUsage[u]
            nbVnfsUsed += len(vnfUsed[u])
            nbVnfsUsedEdge += len(vnfUsed[u])
            if nodesUsage[u] >= topology.nodes[u][0]*0.8:
                percCpuMoreThan80 += 1
                percCpuMoreThan80Edge += 1
            elif nodesUsage[u] <= topology.nodes[u][0]*0.2:
                percCpuLessThan20 += 1
                percCpuLessThan20Edge += 1
        

    percCpuMoreThan80 = percCpuMoreThan80 /float(max(1,len(topology.listAllDC)))*100
    percCpuLessThan20 = percCpuLessThan20 /float(max(1,len(topology.listAllDC)))*100
    percCpuMoreThan80Core = percCpuMoreThan80Core /float(max(1,len(topology.listDCCore)))*100
    percCpuLessThan20Core = percCpuLessThan20Core /float(max(1,len(topology.listDCCore)))*100
    percCpuMoreThan80Edge = percCpuMoreThan80Edge /float(max(1,len(topology.listDCEdge)))*100
    percCpuLessThan20Edge = percCpuLessThan20Edge /float(max(1,len(topology.listDCEdge)))*100
    
    return bandwidthUsed, CpuUsed, nbVnfsUsed, CostVnfsUsed, percLinksMoreThan80, percLinksLessThan20, percCpuMoreThan80, percCpuLessThan20, bandwidthUsedCore, CpuUsedCore, nbVnfsUsedCore, percLinksMoreThan80Core, percLinksLessThan20Core, percCpuMoreThan80Core, percCpuLessThan20Core, bandwidthUsedEdge, CpuUsedEdge, nbVnfsUsedEdge, percLinksMoreThan80Edge, percLinksLessThan20Edge, percCpuMoreThan80Edge, percCpuLessThan20Edge
                
            
        
#Return informations about the network
#    links residual capacities
#    nodes residual capacities
#    VNFs used vnf[nodelocation][VNFinstance]
#    number of vnf instances deployed
#    link capacity used
#    node capacity used
#    total latency of all demands
def networkUtilization(links, nodes, functions, sfc, allocations, roundNumber = -1):
    #We copy the links in links residual and the nodes in nodes residual
    linksResidual = copy.deepcopy(links)
    nodesResidual = copy.deepcopy(nodes)
    
    vnfUsed = {}
    bwUsed = 0
    nbVnfUsed = 0
    latency = 0
    bwDemand = 0
    
    for s in sfc:
        bwDemand += s.bd
        for i in range(len(s.functions)+1):
            for (u,v) in allocations[s.id]["link"][i] :
                linksResidual[(u,v)][0]-= s.bd*allocations[s.id]["link"][i][(u,v)]
                bwUsed += s.bd*allocations[s.id]["link"][i][(u,v)]
                if(roundNumber>0):
                    linksResidual[(u,v)][0] = round(linksResidual[(u,v)][0], roundNumber)
                if (linksResidual[(u,v)][0]<0):
                    #print("Link < 0 : "+ str(u)+" "+str(v)+"  "+str(linksResidual[(u,v)][0]))
                    linksResidual[(u,v)][0]=0
                latency += links[(u,v)][1]
                
        for i in range(len(s.functions)):
            for u in allocations[s.id]["node"][i]:
                f = s.functions[i]
                if not u in vnfUsed:
                    vnfUsed[u] = {}
                if not f in vnfUsed[u]:
                    nbVnfUsed += 1
                    vnfUsed[u][f] = 1
                nodesResidual[u][0] -= s.bd*functions[f][0]*allocations[s.id]["node"][i][u]
                if(roundNumber>0):
                    nodesResidual[u][0] = round(nodesResidual[u][0], roundNumber)
                if (nodesResidual[u][0]<0):
                    #print("node < 0 : "+ str(u)+"  "+str(nodesResidual[u][0]))
                    nodesResidual[u][0]=0
            
    return linksResidual, nodesResidual, vnfUsed, nbVnfUsed, bwUsed, bwDemand, latency

def bandwithUsed(sfc, allocations):
    bwUsed = 0
    for s in sfc:
        for i in range(len(s.functions)+1):
            for (u,v) in allocations[s.id]["link"][i] :
                bwUsed += s.bd*allocations[s.id]["link"][i][(u,v)]
    return bwUsed

def bandwithAndVnfUsed(sfc, allocations):
    bwUsed = 0
    nbVnfUsed = 0
    vnfUsed = {}
    for s in sfc:
        for i in range(len(s.functions)+1):
            for (u,v) in allocations[s.id]["link"][i] :
                bwUsed += s.bd*allocations[s.id]["link"][i][(u,v)]
    for i in range(len(s.functions)):
        for u in allocations[s.id]["node"][i]:
            f = s.functions[i]
            if not u in vnfUsed:
                vnfUsed[u] = []
            if not f in vnfUsed[u]:
                nbVnfUsed += 1
                vnfUsed[u].append(f)
    return bwUsed, nbVnfUsed

#Return informations about the network
#    links residual capacities
#    nodes residual capacities
# There is no rounding on this one : the goal is not to print or save the information but to control it's validity
def trueResidual(topology, functions, listSlices, allocations):
    #We copy the links in links residual and the nodes in nodes residual
    linksResidual = {}
    nodesResidual = {}
    
    for (u,v) in topology.links:
        linksResidual[(u,v)] = topology.links[(u,v)][0]


    for u in topology.listAllDC:
        nodesResidual[u] = topology.nodes[u][0]
    
    #We decreased the residual capacity of the links and the nodes
    for slice in listSlices:
        for i in range(len(slice.functions)+1):
            for (u,v) in allocations[slice.id]["link"][i] :
                linksResidual[(u,v)]-= slice.bd*allocations[slice.id]["link"][i][(u,v)]
        for i in range(len(slice.functions)):
            for u in allocations[slice.id]["node"][i]:
                nodesResidual[u] -= slice.bd*functions[slice.functions[i]][0]*allocations[slice.id]["node"][i][u]
            
    return linksResidual, nodesResidual

#Return the linksCapacity Used and the number of VNF used
def objective(listAllDC, listSlices, functions, allocation):
    vnf = {}
    objBW = 0
    objVNF = 0
    for u in listAllDC:
        vnf[u] = {}
    for slice in listSlices:
        for i in range (len(allocation[slice.id]["link"])):
            for (u,v) in allocation[slice.id]["link"][i]:
                objBW+=allocation[slice.id]["link"][i][(u,v)]*slice.bd
                    
        for i in range (len(allocation[slice.id]["node"])):
            for u in allocation[slice.id]["node"][i]:
                if(allocation[slice.id]["node"][i][u]>0):
                    vnf[u][slice.functions[i]] = 1
    for n in listAllDC:
        for f in vnf[n]:
            #Nb of VNF * their licence cost
            objVNF+=vnf[n][f]*functions[f][1]
    return objBW, objVNF

def getAvgLatency(topology, listSlices, allocations):
    
    avgLatency = 0.0
    avgLatencyeMBB = 0.0
    nbeMBB = 0.0
    avgLatencymMTC = 0.0
    nbmMTC = 0.0
    avgLatencyuRLLC = 0.0
    nbuRLLC = 0.0
    
    for s in listSlices:
        latency = 0
        for i in range(len(s.functions)+1):
            for (u,v) in allocations[s.id]["link"][i] :
                latency += topology.links[(u,v)][1]
        avgLatency += latency
        if s.type == "eMBB":
            avgLatencyeMBB += latency
            nbeMBB += 1
        elif s.type == "mMTC":
            avgLatencymMTC += latency
            nbmMTC += 1
        else:
            avgLatencyuRLLC += latency
            nbuRLLC += 1
            
    avgLatency = avgLatency / float(max(1, len(listSlices)))
    avgLatencyeMBB = avgLatencyeMBB / float(max(1, nbeMBB))
    avgLatencymMTC = avgLatencymMTC / float(max(1, nbmMTC))
    avgLatencyuRLLC = avgLatencyuRLLC / float(max(1, nbuRLLC))
    
    return avgLatency, avgLatencyeMBB, avgLatencymMTC, avgLatencyuRLLC

#Recupere les variables et les valeurs pour recrer l'allocation d'un ensemble de sfc
#Called by allocILP
def recreateAllocGC(listSfc, namesVar, valsVar):
    allocation = {}
    for s in listSfc :
        allocation[s.id] = {}
        allocation[s.id]["link"]=[]
        allocation[s.id]["node"]=[]
        for i in range(len(s.functions)+1):
            allocation[s.id]["link"].append({})
            if(not i == len(s.functions)):
                allocation[s.id]["node"].append({})
                     
    for i in range(len(namesVar)) :
        if round(valsVar[i], 7) > 0:
            if namesVar[i][0]=='x':
                tmp = namesVar[i].split(",")
                id = tmp[1]
                layer = int(float(tmp[2]))
                src = tmp[3]
                dst = tmp[4]
                if not dst == "dst":
                    if param.integerPath:
                        allocation[id]["link"][layer][(src,dst)] = 1
                    else:   
                        allocation[id]["link"][layer][(src,dst)] = round(valsVar[i], 7)
                                        
            elif namesVar[i][0]=='u':
                tmp = namesVar[i].split(",")
                id = tmp[1]
                layer = int(float(tmp[2]))
                src = tmp[3]
                if param.integerPath:
                    allocation[id]["node"][layer][src] = 1
                else:
                    allocation[id]["node"][layer][src] = round(valsVar[i], 7)
                
    return allocation


#Recupere les variables et les valeurs pour recrer l'allocation d'une sfc
#Called by subprobILP and subprobLP
def recreateOneAllocGC(slice, namesVar, valsVar):
    allocation = {}
    
    allocation["link"]=[]
    allocation["node"]=[]
    for i in range(len(slice.functions)+1):
        allocation["link"].append({})
        if(not i == len(slice.functions)):
            allocation["node"].append({})
                     
    for i in range(len(namesVar)) :
        if round(valsVar[i], 7) > 0:
            """
            if sfc.id == "N15_N30_0":
                print("        {}    {}".format(namesVar[i], valsVar[i]))
            """
            if namesVar[i][0]=='x':
                tmp = namesVar[i].split(",")
                layer = int(float(tmp[1]))
                src = tmp[2]
                dst = tmp[3]
                if not dst == "dst":
                    if param.integerPath:
                        allocation["link"][layer][(src,dst)] = 1
                    else:   
                        allocation["link"][layer][(src,dst)] = round(valsVar[i], 7)
                
            elif namesVar[i][0]=='u':
                tmp = namesVar[i].split(",")
                layer = int(float(tmp[1]))
                src = tmp[2]
                if param.integerPath:
                    allocation["node"][layer][src] = 1
                else:
                    allocation["node"][layer][src] = round(valsVar[i], 7)
                
    return allocation


#Check if there is no mistake in the reconfiguration
def checkStepOfReconfiguration(listSlices, topology, functions, allocations, nbSteps):    
    print("Check Reconf MBB OK")
    errorDetected = False
    for t in range(nbSteps) :
        culmulStep = {}
        for slice in listSlices:
            culmulStep[slice.id] = copy.deepcopy(allocations[t][slice.id])
            if not sameAlloc(allocations[t][slice.id], allocations[t+1][slice.id]):
                for i in range(len(slice.functions)):
                    for l in allocations[t+1][slice.id]['link'][i]:
                        if not l in culmulStep[slice.id]['link'][i]:
                            culmulStep[slice.id]['link'][i][l] = allocations[t+1][slice.id]['link'][i][l]
                        else:
                            culmulStep[slice.id]['link'][i][l] += allocations[t+1][slice.id]['link'][i][l]
                    for n in allocations[t+1][slice.id]['node'][i]:
                        if not n in culmulStep[slice.id]['node'][i]:
                            culmulStep[slice.id]['node'][i][n] = allocations[t+1][slice.id]['node'][i][n]
                        else:
                            culmulStep[slice.id]['node'][i][n] += allocations[t+1][slice.id]['node'][i][n]
                for l in allocations[t+1][slice.id]['link'][len(slice.functions)]:
                    if not l in culmulStep[slice.id]['link'][len(slice.functions)]:
                        culmulStep[slice.id]['link'][len(slice.functions)][l] = allocations[t+1][slice.id]['link'][len(slice.functions)][l]
                    else:
                        culmulStep[slice.id]['link'][len(slice.functions)][l] += allocations[t+1][slice.id]['link'][len(slice.functions)][l]
                    
        lRes, nRes = trueResidual(topology, functions, listSlices, culmulStep)
        for l in lRes:
            if lRes[l] < -0.1:
                print("Error between etape {} and {} : {} {}".format(t, t+1, l, lRes[l][0]))
                errorDetected = True
        for n in nRes:
            if nRes[n] < -0.1:
                print("Error between etape {} and {} : {} {}".format(t, t+1, n, nRes[n][0]))
                errorDetected = True
    return errorDetected


#Return if the alloc is compose of a single path
def isSinglePath(alloc):
    
    adj = {}
    for i in range(len(alloc["link"])):
        for (u,v) in alloc["link"][i]:
            if (u, i) in adj:
                return False
            else:
                adj[(u, i)] = [(v, i)]
    for i in range(len(alloc["node"])):
        if(len(alloc["node"][i]))>1:
            return False
        for u in alloc["node"][i]:
            if (u, i) in adj:
                return False
            else:
                adj[(u, i)] = [(u, i+1)]       
    
    return True
    
