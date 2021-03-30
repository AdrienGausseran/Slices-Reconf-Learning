import os
from random import shuffle, choice

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import math

from src import param
           
            
            
class Topology(object):
    '''
    classdocs
    '''


    def __init__(self, nodes, links):
        
        #dictNodes["N1] = [capaDC, [listVnfAvaliable], "Edge or Core or BS"]
        #dictLinks["N1","N2"] = [capaLink, latency, "Edge or Core or Connect"]
        
        self.nodes = nodes
        self.links = links
        
        self.listLinksCore = []
        self.listLinksEdge = []
        self.listLinksConnectivity = []
        self.DCCapacity = 0
        self.linksCapacity = 0
        self.listBaseStation = []
        self.listDCCore = []
        self.listDCEdge = []
        self.listAllDC = []
        self.numberLinksToBaseStations = 0
        
        for l in self.links:
            self.linksCapacity += self.links[l][0]
            if self.links[l][2] == "Core":
                self.listLinksCore.append(l)
            elif self.links[l][2] == "Edge":
                self.listLinksEdge.append(l)
            else:
                self.listLinksConnectivity.append(l)
            if self.nodes[l[0]][2]=="BS":
                self.numberLinksToBaseStations += 1
                
        for n in self.nodes:
            if len(self.nodes[n][1])>0:
                self.DCCapacity += self.nodes[n][0]
                if self.nodes[n][2] == "Core":
                    self.listDCCore.append(n)
                    self.listAllDC.append(n)
                elif self.nodes[n][2] == "Edge":
                    self.listDCEdge.append(n)
                    self.listAllDC.append(n)
            elif self.nodes[n][2] == "BS":
                self.listBaseStation.append(n)
        
    
                
    def setSettings(self, capacityCoreLinks, capacityEdgeLinks, capacityConnectivityLinks, capacityCoreDC, capacityEdgeDC, latencyCoreLinks, latencyEdgeLinks, latencyConnectivityLinks):
        
        self.DCCapacity = 0
        self.linksCapacity = 0
        for n in self.listDCCore:
            self.nodes[n][0] = capacityCoreDC
            self.DCCapacity += capacityCoreDC
        for n in self.listDCEdge:
            self.nodes[n][0] = capacityEdgeDC
            self.DCCapacity += capacityEdgeDC
            
        for l in self.listLinksCore:
            self.linksCapacity += capacityCoreLinks
            self.links[l][0] = capacityCoreLinks
            self.links[l][1] = latencyCoreLinks
        for l in self.listLinksEdge:
            self.linksCapacity += capacityEdgeLinks
            self.links[l][0] = capacityEdgeLinks
            self.links[l][1] = latencyEdgeLinks
        for l in self.listLinksConnectivity:
            self.linksCapacity += capacityConnectivityLinks
            self.links[l][0] = capacityConnectivityLinks
            self.links[l][1] = latencyConnectivityLinks
            
            
