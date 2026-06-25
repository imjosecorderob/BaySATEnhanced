# -*- coding: utf-8 -*-
import networkx as nx

class simpleClauses:
    def __init__(self):
         self.listclaus = []
         self.contradict = False
         self.listvar = set()    
         self.solved = False
         self.solution = set()
         self.unit = set()
         self.listclausOriginal = []
         
         
    def insert(self,x, test=True):
        if self.contradict:
            return []
        if not x:
            self.annul()
            self.contradict= True
            self.listclaus.append(set())
            return []
        y = []
        lstDel = []
        if len(x) ==1:
            v = x.pop()
            if -v in self.unit:
                self.insert(set())
            else:
                self.listvar.add(abs(v))
                self.unit.add(v)
                for cl in self.listclaus:
                    if v in cl:
                        lstDel.append(cl)
                    if -v in cl:
                        lstDel.append(cl)
                        cln = cl - {-v}
                        y.append(cln)
        else:
            if x.intersection(self.unit):
                return []
            else:
                neg = set(map(lambda x: -x, self.unit))
                x = x-neg
                if len(x) <= 1:
                    self.insert(x)
                    return
                
            if test:
                for cl in self.listclaus:
                    if len(x) <= len(cl):
                        claudif = x-cl
                        if not claudif:
                            lstDel.append(cl)
                        elif len(claudif) == 1:
                            var = claudif.pop()
                            if -var in cl:
                                cln = cl -{-var}
                            
                                lstDel.append(cl)
                                y.append(cln)
                    if len(cl) <= len(x):
                        claudif = cl-x
                        if not claudif:
                            return []
                        elif len(claudif) == 1:
                            var = claudif.pop()
                            if -var in x:
                                x.discard(-var)
                                for cl in lstDel:
                                    self.delete(cl)
                                self.insert(x)
                                return []
            nvar = set(map(abs,x))
            self.listvar.update(nvar)
            self.listclaus.append(x)
        for cl in lstDel:
            self.deletes(cl)
        for cl in y:
            self.insert(cl)


    def delete(self,x):
        if len(x)==1:
            v = x.pop()
            self.unit.discard(v)
            return
        try:
            self.listclaus.remove(x)
        except:
            ValueError

            
    def deletes(self,x):
        try:
            self.listclaus.remove(x)
        except:
            ValueError

            
    def annul(self):
        self.listclaus.clear()
        self.listvar.clear()
        self.unit.clear()