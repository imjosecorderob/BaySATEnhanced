# -*- coding: utf-8 -*-
from baysat.dash.satcore.utils import *


class problemTrianFactor:
    def __init__(self,info=None,M=30, Qin=20, SplitIn=True, see_mess=True):
         self.M = M
         self.initial = info
         self.pinitial = PotentialTable()
         self.rela = varpot(Qin,SplitIn,see_mess)
         self.order = []
         self.clusters = []
         self.lqueue  = []
         self.lfloat = []
         self.posvar = dict()
         self.sol = set()
         self.borr = []
         self.child = []
         self.parent = []
         if info:
            self.contradict = info.contradict
         self.evid = set()
         self.toriginalfl = []
         self.Q=Qin
         self.Split=SplitIn
         self.messages_PTF = see_mess


    def start0(self):
            self.pinitial.computefromsimple(self.initial)


    def prior(self, Q = 2, pre = False):
        if pre:
            return
        for x in self.pinitial.unit:
            self.order.append(abs(x))
            t = potdev(x)
            self.lqueue.append(t)
        self.pinitial.unit = set()
        vars = self.pinitial.getvars()
        total = 0
        for K in range(2,Q+1):
            varb = []
            potb = []
            total = 1
            while total >0:
                total = 0
                i=0
                while i < len(self.pinitial.listp):
                    p = self.pinitial.listp[i]
                    if len(p.listvar) == K:
                        for v in p.listvar:
                                deter = p.checkdetermi(v)
                                if deter:
                                    varb.append(v)
                                    potb.append(p)
                                    self.order.append(v)
                                    self.lqueue.append(p)
                                    self.deleted(v,p)
                                    total += 1
                                    break
                    i+= 1
        if self.pinitial.contradict:
            self.contradict = True
        return (varb,potb)


    def deleted(self,v,p):
        bor = []
        tota = set()
        for i in range(len(self.pinitial.listp)):
            q = self.pinitial.listp[i]
            if v in q.listvar:
                if q == p:
                    h = q.delete([v],inplace = False)
                    if h.trivial():
                        bor.append(h)
                else:
                    h = q.combine(p,inplace = False, des= False)
                    h.delete([v], inplace = True)
                    if h.trivial():
                        bor.append(h)
                    if h.contradict():
                        self.annul()
                        print("Contradictory")
                self.pinitial.listp[i] = h
        for q in bor:
            self.pinitial.listp.remove(q)


    def annul(self):
        for i in range(len(self.order)):
            self.lqueue[i].annul()
        self.contradict = True

           
    def insertunit(self,x):
        xp = abs(x)
        nu = set()
        for pos in range(len(self.clusters)):
            if xp in self.clusters[pos]:
                pot = self.lqueue[pos]  
                pot.insertunit(x)
    

    def insertqueuepot(self,p):
            vcl = p.listvar
            if vcl:
                pos = min(map(lambda h: self.posvar[h], vcl))
            else:
                pos = len(self.order)
            pot = self.lqueue[pos]
            pot.listp.append(p)


    def deletein(self, pre = False):
        if self.rela.contradict:
                print("Contradictory")
                self.annul()
                return
        if pre:
            (e,order,new,past)= self.rela.marginalizeset(set(self.order), Q=self.Q,pre = True, order = self.order.copy())
        else:
            (e,order,new,past)= self.rela.marginalizeset(self.rela.getvars(), Q=self.Q,pre = False)
        self.contradict =  self.rela.contradict
        if not pre:
            self.order = self.order +  order
        i=0
        if not self.contradict:
            for x in past:
                i+=1
                y = nodeTable([])
                for t in x:
                    y.combine(t,inplace= True)
                self.lqueue.append(y)
        return e                
            
    
    def delete(self):
        for i in range(len(self.order)):
            if self.initial.contradict:
                break
            var = self.order[i]
            pot = self.lqueue[i]
            if pot.contradict:
                self.initial.contradict=True
                print("Contradiction before normalizing ")
                break
            potn = pot.marginalize(var)
            # print("Marginalize end")
            pos = self.parent[i]
            poti = self.lqueue[pos]
            poti.insert(potn)
            # print("combine end")


    def insert(self,pot):
        for x in pot.unit:
                self.insertunit(x)
        for p in pot.listp:
                self.insertqueuepot(p)
       

    def findsol(self):
        sol = set()
        for i in reversed(range(len(self.order))):
            table = self.lqueue[i]
            var = self.order[i]
            t = table.reduce(list(sol))
            if len(t.listvar) > 1:
                for x in t.listvar:
                    if not x == var:
                        sol.add(x) 
                t = t.reduce(list(sol))
            if t.contradict():
                print("Contradiction looking for solution" , sol )
                break
            elif t.trivial():
                sol.add(var)
            elif t.table[0]:
                sol.add(-var)
            else:
               sol.add(var)
        self.sol = sol
        return sol


    def checkSol(self):
        aux = 0
        for clau in self.initial.listclausOriginal:
            # if (self.messages_PTF): print(clau)
            aux = aux + 1
            if len(clau.intersection(self.sol))==0:
                if (self.messages_PTF): print("\tError in clause: ", clau)
                return False
        if (self.messages_PTF): print("\tSatisfactorily fulfills solution. Number of clauses validated: ", aux)
        return True


    def contradictproblem(self):
        print("Contradiction")
        self.initial.solved = True
        self.initial.contradict = True


    def annul(self):
        self.initial.solved = True
        self.initial.contradict = True
        for pot in self.lpot:
            pot.annul()
        for por in self.lqueue:
            pot.annul()