#Function creating a topology
#    nbCoreNodes       : Number of core nodes
#    nbCoreDCs         : Number of DC inside the core (<= nbCoreNodes)
#    nbEdgeCluster     : Number of Edge cluster (<= nbCoreNodes)
#    nbEdgeNodes       : Number of Nodes in each Edge Cluster
#    nbEdgeDC          : Number of DC in each Edge Cluster (<= nbEdgeNodes)
#    nbBaseStation     : Number of Base Station in each EdgeCluster
#    nbLinksCore       : Number of links in the Core (for each node nbLinksCore >= 2 or (nbLinksCore == 1 if nbCoreNodes == 1))
#    nbLinksEdge       : Number of links in the each Edge (for each node nbLinksEdge >= 2 or (nbLinksEdge == 1 if nbEdgeNodes == 1))
#    nbLinksEdgeToCore : Number of links connecting each Edge to the Core (nbLinksEdgeToCore >= 1 and nbLinksEdgeToCore <= nbEdgeNodes)
def createTopo(nbCoreNodes, nbCoreDCs, nbEdgeCluster, nbEdgeNodes, nbEdgeDC, nbBaseStation, nbLinksCore, nbLinksEdge, nbLinksEdgeToCore, planarNetworks = False):
    listNodesCore = []          # List of Core nodes
    listDCCore = []             # List of Core DC (each DC is also in listNodesCore
    listNodesEdge = []          # List of Edge Networks, each network is a list of edge nodes (can be empty) and correspond to a Core Node
    listDCEdge = []             # List of Edge Networks, each network is a list of DC (each DC is also in listNodesEdge)
    listBaseStation = []        # List of lists of Base stations : each list correspond to an edge network
    
    listLinksCore = []          # List of links inside the Core Network
    listLinksEdge = []          # List of links inside the edge networks (also contains the links between the base stations and the edge nodes
    listLinksConnectivity = []  # List of links connecting the edges to their core node

    #Creation of the Core Network
    for i in range(nbCoreNodes):
        listNodesCore.append("CN{}".format(i))
        
    if planarNetworks:
        listLinksCore = createPlanarMesh(listNodesCore,nbLinksCore)
    else:
        listLinksCore = createMesh(listNodesCore,nbLinksCore)
    
    
    #Selection of the DC inside the Core Network
    nbCoreDCs = min(nbCoreDCs, nbCoreNodes)
    listDCCore = chooseDC(listNodesCore, listLinksCore, nbCoreDCs)

    #For each Core node we initialize the potential edge network
    for i in range(nbCoreNodes):
        listNodesEdge.append([])
        listDCEdge.append([])
        listBaseStation.append([])
        listLinksEdge.append([])
        listLinksConnectivity.append([])
    
    #Validity of nbEdgeCluster and nbLinksEdgeToCore
    nbEdgeCluster = min(nbEdgeCluster, nbCoreNodes)
    nbLinksEdgeToCore = max(1,nbLinksEdgeToCore)
    nbLinksEdgeToCore = min(nbLinksEdgeToCore, nbEdgeNodes)

    #We randomly choose witch core node will be linked to an edge network
    listTmpCoreNodes = listNodesCore[:]
    shuffle(listTmpCoreNodes)
    for i in range(nbEdgeCluster):
        indexCoreNode = listNodesCore.index(listTmpCoreNodes[i])

        #Creation of the Edge Network
        for j in range(nbEdgeNodes):
            listNodesEdge[indexCoreNode].append("EN{}C{}".format(j, indexCoreNode))
        if planarNetworks:
            listLinksEdge[indexCoreNode] = createPlanarMesh(listNodesEdge[indexCoreNode],nbLinksEdge)
        else:
            listLinksEdge[indexCoreNode] = createMesh(listNodesEdge[indexCoreNode],nbLinksEdge)
        
        #Selection of the DC inside the Edge Network
        nbEdgeDC = min(nbEdgeNodes, nbEdgeDC)
        listDCEdge[indexCoreNode] = chooseDC(listNodesEdge[indexCoreNode], listLinksEdge[indexCoreNode], nbEdgeDC)
        
        #Adding the Base Stations and their links to the Edge Network
        listBaseStationTmp, listLinksEdgeTmp = createBaseStations2(nbBaseStation, nbEdgeNodes, listNodesEdge, indexCoreNode)
        for bs in listBaseStationTmp:
            listBaseStation[indexCoreNode].append(bs)
        for l in listLinksEdgeTmp:
            listLinksEdge[indexCoreNode].append(l)
        
        
        #Adding the links connecting the Edge Network and the associated Core Node
        #We randomly choose witch edge nodes will be linked to the core node
        listTmpEdgeNodes = listNodesEdge[indexCoreNode][:]
        shuffle(listTmpEdgeNodes)
        for j in range(nbLinksEdgeToCore):
            listLinksConnectivity[indexCoreNode].append((listTmpCoreNodes[i], listTmpEdgeNodes[j]))
    

    return Topology(listNodesCore, listDCCore, listNodesEdge, listDCEdge, listBaseStation, listLinksCore, listLinksEdge, listLinksConnectivity)

