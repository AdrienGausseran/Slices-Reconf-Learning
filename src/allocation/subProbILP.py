
import cplex
from cplex.exceptions import CplexSolverError

from Util import Util
from Util import pathGC


class SubProb(object):

    def __init__(self, topology, functions, slice, beta, nbSteps = -1):
        self.topology = topology
        self.functions = functions
        self.slice = slice
        self.beta = beta
        self.num = 0
        self.keyAllPath = []
        self.nbSteps = nbSteps
        
        #number of the variables for changing the objective with the duals
        self.colObjPath = 0
        self.colObjLink = 0
        self.colObjNode = []
        self.colObjVNF = []
        
        self.prob = cplex.Cplex()
        self.prob.parameters.read.datacheck.set(0)
        
        self.prob.objective.set_sense(self.prob.objective.sense.minimize)
        self.prob.set_results_stream(None)
        
        #    ---------- ---------- ---------- First we build the model
        
        obj = []        #Objective
        ub = []         #Upper Bound
        rhs = []        #Result for each constraint
        sense = []      #Comparator for each constraint
        colname = []    #Name of the variables
        types = []      #type of the variables
        row = []        #Constraint
        #rowname=[]      #Name of the constraints
        numrow = 0
        numcol = 0
        
        frac = 'B'
                        
                
        #Variable only used for the objective : update by the dual
        colname.append("dualPath")
        obj.append(0)
        ub.append(1)
        types.append(frac)
        numcol += 1
        row.append([["dualPath"], [1]])
        #rowname.append("c{}".format(numrow))
        numrow+=1
        sense.append('E')
        rhs.append(1)
        
        
        #And we create the variables for isUse        
        for f in self.slice.functions:
            self.colObjVNF.append(numcol)
            for u in topology.listAllDC:
                colname.append("isUse,{},{}".format(u,f))
                obj.append(beta*functions[f][1])
                ub.append(1)
                types.append(frac)
                numcol += 1
        
        
        #For each layer of the slice
        for i in range(len(slice.functions)):
            self.colObjNode.append(numcol)
            #for each self.nodes
            for u in topology.listAllDC:
                    #We create a variable to know if we use a node for an option
                    colname.append("use,{},{}".format(i,u))
                    obj.append(0)
                    ub.append(1)
                    types.append(frac)
                    numcol +=1
                        
        self.colObjLink = numcol
        #For each layer of the slice
        for i in range(len(slice.functions)+1):
            if (not self.slice.dst == None) or (not i == len(self.slice.functions)):
                #for each arc we create a lp variable
                for (u,v) in self.topology.links:
                    colname.append("x,{},{},{}".format(i,u,v))
                    obj.append(slice.bd)
                    ub.append(1)
                    types.append(frac)
                    numcol+=1
            #When the slice doesn't have a destination, the last layer is not used for routing because the destination is the node used for the last layer
            #Here we only have fake links to a fake node to conserve the flow
            else:
                for u in topology.listAllDC:
                    colname.append("x,{},{},{}".format(i,u,"dst"))
                    obj.append(0)
                    ub.append(1)
                    types.append(frac)
                    
                    
                    
        #Flow conservation constraints
        for i in range(len(slice.functions)+1):
            for u in topology.nodes:
                listVar = []
                listVal = []
                #If the node is a datacenter
                if(u in topology.listAllDC):
                    #If it's the source layer
                    if(i==0):
                        listVar.append("use,{},{}".format(i,u))
                        listVal.append(1)
                        for (n,v) in topology.links :
                            if(u==n):
                                listVar.append("x,{},{},{}".format(i,u,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        numrow+=1
                        sense.append('E')
                        #If u is the source node
                        if (u==slice.src):
                            rhs.append(1)
                        else:
                            rhs.append(0)
                        
                    #If it's the last layer
                    elif(i==(len(slice.functions))):
                        listVar.append("use,{},{}".format(i-1,u))
                        listVal.append(-1)
                        if (not slice.dst == None):
                            for (n,v) in topology.links :
                                if(u==n):
                                    listVar.append("x,{},{},{}".format(i,u,v))
                                    listVal.append(1)
                                elif(u==v):
                                    listVar.append("x,{},{},{}".format(i,n,v))
                                    listVal.append(-1)
                            row.append([listVar, listVal])
                            numrow+=1
                            sense.append('E')
                            #If u is the destination node
                            if (u==slice.dst):
                                rhs.append(-1)
                            else:
                                rhs.append(0)
                        else:
                            listVar.append("x,{},{},{}".format(i,u,"dst"))
                            listVal.append(1)
                            row.append([listVar, listVal])
                            numrow+=1
                            sense.append('E')
                            rhs.append(0)
                            
                    #If it's in a middle layer
                    else :
                        listVar.append("use,{},{}".format(i,u))
                        listVal.append(1)
                        listVar.append("use,{},{}".format(i-1,u))
                        listVal.append(-1)
                        for (n,v) in topology.links :
                            if(u==n):
                                listVar.append("x,{},{},{}".format(i,u,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        numrow+=1
                        sense.append('E')
                        rhs.append(0)
                    
                #If the node is not a datacenter
                else :
                    
                    #If it's the source layer
                    if(i==0):
                        for (n,v) in topology.links :
                            if(u==n):
                                listVar.append("x,{},{},{}".format(i,u,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        numrow+=1
                        sense.append('E')
                        #If u is the source node
                        if (u==slice.src):
                            rhs.append(1)
                        else:
                            rhs.append(0)
                        
                    #If it's the last layer
                    elif(i==(len(slice.functions))):
                        #if the slice does'nt have a dst, the last layer is only fake links
                        if (not slice.dst == None):
                            for (n,v) in topology.links :
                                if(u==n):
                                    listVar.append("x,{},{},{}".format(i,u,v))
                                    listVal.append(1)
                                elif(u==v):
                                    listVar.append("x,{},{},{}".format(i,n,v))
                                    listVal.append(-1)
                            row.append([listVar, listVal])
                            numrow+=1
                            sense.append('E')
                            #If u is the destination node
                            if (u==slice.dst):
                                rhs.append(-1)
                            else:
                                rhs.append(0)
                            
                    #If it's in a middle layer
                    else :
                        for (n,v) in topology.links :
                            if(u==n):
                                listVar.append("x,{},{},{}".format(i,u,v))
                                listVal.append(1)
                            elif(u==v):
                                listVar.append("x,{},{},{}".format(i,n,v))
                                listVal.append(-1)
                        row.append([listVar, listVal])
                        numrow+=1
                        sense.append('E')
                        rhs.append(0)
                        
            #If the slice does not have a destination we finish the flow
            if(slice.dst == None) and (i==(len(slice.functions))):
                listVar = []
                listVal = []
                for u in topology.listAllDC:
                    listVar.append("x,{},{},{}".format(i,u,"dst"))
                    listVal.append(-1)
                row.append([listVar, listVal])
                numrow+=1
                sense.append('E')
                rhs.append(-1)           
                                  
                        
        #Only one node can be use as a function by slice, by layer
        for i in range(len(slice.functions)):
            listVar = []
            listVal = []
            for u in topology.listAllDC:
                listVar.append("use,{},{}".format(i,u))
                listVal.append(1)
            row.append([listVar, listVal])
            #rowname.append("c{}".format(numrow))
            numrow+=1
            sense.append('E')
            rhs.append(1)
            
        
        listVar = []
        listVal = []
        #Latency constraint
        borneMax = len(slice.functions)+1
        if slice.dst == None:
            borneMax -= 1
        for i in range(borneMax):
            for (u,v) in topology.links:
                listVar.append("x,{},{},{}".format(i,u,v))
                listVal.append(self.topology.links[(u,v)][1])
        row.append([listVar, listVal])
        numrow+=1
        sense.append('L')
        rhs.append(slice.latencyMax)
            
            
        #The constraint for isUse
        for u in self.topology.listAllDC:
            for i in range(len(slice.functions)):
                f = slice.functions[i]
                row.append([["isUse,{},{}".format(u,f), "use,{},{}".format(i,u)], [1, -1]])
                #rowname.append("c{}".format(numrow))
                numrow+=1
                sense.append('G')
                rhs.append(0)
                    
        
        
        """
        print("{} constraints".format(numrow))
        print("constraints {}".format(row[1734]))
        exit()
        for r in range(numrow):
            print(r)
            self.prob.linear_constraints.add(lin_expr=[row[r]], senses=[sense[r]], rhs=[rhs[r]], names=[rowname[r]])
        """
        
        self.prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
        self.prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs)

    #When step not = to None it means we use it for the reconfiguration
    def updateObjective(self, duals, constraintOnePath, constraintLinkCapacity, constraintNodeCapacity, constraintVnfUsed, step = None):
        
        
        #print("---Update Obj {}".format(self.slice.id))
        #Updating  with constraintOnePath
        dual = duals[constraintOnePath]
        if dual < 0:
            dual = -dual
        self.prob.objective.set_linear(self.colObjPath, - dual)
        #if self.slice.id == "N39_N30_1":
        #vars = self.prob.variables.get_names()
        #print("    U8 {} onePath {}".format(duals[constraintOnePath], vars[self.colObjPath]))
        
        #Updating  with constraintNodeCapacity
        for i in range(len(self.slice.functions)):
            numcol = self.colObjNode[i]
            for u in self.topology.listAllDC:
                if step == None :
                    dual = duals[constraintNodeCapacity[u]]
                else:
                    dual = duals[constraintNodeCapacity[u][step-1]]
                if dual < 0:
                    dual = -dual
                self.prob.objective.set_linear(numcol, dual * self.slice.bd * self.functions[self.slice.functions[i]][0])
                numcol+=1
                    
                    
        #Updating  with constraintLinkCapacity
        numcol = self.colObjLink
        for i in range(len(self.slice.functions)+1):
            if (not self.slice.dst == None) or (not i == len(self.slice.functions)):
                for (u,v) in self.topology.links:
                    if step == None :
                        dual = duals[constraintLinkCapacity[(u,v)]]
                    else:
                        dual = duals[constraintLinkCapacity[(u,v)][step-1]]
                    if dual < 0:
                        dual = - dual
                    self.prob.objective.set_linear(numcol, self.slice.bd + dual * self.slice.bd)
                    numcol+=1
                
        
        #Updating  with constraintVnfUsed      
        for i in range(len(self.slice.functions)):
            f = self.slice.functions[i]
            numcol = self.colObjVNF[i]
            for u in self.topology.listAllDC:
                dual = duals[constraintVnfUsed[u][f][self.slice.id]]
                if dual < 0:
                    dual = - dual
                if not step == None:
                    if not step == self.nbSteps:
                        dual = 0
                self.prob.objective.set_linear(numcol, dual * self.beta*self.functions[f][1])
                numcol+=1
        
    
    def solve(self, step = None):
        
        """      
        try:
            self.prob.solve()
        except CplexSolverError:
            print("Exception raised during solve")
            return"""
            
        try:
            self.prob.solve()
        except:
            import sys
            print("Exception raised during solve subProbIlp")
            e = sys.exc_info()[0]
            print(e)
            exit()

        if self.prob.solution.get_status() != 101 and self.prob.solution.get_status() != 102 :
            print("No solution available in subProbILP {}".format(self.slice.id))
            return 100, None
        rc = round(self.prob.solution.get_objective_value(),6)
        valsVar = self.prob.solution.get_values()
        namesVar = self.prob.variables.get_names()

        path = None
        if rc < 0:
            alloc = Util.recreateOneAllocGC(self.slice, namesVar, valsVar)        
            path = pathGC.fromAllocTopathGC(alloc, self.num)
            if not path.key in self.keyAllPath:
                self.num +=1
                self.keyAllPath.append(path.key)
            else:
                rc = 100
        
        return rc, path
    
    

        #Used when the first path is already computed, but outside the subproblem
    def addPath(self, listPath):
        for path in listPath:
            self.keyAllPath.append(path.key)
            self.num +=1
        
    def terminate(self):
        self.prob.end()