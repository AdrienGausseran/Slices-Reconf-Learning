import time
import os
import math

from allocation import allocILP

from Util import pathGC
from Util import TopologyManager
from Util import Util

import param

def doDynamicAllocCapacity(topology, listArrival, functions):
    nodesUsage, linksUsage = {}, {}
    allocInit = {}
    dictPath = {}
    priceOfLinks = {}
    priceOfNodes = {}
    
    #Creation de l'allocation initiale
    t = time.time()
    listSliceTmp = []
    for slices in listArrival:
        
        allocPossible, dictPathTMP, allocInitTMP = allocILP.findAllocation(topology, linksUsage, nodesUsage, slices, functions, {}, 0, priceOfLinks = priceOfLinks)
        if not allocPossible :
            print("STAWP ALLOC IMPOSSIBLE")
            param.log.error("STAWP ALLOC IMPOSSIBLE")
            return False, None, None, None, None, None, None, None

        for s in slices:
            listSliceTmp.append(s)
            dictPath[s.id] = dictPathTMP[s.id]
            allocInit[s.id] = allocInitTMP[s.id]
            for i in range(len(s.functions)):
                for l in allocInit[s.id]['link'][i]:
                    if l in priceOfLinks:
                        priceOfLinks[l] += 1
                    else:
                        priceOfLinks[l] = 2
                for n in allocInit[s.id]['node'][i]:
                    if n in priceOfNodes:
                        priceOfNodes[n] += 1
                    else:
                        priceOfNodes[n] = 1
        linksUsage, nodesUsage, vnfUsed = Util.utilisationAndVnfUsed(functions, listSliceTmp, allocInit, roundNumber = 8)
    
        

    needBW = 0
    maxDC = 0
    needNode = 0
    vnfUsed = {}
    
    for slices in listArrival:
        for s in slices:
            for i in range(len(s.functions)):
                for l in allocInit[s.id]['link'][i]:
                    needBW += allocInit[s.id]['link'][i][l]*s.bd
                for n in allocInit[s.id]['node'][i]:
                    if(not n in vnfUsed):
                        vnfUsed[n] = []
                    if(not s.functions[i] in vnfUsed[n]):
                        vnfUsed[n].append(s.functions[i])
                    maxDC = max(maxDC, (allocInit[s.id]['node'][i][n]*s.bd*functions[s.functions[i]][0]))
                    needNode += (allocInit[s.id]['node'][i][n]*s.bd*functions[s.functions[i]][0])
            for l in allocInit[s.id]['link'][len(s.functions)]:
                needBW += (allocInit[s.id]['link'][len(s.functions)][l]*s.bd)
    tInitialAlloc = time.time() - t
    
    nbVnfUsed = 0
    for n in vnfUsed:
        nbVnfUsed += len(vnfUsed[n])
    
    return True, allocInit, dictPath, needBW, nbVnfUsed, maxDC, needNode, tInitialAlloc
    

def changeDCCapacity(nodes, needNode, coeff = 1):
    DC = []
    for n in nodes:
        if len(nodes[n][1]) > 0:
            DC.append(n)
    cpuByDC = math.ceil(needNode*(1+(0.1*coeff))/float(len(DC)))
    for n in DC:
        nodes[n][0] = cpuByDC
    

def modifyCapacities(listArrival, nodes, links, functions, allocInit):
    for slices in listArrival:
        for s in slices:
            for i in range(len(s.functions)):
                for l in allocInit[s.id]['link'][i]:
                    links[l][0] += (allocInit[s.id]['link'][i][l]*s.bd)
                for n in allocInit[s.id]['node'][i]:
                    nodes[n][0] += (allocInit[s.id]['node'][i][n]*s.bd*functions[s.functions[i]][0])
            for l in allocInit[s.id]['link'][len(s.functions)]:
                links[l][0] += (allocInit[s.id]['link'][len(s.functions)][l]*s.bd)