#First function to create the BS
def createBaseStations(nbBaseStation, nbEdgeNodes, listNodesEdge, indexCoreNode):
    
    #We link the base station randomly to the edge nodes (we assure that their is not too much base station on one node
    listBaseStation = []
    listLinksEdge = []
    
    maxBS = math.ceil(nbEdgeNodes/2.0)
    maxBS = math.ceil(nbBaseStation/float(maxBS))
    basePerNode = {}
    nbBase = 0
    while nbBase < nbBaseStation:
        nodeTmp = choice(listNodesEdge[indexCoreNode])
        if not nodeTmp in basePerNode:
            basePerNode[nodeTmp] = []
        if len(basePerNode[nodeTmp]) >= maxBS:
            continue
        nodeTmp2 = "BS{}C{}".format(nbBase, indexCoreNode)
        listBaseStation.append(nodeTmp2)
        listLinksEdge.append((nodeTmp,nodeTmp2))

        basePerNode[nodeTmp].append(nodeTmp2)
        nbBase += 1
        
    return listBaseStation, listLinksEdge

#Second function to create the BS
#    Each BS of an edge node is linked to the precedent and the next BS of the same edge node
#    If a edge node has a BS it must have at least 2
def createBaseStations2(nbBaseStation, nbEdgeNodes, listNodesEdge, indexCoreNode):
    
    #We link the base station randomly to the edge nodes (we assure that their is not too much base station on one node
    listBaseStation = []
    listLinksEdge = []
    
    maxBS = math.ceil(nbEdgeNodes/2.0)
    maxBS = math.ceil(nbBaseStation/float(maxBS))
    maxBS = max(2, maxBS)
    
    basePerNode = {}
    nbBase = 0
    while nbBase < nbBaseStation:
        #If we can only put 1 BS we chose a node that have already one
        if nbBase == nbBaseStation-1:
            nodeTmp = choice(list(basePerNode.keys()))
        else:
            nodeTmp = choice(listNodesEdge[indexCoreNode])
        #If it's the first BS for the edge node, we create 2 BS
        if not nodeTmp in basePerNode:
            basePerNode[nodeTmp] = []
            nodeTmp2 = "BS{}C{}".format(nbBase, indexCoreNode)
            listBaseStation.append(nodeTmp2)
            listLinksEdge.append((nodeTmp,nodeTmp2))
            basePerNode[nodeTmp].append(nodeTmp2)
            nbBase += 1
        if len(basePerNode[nodeTmp]) >= maxBS:
            continue
        nodeTmp2 = "BS{}C{}".format(nbBase, indexCoreNode)
        listBaseStation.append(nodeTmp2)
        listLinksEdge.append((nodeTmp,nodeTmp2))
        #We also link the base station with the precedent base station of this edge node
        if len(basePerNode[nodeTmp]) > 0:
            listLinksEdge.append((basePerNode[nodeTmp][len(basePerNode[nodeTmp])-1],nodeTmp2))
        
        basePerNode[nodeTmp].append(nodeTmp2)
        nbBase += 1
        
    return listBaseStation, listLinksEdge

#Function linking the nodes
#    listNodes        : List of Nodes to link
#    nbLinksByNode    : Number of links (at least 2 by node)
def createMesh(listNodes, nbLinks):
    #If there are only two nodes there is only 1 link
    if len(listNodes) == 2:
        return [(listNodes[0], listNodes[1])]
    #There can't be more links than all to all
    tmp = ((len(listNodes)-1)*len(listNodes))/2.0
    if nbLinks > tmp:
        nbLinks = tmp
    
    listLinks = []
    dictLink = {}
    for node in listNodes:
        dictLink[node] = []
    #We fist randomly connect each node with 2 links
    for node in listNodes:
        while len(dictLink[node])<2:
            tmp = choice(listNodes)
            if (not tmp == node) and (not tmp in dictLink[node]):
                dictLink[node].append(tmp)
                dictLink[tmp].append(node)
                if listNodes.index(node) < listNodes.index(tmp):
                    listLinks.append((node,tmp))
                else:
                    listLinks.append((tmp,node))
                
    #Then for all the remaining links we connect them randomly
    while(len(listLinks)<nbLinks):
        tmp = choice(listNodes)
        tmp2 = choice(listNodes)
        if (not tmp == tmp2) and (not tmp in dictLink[tmp2]):
            dictLink[tmp2].append(tmp)
            dictLink[tmp].append(tmp2)
            if listNodes.index(tmp2) < listNodes.index(tmp):
                listLinks.append((tmp2,tmp))
            else:
                listLinks.append((tmp,tmp2))
        
    return listLinks


