
import cplex
from cplex.exceptions import CplexSolverError

from Util import Util
from Util import pathGC


#If ObjBandwitch the objective will be to minimize to bandwdith, if false it will be to minimize the delay
#nodeFunction : if != empty it's the Function that are already used on some nodes
def findAllocation(topology, nodesUsage, linksUsage, listSlices, functions, nodeFunction, beta, timeLimit = 1000, optimalNeeded = False, infinitLinksCapacity = False, infinitCpuCapacity = False, infinitLatency = False, priceOfLinks = None, priceOfNodes = None):
    
    prob = cplex.Cplex()
    prob.parameters.read.datacheck.set(0)
    
    prob.objective.set_sense(prob.objective.sense.minimize)
    prob.set_results_stream(None)
    
    if priceOfLinks == None:
        priceOfLinks = {}
    if priceOfNodes == None:
        priceOfNodes = {}
    
    #    ---------- ---------- ---------- First we build the model
    
    obj = []        #Objective
    ub = []         #Upper Bound
    rhs = []        #Result for each constraint
    sense = []      #Comparator for each constraint
    colname = []    #Name of the variables
    types = []      #type of the variables
    row = []        #Constraint
    rowname=[]      #Name of the constraints
    numrow = 1
    

    fractional = False
    if(not fractional):
        frac = 'B'
    else:
        frac = 'C'
        
                    
                 
    #We create a matrix to know which Function a node can have
    #And we create the variables for isUse
    for u in topology.listAllDC:
        for f in functions:
            colname.append("isUse,{},{}".format(u,f))
            obj.append(beta*functions[f][1])
            ub.append(1)
            types.append('B')
            if u in nodeFunction.keys():
                if f in nodeFunction[u].keys():
                    row.append([["isUse,{},{}".format(u,f)], [1]])
                    rowname.append("c{}".format(numrow))
                    numrow+=1
                    rhs.append(nodeFunction[u][f])
                    sense.append("E")
    
    #For each slice
    for s in listSlices:
        #For each layer of the slice
        for i in range(len(s.functions)+1):
            #for each nodes
            for u in topology.listAllDC:
                if(not i == len(s.functions)):
                    #We create a variable to know if we use a node for an option
                    colname.append("use,{},{},{}".format(s.id,i,u))
                    coef = 0
                    if u in priceOfNodes:
                        coef = priceOfNodes[u]
                    obj.append(s.bd*coef)
                    ub.append(1)
                    types.append(frac)
            if (not s.dst == None) or (not i == len(s.functions)):
                #for each arc we create a lp variable
                for (u,v) in topology.links:
                    colname.append("x,{},{},{},{}".format(s.id,i,u,v))
                    coef = 1
                    if (u,v) in priceOfLinks:
                        coef = priceOfLinks[(u,v)]
                    obj.append(s.bd*coef)
                    ub.append(1)
                    types.append(frac)
                    
            #When the slice doesn't have a destination, the last layer is not used for routing because the destination is the node used for the last layer
            #Here we only have fake links to a fake node to conserve the flow
            else:
                for u in topology.listAllDC:
                    colname.append("x,{},{},{},{}".format(s.id,i,u,"dst"))
                    obj.append(0)
                    ub.append(1)
                    types.append(frac)

    
    #Flow conservation constraints
    for s in listSlices:
        for i in range(len(s.functions)+1):
            for u in topology.nodes:
                listVar = []
                listVal = []
                #If the node is a datacenter
                if(u in topology.listAllDC):
                    #If it's the source layer
                    if(i==0):
                        listVar.append("use,{},{},{}".format(s.id,i,u))
                        listVal.append(1)
                        for (n,v) in topology.links :
                            if(u==n):
                                listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{},{}".format(s.id,i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('E')
                        #If u is the source node
                        if (u==s.src):
                            rhs.append(1)
                        else:
                            rhs.append(0)
                        
                    #If it's the last layer
                    elif(i==(len(s.functions))):
                        listVar.append("use,{},{},{}".format(s.id,i-1,u))
                        listVal.append(-1)
                        if (not s.dst == None):
                            for (n,v) in topology.links :
                                if(u==n):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                    listVal.append(1)
                                elif(u==v):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,n,v))
                                    listVal.append(-1)
                            row.append([listVar, listVal])
                            rowname.append("c{}".format(numrow))
                            numrow+=1
                            sense.append('E')
                            #If u is the destination node
                            if (u==s.dst):
                                rhs.append(-1)
                            else:
                                rhs.append(0)
                        else:
                            listVar.append("x,{},{},{},{}".format(s.id,i,u,"dst"))
                            listVal.append(1)
                            row.append([listVar, listVal])
                            rowname.append("c{}".format(numrow))
                            numrow+=1
                            sense.append('E')
                            rhs.append(0)
                            
                            
                    #If it's in a middle layer
                    else :
                        listVar.append("use,{},{},{}".format(s.id,i,u))
                        listVal.append(1)
                        if(s.functions[i-1] in topology.nodes[u][1]):
                            listVar.append("use,{},{},{}".format(s.id,i-1,u))
                            listVal.append(-1)
                        for (n,v) in topology.links :
                            if(u==n):
                                listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{},{}".format(s.id,i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('E')
                        rhs.append(0)
                #If the node is not a datacenter
                else :
                    
                    #If it's the source layer
                    if(i==0):
                        for (n,v) in topology.links :
                            if(u==n):
                                listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{},{}".format(s.id,i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('E')
                        #If u is the source node
                        if (u==s.src):
                            rhs.append(1)
                        else:
                            rhs.append(0)
                        
                    #If it's the last layer
                    elif(i==(len(s.functions))):
                        #if the slice does'nt have a dst, the last layer is only fake links
                        if (not s.dst == None):
                            for (n,v) in topology.links :
                                if(u==n):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                    listVal.append(1)
                                elif(u==v):
                                    listVar.append("x,{},{},{},{}".format(s.id,i,n,v))
                                    listVal.append(-1)
                            row.append([listVar, listVal])
                            rowname.append("c{}".format(numrow))
                            numrow+=1
                            sense.append('E')
                            #If u is the destination node
                            if (u==s.dst):
                                rhs.append(-1)
                            else:
                                rhs.append(0)
                            
                    #If it's in a middle layer
                    else :
                        for (n,v) in topology.links :
                            if(u==n):
                                listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{},{}".format(s.id,i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('E')
                        rhs.append(0)
                        
            #If the slice does not have a destination we finish the flow
            if(s.dst == None) and (i==(len(s.functions))):
                listVar = []
                listVal = []
                for u in topology.listAllDC:
                    listVar.append("x,{},{},{},{}".format(s.id,i,u,"dst"))
                    listVal.append(-1)
                row.append([listVar, listVal])
                rowname.append("c{}".format(numrow))
                numrow+=1
                sense.append('E')
                rhs.append(-1)

    
    #Constraints for links capacity
    for (u,v) in topology.links:
        listVar = []
        listVal = []
        for s in listSlices:
            borneMax = len(s.functions)+1
            if s.dst == None:
                borneMax -= 1
            for i in range(borneMax):
                listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                listVal.append(s.bd)
        row.append([listVar, listVal])
        rowname.append("c{}".format(numrow))
        numrow+=1
        sense.append('L')
        base = topology.links[(u,v)][0]
        if infinitLinksCapacity:
            base = base*10000
        base -= linksUsage.get((u,v),0)
        if base < 0:
            if base < -2:
                print("Capacite de {},{} inferieur a 0 : {}".format(u,v, base))
                exit()
            else:
                base = 0
        rhs.append(base)
    
    
        
    for s in listSlices:
        
        #Only one node can be use as a function by slice, by layer
        for i in range(len(s.functions)):
            listVar = []
            listVal = []
            for u in topology.listAllDC:
                listVar.append("use,{},{},{}".format(s.id,i,u))
                listVal.append(1)
            row.append([listVar, listVal])
            rowname.append("c{}".format(numrow))
            numrow+=1
            sense.append('E')
            rhs.append(1)
        
        listVar = []
        listVal = []
        #Latency constraint
        borneMax = len(s.functions)+1
        if s.dst == None:
            borneMax -= 1
        for i in range(borneMax):
            for (u,v) in topology.links:
                listVar.append("x,{},{},{},{}".format(s.id,i,u,v))
                listVal.append(topology.links[(u,v)][1])
        row.append([listVar, listVal])
        rowname.append("c{}".format(numrow))
        numrow+=1
        sense.append('L')
        if infinitLatency:
            rhs.append(s.latencyMax*1000)
        else:
            rhs.append(s.latencyMax)
        
    
    #Constraints for nodes capacity
    for u in topology.listAllDC:
        listVar = []
        listVal = []
        
        for s in listSlices:
            for i in range(len(s.functions)):
                listVar.append("use,{},{},{}".format(s.id,i,u))
                val = s.bd*functions[s.functions[i]][0]
                listVal.append(val)
        row.append([listVar, listVal])
        rowname.append("c{}".format(numrow))
        numrow+=1
        sense.append('L')
        base = topology.nodes[u][0]
        if infinitCpuCapacity:
            rhs.append(base*10000)
        else:
            base -= nodesUsage.get(u,0)
            if base < 0:
                if base < -2:
                    print("Capacite de {} inferieur a 0 : {}".format(u, base))
                    exit()
                else:
                    base = 0
            rhs.append(base)
        
        #The constraint for isUse
        for f in functions:
            for s in listSlices:
                for i in range(len(s.functions)):
                    if(s.functions[i] == f):
                        row.append([["isUse,{},{}".format(u,f), "use,{},{},{}".format(s.id,i,u)], [1, -1]])
                        rowname.append("c{}".format(numrow))
                        numrow+=1
                        sense.append('G')
                        rhs.append(0)   
    
    
    prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
    
    """print("{} constraints".format(numrow))
    print("constraints {}".format(row[1734]))
    for r in range(numrow):
        print(r)
        #print("{}    {}    {}    {}".format(row[r], sense[r], rhs[r], rowname[r]))
        prob.linear_constraints.add(lin_expr=[row[r]], senses=[sense[r]], rhs=[rhs[r]], names=[rowname[r]])"""
    

    prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs, names=rowname)
    prob.parameters.timelimit.set(timeLimit)
    
    
    """
    if listSlices[0].id == "63_0_BS0C0":
        prob.write("alloc.lp")
        exit()"""
    
    """
    try:
        prob.solve()
    except CplexSolverError:
        print("Exception raised during solve")
        prob.end()
        return False, {}, {}"""
        
    try:
        prob.solve()
    except:
        import sys
        print("Exception raised during solve allocIlp")
        e = sys.exc_info()[0]
        print(e)
        exit()

    if prob.solution.get_status() != 101 and prob.solution.get_status() != 102:
        #print("No solution available")
        prob.end()
        return False, {}, {}
    #TimeLimit
    if optimalNeeded and prob.solution.get_status() == 107:
        #print("No solution available")
        prob.end()
        return False, {}, {}
    
    """if listSlices[0].id == "63_0_BS0C0":
        print(prob.solution.get_objective_value())
        exit()"""
    
    
    valsVar = prob.solution.get_values()
    namesVar = prob.variables.get_names()

    dictPath = {}
    allocation = Util.recreateAllocGC(listSlices, namesVar, valsVar)
    for s in listSlices: 
        path = pathGC.fromAllocTopathGC(allocation[s.id], 0)
        dictPath[s.id] = [path]
        
    prob.end()
    return True, dictPath, allocation
        