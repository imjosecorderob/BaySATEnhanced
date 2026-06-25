# -*- coding: utf-8 -*-

import numpy as np

from . import utils as u
from .ClausesTable import nodeTable


def valord(p):
    if not len(p.listvar)==1:
        print("improper call")
    else:
        v = p.listvar[0]
        if not p.table[0]:
            return v
        else:
            return -v



class varpot:
        def __init__(self, Qin=20, SplitIn=True, see_mess=True): 
            self.table = dict()
            self.unit = set()
            self.contradict = False
            self.Q = Qin 
            self.split=SplitIn
            self.messages_TP = see_mess


        def annul(self):
            self.table = dict()
            self.unit = set()
            self.contradict = True


        def insertu(self,v):
            self.reduce(v, inplace=True)
            self.unit.add(v)


        def getvars(self):
            res = set(map(abs,self.unit))
            for v in self.table:
                if self.table[v]:
                    res.add(v)
            return res


        def trivial(self):
            if self.unit:
                return False
            if self.table:
                for v in self.table:
                    if self.table[v]:
                        return False
            return True


        def insert(self,p):
            if len(p.listvar) ==1:
                if p.contradict():
                    self.annul()
                    return
                if not p.trivial():
                    u = valord(p)
                    self.insertu(u)
                    return
                else:
                    return 
            if self.unit:
                varsu = set(map(abs,self.unit))
                if varsu.intersection(set(p.listvar)):
                    varr = filter(lambda x: abs(x) in varsu, self.unit)
                    p = p.reduce(varr,inplace=False)
            for v in p.listvar:
                if v in self.table:
                    self.table[v].append(p)
                else:
                    self.table[v] = [p]


        def reduce(self,v,inplace=True):
            res = self if inplace else  self.copyto()
            if v in self.unit:
                res.unit.discard(v)
            elif -v in self.unit:
                res.annul()
            elif v in self.table:
                list_ = res.get(v)
                res.deletev(v)
                for p in list_:
                    q = p.reduce([v],inplace = False)
                    res.insert(q)
            elif -v in self.table:
                list_ = res.get(-v)
                res.deletev(-v)
                for p in list_:
                    q = p.reduce([v],inplace = False)
                    res.insert(q)
            return res


        def copyto(self):
            res = varpot(see_mess=self.messages_TP)
            res.unit = self.unit.copy()
            res.contradict = self.contradict
            for x in self.table.keys():
                res.table[x] = self.table[x].copy()
            return res


        def createfrompot(self,pot):
            self.contradict = self.contradict
            self.unit = pot.unit.copy()
            for p in pot.listp:
                self.insert(p)
        

        def createfromlist(self,l):
            for p in l:
                self.insert(p)


        def deletepot(self,p):
            if len(p.listvar) == 1:
                v = p.listvar[0]
                if not p.table[0]:
                    self.unit.discard(-v)
                elif not p.table[1]:
                    self.unit.discard(v)
                return 
            for v in p.listvar:
                if v in self.table:
                    try:
                        self.table[v].remove(p)
                    except ValueError:
                        pass # or scream: thing not in some_list!self.table[v].remove(p)


        def deletev(self,v):
            self.unit.discard(v)
            self.unit.discard(-v)
            if v in self.table:
                for p in self.table[v].copy():
                    self.deletepot(p)
                del self.table[v]

        
        def combine(self,rela, inplace=True):
            res = self if inplace else  self.copyto()
            for u in rela.unit:
                res.insertu(u)
            for v in rela.table:
                for p in rela.table[v]:
                    if min(p.listvar) ==v:
                        res.insert(p)
            return res


        def marginalize(self,var,M = 30, Q=20):
            list_ = []
            if self.contradict:
                    print("contradiction ")
                    return (True,list_,[])
            if var in  self.unit:
                    self.unit.discard(var)
                    return (True,list_,[u.potdev(var)])
            elif -var in self.unit:
                    self.unit.discard(-var) 
                    return (True,list_,[u.potdev(-var)])
            (exact,list_,listwithvar) = u.marginalize(self.get(var).copy(),var,self.split,M,Q,self.messages_TP)
            if exact and list_ and not list_[0].listvar:
                if list_[0].contradict():
                    print ("contradiction")
                    self.annul()    
                    return(True,list_,listwithvar)
            for p in list_:
                if p.contradict():
                    print ("contradiction")
                    self.annul()
                else:
                    self.insert(p)     
            self.deletev(var)
            return (exact,list_,listwithvar)


        def marginalizeset(self,vars,M = 30, Q=20, ver = False, inplace = True, pre = False, order = []):
            if not pre:
                vars.intersection_update(self.getvars())
            if inplace:
                if not pre:
                    order = []
                listn = []
                listq = []
                new = []
                if pre:
                    nvars = [x for x in order if x in vars]
                    nvars.reverse()
                    vars = nvars
                e = True
                while vars and not self.contradict:
                    if pre:
                        var = vars.pop()
                    else:
                        var = self.nextp(vars)
                  
                    sizea = u.size(self.table.get(var))
                    list_ = self.get(var)
                    if not pre:
                        pos = vars.copy()
                        dif = 0
                        while pos and dif <=2:
                            met = u.calculamethod(list_,var)
                            if met == 1:
                                break
                            else:
                                if not pre:
                                    pos.discard(var)
                                if pos:
                                    var = self.nextp(pos)
                                    list_ =self.get(var)
                                    dif = u.size(self.table.get(var))- sizea
                        if met==2:
                            var = self.nextp(vars)
                            list_ = self.get(var)
                    u.orderandcombineincluded(list_,self, vdelete = True, inter=False)
                    if ver:
                        if (self.messages_TP): print("\t\tvar", var, "quedan ", len(vars))
                    if not pre:
                        vars.discard(var)
                    (exac,new,past) = self.marginalize(var,M,Q)
                    if not exac:
                        if (self.messages_TP): print("inaccurate deletion" )
                        e = False
                    if not pre:
                        order.append(var)
                    listn.append(new)
                    listq.append(past)
                    if not self.contradict:
                        u.orderandcombineincluded(new,self, vdelete=True)
                return(e,order,new,listq)
            else:
                res = self.copyto()
                res.marginalizeset(vars,M , Q, ver , inplace = True)
                return res

        
        def extractlist(self):
            list_ = []
            for v in self.table:
                for p in self.table[v]:
                    if min(p.listvar) == v:
                        list_.append(p)
            return list_


        def atable(self):
            res = nodeTable([])
            for v in self.unit:
                res.combine(u.potdev(v), inplace=True)
            for v in self.table:
                for p in self.table[v]:
                    if min(p.listvar) == v:
                        res.combine(p, inplace=True)
            return res


        def localUpgrade(self,M=25,Q=20,N=2):
            listp = self.extractlist()        
            for p in listp:                
                    old = np.sum(p.table)
                    vars = set(p.listvar)
                    nvars = vars.copy()
                    tvars = set(p.listvar)
                    list_ = []
                    for i in range(N):
                        for v in nvars:
                            for q in self.table[v]:
                                if not q in list_:
                                    list_.append(q)
                                    qv = set(q.listvar)
                                    tvars.update(qv)
                            nvars = tvars-vars
                            vars = tvars.copy()
                    r = varpot(see_mess=self.messages_TP)
                    r.createfromlist(list_)
                    r.marginalizeset(tvars-set(p.listvar),M,self.Q, ver=False) 
                    nl = r.extractlist()
                    lk = nodeTable([])
                    for q in nl:
                        lk.combine(q,inplace=True)
                    ns = np.sum(lk.table)
                    if (ns < old):
                        self.deletepot(p)
                        self.insert(lk)


        def nextp(self,pos):
            if self.unit:
                varu = set(map(abs,self.unit))
                if varu.intersection(pos):
                    x = varu.pop()
                    return x
            miv = min(pos,key = lambda x: len(self.table.get(x)))
            mav = max(pos,key = lambda x: len(self.table.get(x)))
            if len(self.table.get(miv)) == 1:
                return (miv)
            miv = min(pos,key = lambda x: u.size(self.table.get(x)))
            mav = max(pos,key = lambda x: u.size(self.table.get(x)))
            return miv


        def get(self,i):
            return self.table.get(i,[]).copy()