#Function linking the nodes
#    listNodes        : List of Nodes to link
#    nbLinksByNode    : Number of links (at least 2 by node)
def createPlanarMesh(listNodes, nbLinks):
    return
    #If there are only two nodes there is only 1 link
    if len(listNodes) == 2:
        return [(listNodes[0], listNodes[1])]
    #There can't be more links than all to all
    tmp = ((len(listNodes)-1)*len(listNodes))/2.0
    if nbLinks > tmp:
        nbLinks = tmp
    
    listLinks = []
    dictLink = {}
    for node in listNodes:
        dictLink[node] = []
    #We fist connect each node the previous and the next
    for i in range(len(listNodes)):
        node1 = listNodes[i]
        node2 = listNodes[(i+1)% len(listNodes)]
        dictLink[node1].append(node2)
        dictLink[node2].append(node1)
        if i < (i+1)% len(listNodes):
            listLinks.append((node1,node2))
        else:
            listLinks.append((node2,node1))
                
    #Then for all the remaining links we connect them randomly
    while(len(listLinks)<nbLinks):
        tmp = choice(listNodes)
        tmp2 = choice(listNodes)
        if (not tmp == tmp2) and (not tmp in dictLink[tmp2]):
            dictLink[tmp2].append(tmp)
            dictLink[tmp].append(tmp2)
            if listNodes.index(tmp2) < listNodes.index(tmp):
                listLinks.append((tmp2,tmp))
            else:
                listLinks.append((tmp,tmp2))
        
    return listLinks


#Function that choose the DC of a network (considering the connection)
#    listNodes        : List of Nodes
#    listLinks        : List of Links
#    nbDC             : Number of datacenters to choose
def chooseDC(listNodes, listLinks, nbDC):
    nbLinks = []
    listDC = []
    #We count the number of links for each node
    for node in listNodes:
        nb = 0
        for link in listLinks:
            if node in link:
                nb += 1
        nbLinks.append((node,nb))
    #We shuffle and then sort the list
    shuffle(nbLinks)
    nbLinks = sorted(nbLinks,key=getSecondOfTuple)
    #We choose the DC
    i = len(nbLinks)-1
    while len(listDC)<nbDC and i >= 0:
        listDC.append(nbLinks[i][0])
        i -= 1
        
    return listDC


def saveTopology(pathToInstanceFolder, name, topology):
    file_to_open = os.path.join(pathToInstanceFolder, "instances")
    file_to_open = os.path.join(file_to_open, "topology")
    file_to_open = os.path.join(file_to_open, name)
    file = open(file_to_open+".txt", 'w')
    
    #Saving the nodes
    file.write("Nodes{\n")
    #First we save the Core nodes
    for node in topology.listNodesCore:
        if node in topology.listDCCore:
            file.write("    {}>DC\n".format(node))
        else:
            file.write("    {}\n".format(node))
    file.write("\n")
    #Then we save the Edge nodes
    for i in range(len(topology.listNodesCore)):
        file.write("    -\n")
        for node in topology.listNodesEdge[i]:
            if node in topology.listDCEdge[i]:
                file.write("    {}>DC\n".format(node))
            else:
                file.write("    {}\n".format(node))
    file.write("\n")
    #Finally we save the base stations
    for i in range(len(topology.listNodesCore)):
        file.write("    +\n")
        for node in topology.listBaseStation[i]:
            file.write("    {}\n".format(node))
    file.write("}\n")
    
    #Saving the links
    file.write("Links{\n")
    #First we save the Core links
    for (u,v) in topology.listLinksCore:
        file.write("    {}:{}\n".format(u,v))
    file.write("\n")
    #Then we save the Edge nodes
    for i in range(len(topology.listNodesCore)):
        file.write("    -\n")
        for (u,v) in topology.listLinksEdge[i]:
            file.write("    {}:{}\n".format(u,v))
    file.write("\n")
    #Finally we save the Core/Edge links
    for i in range(len(topology.listNodesCore)):
        file.write("    +\n")
        for (u,v) in topology.listLinksConnectivity[i]:
            file.write("    {}:{}\n".format(u,v))
    file.write("}\n")
    
    file.close()
    print("    Topology {} created".format(name))
    