def fixCapacities(DC1, links1, DC2, links2, needNode, needBW, maxBwSfc, functions):

    #The ressources we will give
    bwToGive = needBW * 1.6
    cpuToGive = needNode * 1.6
    capaLink = 0.0
    capaNode = 0.0
    nbVnf = 0
    
    links = {}
    DC = {}
    
    minValLink = maxBwSfc
    mulMaxFunction = max(functions[i][0] for i in functions)
    minValDC = minValLink * 2 * mulMaxFunction
    
    tmpLinks = {}
    tmpDC = {}
    restDivideur = 0
    for l in links1:
        #print("    {}    {}    {}".format(l, links1[l][0], links2[l][0]))
        tmpLinks[l] = math.ceil(max((links1[l][0]+links2[l][0])/2.0, minValLink))
        restDivideur = restDivideur + tmpLinks[l]
        tmp = math.ceil(((links1[l][0]+links2[l][0])/2.0)/1)
        links[l] = max(tmp, minValLink)
        capaLink = capaLink + max(tmp, minValLink)
    coeficientToGive = max(0, (bwToGive - capaLink) / float(restDivideur))
    for l in links1:
        tmp = coeficientToGive * tmpLinks[l]
        links[l] = math.ceil(links[l] + tmp)
        capaLink = capaLink + tmp
        #print("    {}        {}".format(l, links[l][0]))
        
        
    #print("")
    restDivideur = 0
    for n in DC1:
        #print("    {}        {}    {}".format(n, DC1[n][0], DC2[n][0]))
        nbVnf += len(DC1[n][1])
        tmpDC[n] = max(((DC1[n][0]+DC2[n][0])/2.0 ), minValDC)
        restDivideur = restDivideur + tmpDC[n]
        tmp = math.ceil(((DC1[n][0]+DC2[n][0])/2.0 )/1.5)
        DC[n] = max(tmp, minValDC)
        capaNode = capaNode + max(tmp, minValDC)
    coeficientToGive = max(0, (cpuToGive - capaNode) / float(restDivideur))
    for n in DC:
        tmp = coeficientToGive * tmpDC[n]
        DC[n] = math.ceil(DC[n] + tmp)
        capaNode = capaNode + tmp
        #print("    {}        {}".format(n, DC[n][0]))
        


    print("")
    print("        NeedBW {}    NeedNode {}".format(needBW, needNode))
    print("        capaLink {}    capaNode {}".format(capaLink, capaNode))
    print("        {}    {}".format(needBW/float(capaLink)*100, needNode/float(capaNode)*100))
        
    return links, DC, capaLink, capaNode, nbVnf

def avgCapa(topoName, functions, listOfArrival, avgNumber = 5):

    nodes, links = TopologyManager.loadTopologyOld("..", topoName, functions, capacityInfiny = 100000000)

    tmpTopo = TopologyManager.Topology(nodes, links)
    DCIt = []
    linksIt = []
    for it in range(avgNumber):
        
        
        listArrival = []
        numTmp = 0
        maxBwSfc = 0
        
        nbToAllocate = param.numberOfSlices[topoName]['Init']
        
        for i in range(numTmp,nbToAllocate + numTmp):
            slices = listOfArrival[i]
            listArrival.append(slices)
            for slice in slices:
                maxBwSfc = max(maxBwSfc, slice.bd)
            
                
        DCTmp1 = {}
        linksTmp1 = {}
        DCTmp2 = {}
        linksTmp2 = {}
        for l in links:
            linksTmp1[l] = [0, 5]
            linksTmp2[l] = [0, 5]
        for n in nodes:
            if(len(nodes[n][1])>0):
                DCTmp1[n] = [0, nodes[n][1]]
                DCTmp2[n] = [0, nodes[n][1]]
                
        linksIt.append(None)
        DCIt.append(None)
        
        """for s in listSfc:
            s.latencyMax *= 2"""
        
        """****************************************************************         Fix Capacities                                                     """
        allocOK, allocInit, dictPath, needBW, nbVnfUsed, maxDC, needNode, tInitialAlloc = doDynamicAllocCapacity(tmpTopo, listArrival, functions)
        modifyCapacities(listArrival, DCTmp1, linksTmp1, functions, allocInit)
        allocOK = False
        nbFois = 1
        while not allocOK:
            changeDCCapacity(nodes, needNode, nbFois)
            allocOK, allocInit, dictPath, aaa, nbVnfUsed, maxDC, bbb, tInitialAlloc = doDynamicAllocCapacity(tmpTopo, listArrival, functions)
            nbFois += 1
        modifyCapacities(listArrival, DCTmp2, linksTmp2, functions, allocInit)
        linksIt[it],  DCIt[it], capaLink, capaNode, nbVnf = fixCapacities(DCTmp1, linksTmp1, DCTmp2, linksTmp2, needNode, needBW, maxBwSfc, functions)
        """////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////                    """  
                
                
        numTmp += nbToAllocate
        
    DC = {}
    capaLink = 0
    capaNode = 0
    for l in links:
        links[l][0] = 0
        for it in range(avgNumber):
            links[l][0] += linksIt[it][l]
        links[l][0] = links[l][0] / float(avgNumber)
        capaLink += links[l][0]
    for n in nodes:
        nodes[n][0] = 0
        if(len(nodes[n][1])>0):
            for it in range(avgNumber):
                nodes[n][0] += DCIt[it][n]
            nodes[n][0] = nodes[n][0] / float(avgNumber)
            nodes[n][0] = nodes[n][0]
            DC[n] = nodes[n]
            capaNode += nodes[n][0]  
            
    return links, nodes, DC, capaLink, capaNode, nbVnf

