
class PathGC(object):

    def __init__(self, num, alloc, nbLinks, nodesUsed, key = None):
        self.num = num
        self.alloc = alloc
        self.nbLinks = nbLinks
        self.nodesUsed = nodesUsed
        self.key = key
        
    def __repr__(self):
        return self.key
        
def fromAllocTopathGC(alloc, num):
    nbLinks = {}
    nodesUsed = []  
    key = ""
    

    for i in range(len(alloc["node"])):
        listL = list(list(alloc["link"][i].keys()))
        listL.sort()
        tmp = list(alloc["node"][i].keys())[0]
        key +=str(tmp)
        for (u,v) in listL:
            nbLinks[(u,v)] = nbLinks.get((u,v),0) + 1
            key += u+"-"+v
        nodesUsed.append(tmp)
    listL = list(alloc["link"][len(alloc["link"])-1].keys())
    listL.sort()
    #key += str(len(alloc["link"][len(alloc["link"])-1]))
    for (u,v) in listL:
        nbLinks[(u,v)] = nbLinks.get((u,v),0) + 1
        key += u+"-"+v
    """
    
    for i in range(len(alloc["link"])):
        for (u,v) in alloc["link"][i]:
            nbLinks[(u,v)] = nbLinks.get((u,v),0) + 1
          
    for i in range(len(alloc["node"])):
        nodesUsed.append(alloc["node"][i].keys()[0])

    """
    
    return PathGC(num, alloc, nbLinks, nodesUsed, key)

def maxAllocForPaths(alloc, listPathGC):
    
    if len(listPathGC)<2:
        return [1.0]
    val = 0.0
    return []
    """
    listVal = []
    for p in listPathGC:
        minVal = 1.0 - val
        for layer in range(len(p.alloc["link"])):
            for l in p.alloc["link"][layer]:
                minVal = min(minVal, alloc["link"][layer][l])
        for layer in range(len(p.alloc["node"])):
            for u in p.alloc["node"][layer]:
                minVal = min(minVal, alloc["node"][layer][u])
        val += minVal
        p.valAlloc = minVal
        if val >= 1.0:
            break
        else:
            for layer in range(len(p.alloc["link"])):
                for l in p.alloc["link"][layer]:
                    alloc["link"][layer][l] -= minVal
            for layer in range(len(p.alloc["node"])):
                for u in p.alloc["node"][layer]:
                    alloc["node"][layer][u] -= minVal
    """
        