def loadTopologyNew(path, name, listFunctions):
    fileToOpen = os.path.join(path, "instances")
    fileToOpen = os.path.join(fileToOpen, "topology")
    fileToOpen = os.path.join(fileToOpen, name)
    fileToOpen = os.path.join(fileToOpen, "{}.txt".format(name))
    """
    listNodesCore = []          # List of Core nodes
    listDCCore = []             # List of Core DC (each DC is also in listNodesCore
    listNodesEdge = []          # List of Edge Networks, each network is a list of edge nodes (can be empty) and correspond to a Core Node
    listDCEdge = []             # List of Edge Networks, each network is a list of DC (each DC is also in listNodesEdge)
    listBaseStation = []        # List of lists of Base stations : each list correspond to an edge network
    
    listLinksCore = []          # List of links inside the Core Network
    listLinksEdge = []          # List of list of links inside the edge networks (also contains the links between the base stations and the edge nodes
    listLinksConnectivity = []  # List of list of links connecting the edges to their core node
    """
    nodes = {}
    links = {}
    
    NodePart = False
    LinkPart = False
    partie = 0
    iteratorEdgeNetwork = -1
    
        
    with open(fileToOpen, "r") as f:
        for line in f :
            
                
            #Nodes part
            if NodePart:
                if line[0] == "}":
                    NodePart = False
                    partie = 0
                elif line == "\n":
                    """
                    if partie == 1 :
                        #For each Core node we initialize the potential edge network
                        for i in range(len(listNodesCore)):
                            listNodesEdge.append([])
                            listDCEdge.append([])
                            listBaseStation.append([])
                            listLinksEdge.append([])
                            listLinksConnectivity.append([])
                    """
                    partie += 1
                    iteratorEdgeNetwork = -1
                    continue
                else:
                    line = line.replace("    ", "")
                    line = line.replace("\n", "")
                #Core part
                if partie == 1:
                    line = line.split(">")
                    """listNodesCore.append(line[0])"""
                    #DataCenter
                    if len(line) > 1:
                        """listDCCore.append(line[0])"""
                        nodes[line[0]] = [1000]
                        tmp = []
                        for vnf in listFunctions:
                            tmp.append(vnf)
                        nodes[line[0]].append(tmp)
                    else:
                        nodes[line[0]] = [0, []]
                    nodes[line[0]].append("Core")
                        
                #Edge part
                elif partie == 2:
                    if line[0] == '-':
                        iteratorEdgeNetwork += 1
                        continue
                    line = line.split(">")
                    """listNodesEdge[iteratorEdgeNetwork].append(line[0])"""
                    #DataCenter
                    if len(line) > 1:
                        """listDCEdge[iteratorEdgeNetwork].append(line[0])"""
                        nodes[line[0]] = [1000]
                        tmp = []
                        for vnf in listFunctions:
                            tmp.append(vnf)
                        nodes[line[0]].append(tmp)
                    else:
                        nodes[line[0]] = [0, []]
                    nodes[line[0]].append("Edge")
                    
                #BS part
                elif partie == 3:
                    if line[0] == '+':
                        iteratorEdgeNetwork += 1
                        continue
                    """listBaseStation[iteratorEdgeNetwork].append(line)"""
                    nodes[line] = [0, []]
                    nodes[line].append("BS")
                    
            
            
            #Links part
            elif LinkPart:
                if line[0] == "}":
                    LinkPart = False
                    partie = 0
                elif line == "\n":
                    partie += 1
                    iteratorEdgeNetwork = -1
                    continue
                else:
                    line = line.replace("    ", "")
                    line = line.replace("\n", "")
                    
                #dictLinks["N1","N2"] = [capaLink, latency, "Edge or Core or Connect"]
                    
                    
                #Core part
                if partie == 1:
                    line = line.split(":")
                    """listLinksCore.append((line[0],line[1]))"""
                    links[(line[0],line[1])] = [0, 0, "Core"]
                    links[(line[1],line[0])] = [0, 0, "Core"]
                #Edge part
                elif partie == 2:
                    if line[0] == '-':
                        iteratorEdgeNetwork += 1
                        continue
                    line = line.split(":")
                    """listLinksEdge[iteratorEdgeNetwork].append((line[0],line[1]))"""
                    links[(line[0],line[1])] = [0, 0, "Edge"]
                    links[(line[1],line[0])] = [0, 0, "Edge"]
                #Core/Edge part
                elif partie == 3:
                    if line[0] == '+':
                        iteratorEdgeNetwork += 1
                        continue
                    line = line.split(":")
                    """listLinksConnectivity[iteratorEdgeNetwork].append((line[0],line[1]))"""
                    links[(line[0],line[1])] = [0, 0, "Connect"]
                    links[(line[1],line[0])] = [0, 0, "Connect"]
                    

            else:
                if line[0] == "N":
                    NodePart = True
                    partie = 1
                    iteratorEdgeNetwork = -1
                elif line[0] == "L":
                    LinkPart = True
                    partie = 1
                    iteratorEdgeNetwork = -1
                    
    f.close()
    
    return Topology(nodes, links)

