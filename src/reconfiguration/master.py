
import cplex
from cplex.exceptions import CplexSolverError
from Util.Util import checkStepOfReconfiguration

import param

class Master(object):

    #dictPath contain all the path
    #dictPathIntitiale contain only the path for the initial alloc and it contain it's value : dictPathIntitiale[s.id] = [(valPath1, path1), (valPath2, path2)]
    #dictPathIntitiale contain multiple path for each slice only if we have fractional paths
    #The paths in dictPathIntitiale are in dictPath
    def __init__(self, topology, functions, listSlices, nbEtapes, beta, dictPath, integral):
        
        #print(beta)
        self.topology = topology
        self.functions = functions
        self.listSlices = listSlices
        self.nbEtapes = nbEtapes
        self.beta = beta
        self.numcol = 0
        self.allPath = {}
        self.nbIter = 0
        self.integral = integral
        
        self.numberOfPathReallyUsed = 0
        
        #Var for reduceNumberOfPath1 and 2
        self.listPathUsed = {}
        self.listNbPathUsed = {}
        self.listPathNbDispo = {}
        for s in listSlices:
            self.listPathUsed[s.id] = []
            self.listNbPathUsed[s.id] = []
            self.listPathNbDispo[s.id] = []
            for t in range(self.nbEtapes+1):
                self.listPathUsed[s.id].append([])
                self.listNbPathUsed[s.id].append({})
                self.listPathNbDispo[s.id].append({})
        
        #Var for reduceNumberOfPath3
        self.listPathBase = {}
        self.listNbPathBase = {}
        for s in listSlices:
            self.listPathBase[s.id] = []
            self.listNbPathBase[s.id] = []
            for t in range(self.nbEtapes+1):
                self.listPathBase[s.id].append([])
                self.listNbPathBase[s.id].append({})
        
        
        #The number of the row for each slice and each constraints for the duals
        self.rowOnePath = {}
        self.rowLinkCapacity = {}
        self.rowNodeCapacity = {}
        self.rowVnfUsed = {}
        
        self.numColToChangeUB = []
            
        
        self.prob = cplex.Cplex()
        
        self.prob.parameters.read.datacheck.set(0)
        
        self.prob.objective.set_sense(self.prob.objective.sense.minimize)
        self.prob.set_results_stream(None)
        self.numrow = 0
        
        #    ---------- ---------- ---------- First we build the model
    
        obj = []        #Objective
        ub = []         #Upper Bound
        rhs = []        #Result for each constraint
        sense = []      #Comparator for each constraint
        colname = []    #Name of the variables
        types = []      #type of the variables
        row = []        #Constraint
        #rowname=[]      #Name of the constraints
 
        self.frac = 'C'
        
        
        #And we create the variables for isUse
        for u in topology.listAllDC:
            self.rowVnfUsed[u] = {}
            for f in functions:
                self.rowVnfUsed[u][f] = {}
                colname.append("isUse,{},{}".format(u,f))
                obj.append(beta*functions[f][1])
                ub.append(cplex.infinity)
                types.append(self.frac)
                self.numColToChangeUB.append(self.numcol)
                self.numcol += 1
        self.lastColUsed = self.numcol
        
        self.initialPath = {}                
        #Variables for the paths used
        for s in listSlices:
            self.initialPath[s.id] = []
            self.rowOnePath[s.id] = []
            self.allPath[s.id] = []
            for t in range(self.nbEtapes+1):
                self.allPath[s.id].append([])
                self.initialPath[s.id].append([])
                for p in dictPath[s.id]:
                    #we create  the variable for the first path
                    colname.append("p,{},{},{}".format(s.id,p.num, t))
                    if t == self.nbEtapes:
                        tmp = 0
                        for l in p.nbLinks:
                            tmp += p.nbLinks[l]
                        for f in functions:
                            if f in s.functions:
                                self.rowVnfUsed[u][f][s.id] = -1
                        obj.append(tmp * s.bd)
                    else:
                        obj.append(0)
                    self.allPath[s.id][t].append((p, self.numcol))
                    self.initialPath[s.id][t].append(self.numcol)
                    self.listPathNbDispo[s.id][t][p.num] = 0.0
                    self.listNbPathBase[s.id][t][p.num] = 0.0
                    self.listNbPathUsed[s.id][t][p.num] = 0.0
                    
                    
                    ub.append(cplex.infinity)
                    types.append(self.frac)
                    self.numColToChangeUB.append(self.numcol)
                    self.numcol += 1
                    
        #Variables integrity between time step
        for s in listSlices:
            for t in range(1, self.nbEtapes+1):
                for p in dictPath[s.id]:
                    #we create  the variable for the first path
                    colname.append("y_p,{},{},{}".format(s.id,p.num, t))
                    obj.append(0)
                    ub.append(cplex.infinity)
                    types.append(self.frac)
                    self.numColToChangeUB.append(self.numcol)
                    self.numcol += 1

        #Constraints for the initial  state
        for s in listSlices:
            #if (s != newslice):
            for i in range (len(dictPath[s.id])-1):
                row.append([["p,{},{},{}".format(s.id,dictPath[s.id][i].num, 0)],[1]])
                #rowname.append("Ini_{}".format(self.numrow))
                self.numrow+=1
                sense.append('E')
                rhs.append(1)

        #Constraints for integrity between time step
        for s in listSlices:
            for p in dictPath[s.id]:
                for t in range(1, self.nbEtapes+1):
                    row.append([["y_p,{},{},{}".format(s.id,p.num, t),"p,{},{},{}".format(s.id,p.num, t)], [1,-1]])
                    #rowname.append("YT_{}".format(self.numrow))
                    self.numrow+=1
                    sense.append('G')
                    rhs.append(0)
                    row.append([["y_p,{},{},{}".format(s.id,p.num, t),"p,{},{},{}".format(s.id,p.num, t-1)], [1,-1]])
                    #rowname.append("YT-1_{}".format(self.numrow))
                    self.numrow+=1
                    sense.append('G')
                    rhs.append(0)
                    
        #Constraints for links capacity
        for (u,v) in topology.links:
            type = topology.links[(u,v)]
            self.rowLinkCapacity[(u,v)] = []
            for t in range(1, self.nbEtapes+1):
                listVar, listVal = [], []
                for s in listSlices:
                    for p in dictPath[s.id]:
                        if((u,v) in p.nbLinks):
                            listVar.append("y_p,{},{},{}".format(s.id,p.num, t))
                            listVal.append(p.nbLinks[(u,v)]*s.bd)
                row.append([listVar, listVal])
                self.rowLinkCapacity[(u,v)].append(self.numrow)    
                self.numrow+=1
                sense.append('L')
                rhs.append(topology.links[(u,v)][0])     

        #Only one path by slice
        for s in listSlices:
            for t in range(self.nbEtapes+1):
                listVar = []
                listVal = []
                for p in dictPath[s.id]:
                    listVar.append("p,{},{},{}".format(s.id,p.num,t))
                    listVal.append(1)
                row.append([listVar, listVal])
                #rowname.append("OnePAth_{}".format(self.numrow)) 
                self.rowOnePath[s.id].append(self.numrow)
                #rowname.append("c{}".format(numrow))
                self.numrow+=1
                sense.append('E')
                rhs.append(1)
            
        #Constraints for nodes capacity
        for u in topology.listAllDC:
            self.rowNodeCapacity[u] = []
            for t in range(1, self.nbEtapes+1):
                listVar = []
                listVal = []
                for s in listSlices:
                    for p in dictPath[s.id]:
                        tmp = 0
                        for i in range(len(s.functions)):
                            if p.nodesUsed[i] == u:
                                tmp += functions[s.functions[i]][0]
                        if tmp > 0 :
                                listVar.append("y_p,{},{},{}".format(s.id,p.num, t))
                                listVal.append(s.bd*tmp)
                            
                row.append([listVar, listVal])
                #rowname.append("NCapa_{}".format(self.numrow)) 
                self.rowNodeCapacity[u].append(self.numrow)
                #rowname.append("c{}".format(numrow))
                self.numrow+=1
                sense.append('L')
                rhs.append(self.topology.nodes[u][0])
        
        #Constraints for vnf Used
        for u in topology.listAllDC: 
            #For each vnf on the DC
            for f in functions:
                #For each slice
                for s in listSlices:
                    index = []
                    for i in range(len(s.functions)):
                        #We save in wich layer the function is used by the slice
                        if s.functions[i] == f:
                            index.append(i)
                    #If the function is used by the slice
                    if not len(index) == 0:
                        for p in dictPath[s.id]:
                            ok = False
                            for i in index:
                                if p.nodesUsed[i] == u:
                                    ok = True
                            #If the path use the vnf
                            if ok:
                                row.append([["isUse,{},{}".format(u,f), "p,{},{},{}".format(s.id,p.num,self.nbEtapes)],[1,-1]])
                            else:
                                row.append([["isUse,{},{}".format(u,f)],[1]])
                            self.rowVnfUsed[u][f][s.id] = self.numrow
                            #rowname.append("isUse_{}".format(self.numrow)) 
                            self.numrow+=1
                            sense.append('G')
                            rhs.append(0)
                
                
        
        
        
        """
        print("{} constraints".format(numrow))
        print("constraints {}".format(row[214]))
        exit()
        
        self.prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
        for r in range(numrow):
            print(r)
            print("{}    {}    {}    {}".format(row[r], sense[r], rhs[r], rowname[r]))
            self.prob.linear_constraints.add(lin_expr=[row[r]], senses=[sense[r]], rhs=[rhs[r]], names=[rowname[r]])
        """
        
        """
        print("{} slice".format(len(listSlices)))
        print("{} Variables".format(len(obj)))
        print("{} constraints".format(len(row)))
        exit()
        """

        
        self.prob.variables.add(obj=obj, types=types, ub=ub, names=colname)
        self.prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs)   
          
            
    
    def solve(self, verbose = False):
        #Set the problem to be an LP, if not Cplex will do it as a MIP for unknowns reasons and we can't have the duals :'(
        self.prob.set_problem_type(0)
        
        try:
            self.prob.solve()
        except:
            import sys
            print("Exception raised during solve master")
            e = sys.exc_info()[0]
            print("e")
            exit()
        
        #self.prob.solve()
        #self.prob.write("master_{}.lp".format(self.nbIter))
        self.nbIter += 1
        
        #Optimal Infeasible
        if self.prob.solution.get_status() == 5:
            #self.prob.solve()
            try:
                self.prob.solve()
            except:
                import sys
                print("Exception raised during solve master2")
                e = sys.exc_info()[0]
                print("e")
                exit()
            if self.prob.solution.get_status() != 1:
                infoError(self.prob.solution.get_status(), 2, self)
                exit()
        elif self.prob.solution.get_status() != 1:
            infoError(self.prob.solution.get_status(), 1, self)
            exit()
        """
        vals = self.prob.solution.get_values()
        vars = self.prob.variables.get_names()
        for i in range(len(vals)):
            if vals[i]!=0:
                print("    {}    {}".format(vars[i], vals[i]))"""
        
        if verbose:        
            print("        Master Reconf obj : {}".format(self.prob.solution.get_objective_value()))
            
        values = self.prob.solution.get_values()
        bases = self.prob.solution.basis.get_basis()[0]
        
        self.numberOfPathReallyUsed = 0
        #Update of the variables used in reduceNumberOPath#
        for s in self.listSlices:
            for t in range(1,self.nbEtapes+1):
                self.numberOfPathReallyUsed += len(self.allPath[s.id][t])
                tmp = []
                tmp2 = []
                for (path,num) in self.allPath[s.id][t]:
                    self.listPathNbDispo[s.id][t][path.num] += 1.0
                    #For reduceNumberOPath1 and 2
                    if(values[num] > 0):
                        tmp.append(path.num)
                        self.listNbPathUsed[s.id][t][path.num] += 1
                    #For reduceNumberOPath3
                    if(bases[num] > 0):
                        tmp2.append(path.num)
                        self.listNbPathBase[s.id][t][path.num] += 1
                        
                self.listPathUsed[s.id][t].append(tmp)  
                self.listPathBase[s.id][t].append(tmp2)    
                  
        return self.prob.solution.get_objective_value()   
        

        
    def solveOpt(self, timelimit = 1000):
        
        """
        for i in range(self.prob.variables.get_num()):
            self.prob.variables.set_upper_bounds(i,1)
        self.prob.solve()
        print(self.prob.solution.get_objective_value())"""
            
        #Set the problem to be an ILP
        self.prob.set_problem_type(1)

        if self.integral:
           
            for i in range(self.prob.variables.get_num()):
                self.prob.variables.set_upper_bounds(i,1)
                self.prob.variables.set_types(i, 'B')
        else:
            for i in range(self.lastColUsed):
                self.prob.variables.set_types(i, 'B')
            for i in range(self.prob.variables.get_num()):
                self.prob.variables.set_upper_bounds(i,1)
                
        """self.prob.write("a.lp")
        self.prob = cplex.Cplex()
        self.prob.read("a.lp")"""
                    
        
        self.prob.parameters.timelimit.set(timelimit)
        self.prob.parameters.mip.tolerances.mipgap.set(0.0001)
        
        try:
            self.prob.solve()
        except:
            import sys
            print("Exception raised during solve master opt")
            e = sys.exc_info()[0]
            print("e")
            exit()
        
        #print(self.prob.solution.get_objective_value())
        """
        val = self.prob.solution.get_values()
        name = self.prob.variables.get_names()
        for i in range(len(val)):
            print("{}    {}".format(name[i], val[i]))
        """
        #print("Master obj Opt: {}".format(self.prob.solution.get_objective_value()))
    
    #addPath
    def addPath(self, path, slice):     
        tmp = 0
        for l in path.nbLinks:
            tmp += path.nbLinks[l]
            
        numVarPath = []
        numVarPathY = []
               
        #We add the path variable and the Y_path variables
        for t in range(1,self.nbEtapes+1):
            self.allPath[slice.id][t].append((path, self.numcol))
            self.listPathNbDispo[slice.id][t][path.num] = 0.0
            self.listNbPathUsed[slice.id][t][path.num] = 0
            self.listNbPathBase[slice.id][t][path.num] = 0
            
            if t < self.nbEtapes:
                self.prob.variables.add(obj=[0], types=[self.frac], ub=[cplex.infinity], names=["p,{},{},{}".format(slice.id,path.num,t)])
            else:
                self.prob.variables.add(obj=[tmp * slice.bd], types=[self.frac], ub=[cplex.infinity], names=["p,{},{},{}".format(slice.id,path.num,t)])
            numVarPath.append(self.numcol)
            self.numColToChangeUB.append(self.numcol)
            self.numcol += 1
            self.prob.variables.add(obj=[0], types=[self.frac], ub=[cplex.infinity], names=["y_p,{},{},{}".format(slice.id,path.num,t)])
            numVarPathY.append(self.numcol)
            self.numColToChangeUB.append(self.numcol)
            self.numcol += 1
                
        rhs = []        #Result for each constraint
        sense = []      #Comparator for each constraint
        row = []        #Constraint
                
        #We add constraints for integrity between time step
        for t in range(1, self.nbEtapes+1):
            row.append([["y_p,{},{},{}".format(slice.id,path.num, t),"p,{},{},{}".format(slice.id,path.num, t)], [1,-1]])
            #rowname.append("YT_{}".format(self.numrow))
            self.numrow+=1
            sense.append('G')
            rhs.append(0)
            if t > 1:
                row.append([["y_p,{},{},{}".format(slice.id,path.num, t),"p,{},{},{}".format(slice.id,path.num, t-1)], [1,-1]])
                #rowname.append("YT-1_{}".format(self.numrow))
                self.numrow+=1
                sense.append('G')
                rhs.append(0)
            
        self.prob.linear_constraints.add(lin_expr=row, senses=sense, rhs=rhs)    
        

        #Updating the constraint for One path taken
        for t in range(1,self.nbEtapes+1):
            self.prob.linear_constraints.set_coefficients(self.rowOnePath[slice.id][t], numVarPath[t-1], 1)
        
        #Updating the constraint for links capacity
        for (u,v) in path.nbLinks:
            for t in range(self.nbEtapes):
                self.prob.linear_constraints.set_coefficients(self.rowLinkCapacity[(u,v)][t], numVarPathY[t], (path.nbLinks[(u,v)]*slice.bd))
        
        #Updating the constraint for nodes capacity and vnf deploiement
        dictTmpVnf = {}
        dictTmpCapa = {}
        for i in range(len(slice.functions)):
            u = path.nodesUsed[i]
            f = slice.functions[i]
            if u in dictTmpCapa:
                dictTmpCapa[u] += self.functions[f][0]
                dictTmpVnf[u].append(f)
            else:
                dictTmpCapa[u] = self.functions[f][0]
                dictTmpVnf[u] = [f]
        for u in dictTmpCapa:
            for t in range(self.nbEtapes):
                self.prob.linear_constraints.set_coefficients(self.rowNodeCapacity[u][t], numVarPathY[t], (dictTmpCapa[u]*slice.bd))
            for f in dictTmpVnf[u]:
                self.prob.linear_constraints.set_coefficients(self.rowVnfUsed[u][f][slice.id], numVarPath[self.nbEtapes-1], -1)

    
    def getDuals(self):
        duals = self.prob.solution.get_dual_values()
        
        """
        varName = self.prob.variables.get_names()
        reduceCost = self.prob.solution.get_reduced_costs()
        print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        for v in range(len(varName)):
            print("{} {}".format(varName[v], reduceCost[v]))
        print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        """
        
        """
        for id in self.allPath:
            print("{} {}".format(id, self.allPath[id][0][0].nodesUsed))
            for f in self.functions:
                for u in self.nodesDC:
                    if f in self.nodesDC[u][1]:
                        if id in self.rowVnfUsed[u][f]:
                            print("{} {} {} {}".format(u, f, id, duals[self.rowVnfUsed[u][f][id]]))
        """
        
        return duals, self.rowOnePath, self.rowLinkCapacity, self.rowNodeCapacity, self.rowVnfUsed

    
    def getResult(self, checkSolution = False):
        
        pathUsed = {}
        dictPath = {}
        
        values = self.prob.solution.get_values()
        
        
        """
        names = self.prob.variables.get_names()
        
        allocation = []
        for t in range(self.nbEtapes + 1):
            allocation.append({})
            for s in self.listSlices:
                allocation[t][s.id] = {}
                allocation[t][s.id]["link"] = []
                allocation[t][s.id]["node"] = []
                pathUsed[s.id] = []
                
                allocation[t][s.id]["link"].append({})
                for i in range(len(s.functions)):
                    allocation[t][s.id]["link"].append({})
                    allocation[t][s.id]["node"].append({})
        for i in range(len(names)):
            if values[i] > 0:
                tmp = names[i].split(",")
                if(tmp[0][0] == 'p'):
                    id = tmp[1]
                    num = int(float(tmp[2]))
                    t = int(float(tmp[3]))
                    if t == self.nbEtapes:
                        print("    {}    {}    {}".format(id, names[i], values[i]))
        """
        roundValue = 8
        if self.integral:
            roundValue = 0
        if checkSolution :
             
            allocation = []
            for t in range(self.nbEtapes + 1):
                allocation.append({})
                for s in self.listSlices:
                    allocation[t][s.id] = {}
                    allocation[t][s.id]["link"] = []
                    allocation[t][s.id]["node"] = []
                    pathUsed[s.id] = []
                    dictPath[s.id] = []
                    
                    allocation[t][s.id]["link"].append({})
                    for i in range(len(s.functions)):
                        allocation[t][s.id]["link"].append({})
                        allocation[t][s.id]["node"].append({})
                        
                    for (path,num) in self.allPath[s.id][t]:
                        flow = round(values[num], roundValue)
                        if(flow > 0):
                            if t == self.nbEtapes :
                                pathUsed[s.id].append(path.num)
                                dictPath[s.id].append(path)
                            flow = round(values[num], roundValue)
                            for i in range(len(path.alloc["link"])):
                                for (u,v) in path.alloc["link"][i]:
                                    allocation[t][s.id]["link"][i][(u,v)] = allocation[t][s.id]["link"][i].get((u,v),0) + (path.alloc["link"][i][(u,v)]*flow)
                            for i in range(len(path.alloc["node"])):
                                for u in path.alloc["node"][i]:
                                    allocation[t][s.id]["node"][i][u] = allocation[t][s.id]["node"][i].get(u,0) + (path.alloc["node"][i][u]*flow)
            checkStepOfReconfiguration(self.listSlices, self.topology, self.functions, allocation, self.nbEtapes)
            allocation = allocation[self.nbEtapes]

        else:
            
            allocation = {}
            for s in self.listSlices:
                allocation[s.id] = {}
                allocation[s.id]["link"] = []
                allocation[s.id]["node"] = []
                pathUsed[s.id] = []
                dictPath[s.id] = []
                
                allocation[s.id]["link"].append({})
                for i in range(len(s.functions)):
                    allocation[s.id]["link"].append({})
                    allocation[s.id]["node"].append({})
            
            
                for (path,num) in self.allPath[s.id][self.nbEtapes]:
                    flow = round(values[num], roundValue)
                    if(flow > 0):
                        #print(values[num])
                        #print(path.alloc)
                        pathUsed[s.id].append(path.num)
                        dictPath[s.id].append(path)
                        flow = round(values[num], roundValue)
                        for i in range(len(path.alloc["link"])):
                            for (u,v) in path.alloc["link"][i]:
                                allocation[s.id]["link"][i][(u,v)] = allocation[s.id]["link"][i].get((u,v),0) + (path.alloc["link"][i][(u,v)]*flow)
                        for i in range(len(path.alloc["node"])):
                            for u in path.alloc["node"][i]:
                                allocation[s.id]["node"][i][u] = allocation[s.id]["node"][i].get(u,0) + (path.alloc["node"][i][u]*flow)

        return allocation, pathUsed, dictPath
    
    def terminate(self):
        self.prob.end()
        
def byTime(elem):
    return elem.timeUsed
def bySecond(elem):
    return elem[1]


def infoError(status, cas, master):
    print("No solution available for the master")
    print("Cas {}".format(cas))
    print("Status : {}".format(status))
    print("Initial")
    for s in master.listSlices:
        print("{}    {}".format(s.id, master.initialPath[s.id][master.nbEtapes]))
    print("All path")
    for s in master.listSlices:
        print("{}    {}".format(s.id, master.allPath[s.id][master.nbEtapes]))
    master.prob.write("prob.lp")
    