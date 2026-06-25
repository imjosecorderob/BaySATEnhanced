# -*- coding: utf-8 -*-
"""
Created on Tue Oct 19 20:16:00 2021

@author: efrai
"""
 
import networkx as nx

class simpleClausulas:
    def __init__(self):
         self.listaclaus = []
         self.contradict = False
         self.listavar = set()    
         self.solved = False
         self.solution = set()
         self.unit = set()
         self.listaclausOriginal = []
         
    def insertar(self,x, test=True):
        # nx = set(map(lambda t: -t, x))
        # if nx.intersection(x):
        #     print("no inserto ", x)
        #     return

        if self.contradict:
            return []
        if not x:
            self.anula()
            self.contradict= True
            self.listaclaus.append(set())
            return []
        y = []
        borr = []
        if len(x) ==1:
            v = x.pop()
            if -v in self.unit:
                self.insertar(set())
            else:
                self.listavar.add(abs(v))
                self.unit.add(v)
                for cl in self.listaclaus:
                    if v in cl:
                        borr.append(cl)
                    if -v in cl:
                        borr.append(cl)
                        cl.discard(-v)
                        y.append(cl)
        else:
            if x.intersection(self.unit):
                return []
            else:
                neg = set(map(lambda x: -x, self.unit))
                x = x-neg
                if len(x) <= 1:
                    self.insertar(x)
                    return
                
            if test:
                for cl in self.listaclaus:
                    if len(x) <= len(cl):
                        claudif = x-cl
                        if not claudif:
                            borr.append(cl)
                        elif len(claudif) == 1:
                            var = claudif.pop()
                            if -var in cl:
                                cl.discard(-var)
                                borr.append(cl)
                                y.append(cl)
                    if len(cl) <= len(x):
                        claudif = cl-x
                        if not claudif:
                            return []
                        elif len(claudif) == 1:
                            var = claudif.pop()
                            if -var in x:
                                x.discard(-var)
                                for cl in borr:
                                    self.eliminar(cl)
                                self.insertar(x)
                                return []
            nvar = set(map(abs,x))
            self.listavar.update(nvar)
            self.listaclaus.append(x)
        for cl in borr:
            self.eliminars(cl)
        for cl in y:
            self.insertar(cl)

    def eliminar(self,x):
        if len(x)==1:
            v = x.pop()
            self.unit.discard(v)
            return
        try:
            self.listaclaus.remove(x)
        except:
            ValueError
            
    def eliminars(self,x):
        try:
            self.listaclaus.remove(x)
        except:
            ValueError
            
    def anula(self):
        self.listaclaus.clear()
        self.listavar.clear()
        self.unit.clear()

    def cgrafo(self):
        grafo = nx.Graph()
        grafo.add_nodes_from(self.listavar)
        for cl in self.listaclaus:
           for u in cl:
                   for v in cl:
                       if not abs(u)==abs(v):
                           grafo.add_edge(abs(u),abs(v))                     
        return grafo
    
    def simplificaunit(self,v):
        if -v in self.unit:
            self.insertar(set())
        if v in self.unit:
            self.unit.discard(v)
            self.listavar.discard(abs(v))
        else:
            y = []
            borr = []
            for cl in self.listaclaus:
                if -v in cl:
                    borr.append(cl)
                    cl.discard(-v)
                    y.append(cl)
                elif v in cl:
                    borr.append(cl)
            for cl in borr:
                self.eliminars(cl)
            for cl in y:
                self.insertar(cl)

    def compruebasol2(self,config):
        conf = set(config)
        if not self.unit <= conf:
            print("Solucion no valida")
            print(config)
            print("unitarias", self.unit)
            return False



        for y in self.listaclaus:
            inte = conf.intersection(y)
            if not inte:
                print("solucion no valida ")
                print(config)
                print("clausula ",y)
                return False
        print ("correcto")
        return True  
                        
                
    def combina(self,simple):
        if self.contradict:
            return
        neg = set(map(lambda x: -x, simple.unit))
        if neg.intersection(self.unit):
            self.insertar(set())
        else:
            for v in simple.unit:
                self.insertar({v})
            for cl in simple.listaclaus:
                self.insertar(cl)
                