def loadTopologyOld(path, name, listFunctions, capacityInfiny = -1):
    fileToOpen = os.path.join(path, "instances")
    fileToOpen = os.path.join(fileToOpen, "topologyOld")
    fileToOpen = os.path.join(fileToOpen, name)
    fileToOpen = os.path.join(fileToOpen, "{}.txt".format(name))
    
    nodes = {}
    links = {}
    nodePart = False
    linkPart = False
    
    with open(fileToOpen, "r") as f:
        for line in f :
               
            
            #We save the nodes
            if(nodePart):
                if(line==")\n"):
                    nodePart = False
                    continue
                line = line.replace("  ", "")
                nodeid=line[:line.find("(")-1]
                mySubString=line[line.find("(")+2:line.find(")")-1]
                #We collect the node
                nodes[nodeid] = []
                #We collect the capacity
                capacity = int(mySubString)
                if(capacity > 0 and capacityInfiny > -1):
                    nodes[nodeid].append(capacityInfiny)
                else:  
                    nodes[nodeid].append(int(mySubString))
                line=line[line.find("[")+2:line.find("]")-1]
                tmpFunction = line.split(" ")
                #We collect the functions
                nodes[nodeid].append([])
                if nodes[nodeid][0] > 0:
                    """for i in range(len(tmpFunction)):
                        if(tmpFunction[i]!=''):
                            nodes[nodeid][1].append(tmpFunction[i])"""
                    for vnf in listFunctions:
                        nodes[nodeid][1].append(vnf)
                nodes[nodeid].append("Core")
                
                        
            #We save the links
            elif(linkPart):
                if(line==")\n"):
                    linkPart = False
                    break
                mySubString=line[line.find("(")+2:line.find(")")-1]
                #We save the source and the destination
                tmp=mySubString.split(" ")
                node1 = tmp[0]
                node2 = tmp[1]
                links[(node1, node2)]=[]
                #We save the capacity and the delay
                line = line[line.find(")")+1:]
                line = line.replace(' ( ','')
                line = line.replace(' )\n','')
                tmp=line.split(" ")
                if(capacityInfiny > -1):
                    capacity = capacityInfiny
                else:  
                    capacity = int(tmp[0])
                delay = float(tmp[1])
                links[(node1, node2)].append(capacity)
                links[(node1, node2)].append(delay)
                links[(node1, node2)].append("Core")
                #We save the link in the other way
                links[(node2, node1)]=[]
                links[(node2, node1)].append(capacity)
                links[(node2, node1)].append(delay)
                links[(node2, node1)].append("Core")
                
                
            else:
                if(line=="NODES (\n"):
                    nodePart = True
                elif(line=="LINKS (\n"):
                    linkPart = True
                else:
                    continue
            
    f.close()
    
    #return Topology(nodes, links)
    return nodes, links
        
        
