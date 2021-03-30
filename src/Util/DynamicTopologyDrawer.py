import matplotlib.pyplot as plt
from matplotlib import style
import matplotlib.colors as mcolors

import networkx as nx

from src import param


class DynamicTopologyDrawer(object):



    def __init__(self,topology):
        self.G=nx.DiGraph()
        self.topology = topology
        fig = plt.figure(figsize=(14, 14))
        net = fig.add_subplot(111)
        plt.ion()
        plt.show()
        

    def draw(self, linksUsage, nodesUsage, name):

        self.G.clear()
        plt.clf()
        

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
        for u in self.topology.nodes:
            self.G.add_node(u)
            
            if self.topology.nodes[u][2] == "Core":
                
                if u in self.topology.listDCCore:
                    listDCCore.append(u)
                    usage = 0
                    if u in nodesUsage:
                        usage = (nodesUsage[u])/float(self.topology.nodes[u][0])*100.0
                    listDCCoreColor.append(usage)
                else:
                    listNodeCore.append(u)
                
            elif self.topology.nodes[u][2] == "Edge":
                
                if u in self.topology.listDCEdge:
                    listDCCore.append(u)
                    usage = 0
                    if u in nodesUsage:
                        usage = (nodesUsage[u])/float(self.topology.nodes[u][0])*100.0
                    listDCEdgeColor.append(usage)
                else:
                    listNodeEdge.append(u)
                
            else:
                listBS.append(u)
                listBSColor.append("black")
            
    
                    
        for (u,v) in self.topology.links:
            self.G.add_edge(u, v)
            listLink.append((u,v))
            usage = 0
            if (u,v) in linksUsage:
                usage = (linksUsage[(u,v)])/float(self.topology.links[(u,v)][0])*100.0
            listLinksColor.append(usage)
    
    
    
            
        #nx.draw_kamada_kawai(self.G, node_shape=listNodesShape, node_color=listNodesColor, node_cmap=cmap , edge_color=listLinksColor, edge_cmap=cmap, arrowstyle="->")
        #nx.draw_kamada_kawai(self.G, node_shape=listNodesShape, node_color=listNodesColor, arrowstyle="->")
        
        pos = nx.layout.kamada_kawai_layout(self.G, scale=3)
        
        nx.draw_networkx_nodes(self.G,pos,node_shape = "P", node_size = 400, nodelist = listNodeCore, node_color=["grey" for i in range(len(listNodeCore))])
        nx.draw_networkx_nodes(self.G,pos,node_shape = "P", node_size = 400, cmap = cmap, nodelist = listDCCore, node_color=listDCCoreColor, vmin=vmin, vmax=vmax)
        nx.draw_networkx_nodes(self.G,pos,node_shape = "o", nodelist = listNodeEdge, node_color=["grey" for i in range(len(listNodeEdge))])
        nx.draw_networkx_nodes(self.G,pos,node_shape = "o", cmap = cmap, nodelist = listDCEdge, node_color=listDCEdgeColor, vmin=vmin, vmax=vmax)
        nx.draw_networkx_nodes(self.G,pos,node_shape = "1", node_size = 500, nodelist = listBS, node_color=["grey" for i in range(len(listBS))])
        nx.draw_networkx_labels(self.G,pos, labels = {n:chr(9608)*len(n) for n in self.topology.nodes}, font_size=8.0, font_weight='bold', font_color="white", alpha = 0.85)
        nx.draw_networkx_labels(self.G,pos, labels = {n:n for n in self.topology.nodes}, font_size=8.0, font_weight='bold', font_color="black")
        
        nx.draw_networkx_edges(self.G,pos, edgelist=listLink, edge_cmap=cmap, edge_color=listLinksColor, edge_vmin=vmin, edge_vmax=vmax, width=1.25, arrows=True, arrowsize=8.0, arrowstyle='->', connectionstyle='arc3,rad=0.1')
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin = vmin, vmax=vmax))
        sm._A = []
        cbar = plt.colorbar(sm)
        plt.title(name)
        #cbar.setlabel("Ressoures Utilization")
        plt.pause(0.001)