#Show the topology using networkX
#    Dark Red       : Core Nodes
#    Red            : Core Datacenter
#    Cyan           : Edge Nodes
#    Dark Blue      : Edge Datacenter
#    Green          : Base Stations
def showTopology(topology):
    
    G =  nx.Graph()
    listColor = []
    for u in topology.nodes:
        G.add_node(u)
        if topology.nodes[u][2] == "Core":
            
            if u in topology.listDCCore:
                listColor.append("red")
            else:
                listColor.append("darkred")
            
        elif topology.nodes[u][2] == "Edge":
            
            if u in topology.listDCEdge:
                listColor.append("blue")
            else:
                listColor.append("cyan")
            
        else:
            listColor.append("green")
                  
    for (u,v) in topology.links:
        G.add_edge(u, v)
        
    nx.draw_kamada_kawai(G, node_color=listColor)
    plt.show()

    
    
#Show the topology usage using networkX
#    Dark Red       : Core Nodes
#    Red            : Core Datacenter
#    Cyan           : Edge Nodes
#    Dark Blue      : Edge Datacenter
#    Green          : Base Stations
def showTopologyUsage(topology, linksUsage, nodesUsage, name):
    
    G =  nx.DiGraph()
    vmin = 0
    vmax = 100
    
    
    cdict = {'red':   ((0.0, 0.0, 0.0),
                       (0.5, 0.0, 0.0),
                       (1.0, 1.0, 1.0)),
             'blue':  ((0.0, 0.0, 0.0),
                       (1.0, 0.0, 0.0)),
             'green': ((0.0, 0.0, 1.0),
                       (0.5, 0.0, 0.0),
                       (1.0, 0.0, 0.0))}
    
    cmap = mcolors.LinearSegmentedColormap('my_colormap', cdict, 100)
    
    #cmap = plt.cm.plasma
    listNodeCore = []
    listDCCore = []
    listDCCoreColor = []
    listNodeEdge = []
    listDCEdge = []
    listDCEdgeColor = []
    listBS = []
    listBSColor = []
    listLink = []
    listLinksColor = []
    for u in topology.nodes:
        G.add_node(u)
        
        if topology.nodes[u][2] == "Core":
            
            if u in topology.listDCCore:
                listDCCore.append(u)
                usage = 0
                if u in nodesUsage:
                    usage = (nodesUsage[u])/float(topology.nodes[u][0])*100.0
                listDCCoreColor.append(usage)
            else:
                listNodeCore.append(u)
            
        elif topology.nodes[u][2] == "Edge":
            
            if u in topology.listDCEdge:
                listDCCore.append(u)
                usage = 0
                if u in nodesUsage:
                    usage = (nodesUsage[u])/float(topology.nodes[u][0])*100.0
                listDCEdgeColor.append(usage)
            else:
                listNodeEdge.append(u)
            
        else:
            listBS.append(u)
            listBSColor.append("black")
        

                
    for (u,v) in topology.links:
        G.add_edge(u, v)
        listLink.append((u,v))
        usage = 0
        if (u,v) in linksUsage:
            usage = (linksUsage[(u,v)])/float(topology.links[(u,v)][0])*100.0
        listLinksColor.append(usage)



        
    #nx.draw_kamada_kawai(G, node_shape=listNodesShape, node_color=listNodesColor, node_cmap=cmap , edge_color=listLinksColor, edge_cmap=cmap, arrowstyle="->")
    #nx.draw_kamada_kawai(G, node_shape=listNodesShape, node_color=listNodesColor, arrowstyle="->")
    
    pos = nx.layout.kamada_kawai_layout(G, scale=3)
    
    nx.draw_networkx_nodes(G,pos,node_shape = "P", node_size = 400, nodelist = listNodeCore, node_color=["grey" for i in range(len(listNodeCore))])
    nx.draw_networkx_nodes(G,pos,node_shape = "P", node_size = 400, cmap = cmap, nodelist = listDCCore, node_color=listDCCoreColor, vmin=vmin, vmax=vmax)
    nx.draw_networkx_nodes(G,pos,node_shape = "o", nodelist = listNodeEdge, node_color=["grey" for i in range(len(listNodeEdge))])
    nx.draw_networkx_nodes(G,pos,node_shape = "o", cmap = cmap, nodelist = listDCEdge, node_color=listDCEdgeColor, vmin=vmin, vmax=vmax)
    nx.draw_networkx_nodes(G,pos,node_shape = "1", node_size = 500, nodelist = listBS, node_color=["grey" for i in range(len(listBS))])
    nx.draw_networkx_labels(G,pos, labels = {n:chr(9608)*len(n) for n in topology.nodes}, font_size=8.0, font_weight='bold', font_color="white", alpha = 0.85)
    nx.draw_networkx_labels(G,pos, labels = {n:n for n in topology.nodes}, font_size=8.0, font_weight='bold', font_color="black")
    
    nx.draw_networkx_edges(G,pos, edgelist=listLink, edge_cmap=cmap, edge_color=listLinksColor, edge_vmin=vmin, edge_vmax=vmax, width=1.25, arrows=True, arrowsize=8.0, arrowstyle='->', connectionstyle='arc3,rad=0.1')
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin = vmin, vmax=vmax))
    sm._A = []
    cbar = plt.colorbar(sm)
    plt.title(name)
    #cbar.setlabel("Ressoures Utilization")
    plt.show()
    
    
        
def getSecondOfTuple(item):
    return item[1]

if __name__ == '__main__':
    
    nbCoreNodes = 8
    nbCoreDCs=3
    nbEdgeCluster=5
    nbEdgeNodes=6
    nbEdgeDC=3
    nbBaseStation=10
    nbLinksCore = 14
    nbLinksEdge = 9
    nbLinksEdgeToCore = 2
    
    nbCoreNodes = 5
    nbCoreDCs=2
    nbEdgeCluster=3
    nbEdgeNodes=4
    nbEdgeDC=2
    nbBaseStation=6
    nbLinksCore = 7
    nbLinksEdge = 5
    nbLinksEdgeToCore = 2
    
    nbCoreNodes = 5
    nbCoreDCs=2
    nbEdgeCluster=3
    nbEdgeNodes=5
    nbEdgeDC=2
    nbBaseStation=6
    nbLinksCore = 7
    nbLinksEdge = 8
    nbLinksEdgeToCore = 2

    #topo = createTopo(nbCoreNodes, nbCoreDCs, nbEdgeCluster, nbEdgeNodes, nbEdgeDC, nbBaseStation, nbLinksCore, nbLinksEdge, nbLinksEdgeToCore, planarNetworks = False)
    
    #name = "Topo_{}_{}_{}_{}_{}_{}_{}_{}_{}-2".format(8,3,5,6,3,10,14,9,2)
    #name = "Topo_{}_{}_{}_{}_{}_{}_{}_{}_{}".format(nbCoreNodes,nbCoreDCs,nbEdgeCluster,nbEdgeNodes,nbEdgeDC,nbBaseStation,nbLinksCore,nbLinksEdge,nbLinksEdgeToCore)
    #saveTopology("../..", name, topo)
    
    #topo = loadTopologyNew("../..", "TopoTest4", ["F1"])
    nodes, links = loadTopologyOld("../..", "ta1", ["F1"])
    topo = Topology(nodes, links)
    showTopology(topo)

    
    #topo2 = loadTopology("../..", "tmp")
    