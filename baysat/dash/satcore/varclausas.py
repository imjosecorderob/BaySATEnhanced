# -*- coding: utf-8 -*-
"""
Created on 31 Enero 2022
@author: Serafin
"""
from varclausas import *
from ClausesSimple import *


def signal_handler(signum, frame):
    raise Exception("Tiempo limite")


    
def leeArchivoGlobal(Archivo):
    reader=open(Archivo,"r") 
    cadena = reader.readline()
    while cadena[0]=='c':
        cadena = reader.readline()
    
    cadena.strip()
    listaaux = cadena.split()
    print(listaaux)
    nvar = int(listaaux[2])
    nclaus = int(listaaux[3])
    print(nvar)
    while cadena[0]=='c':
        cadena = reader.readline()

    infor = simpleClauses()
    for cadena in reader:
        if (cadena[0]!='c'):
            cadena.strip()
            listaux=cadena.split()
            listaux.pop()
            listaux = map(int,listaux)
            clausula= set(listaux)
            nc = set( map(lambda t: -t, clausula))

            infor.listclausOriginal.append(clausula.copy())
            if not nc.intersection(clausula):
                infor.insert(clausula, test = False)
            else:
               print("trivial ", clausula)

            if infor.contradict:
                print("contradiccion leyendo")
    
    return infor, nvar, nclaus
   
def experimentDP(fi = "data_In_Out/list0", fo = "data_In_Out/output1"):
        reader=open("data_In_Out/list0","r")
        writer=open("data_In_Out/output1","w")
        writer.write("Problem;Time\n")
        ttotal = 0
        # signal.signal(signal.SIGALRM, signal_handler)

        for linea in reader:
            # i=i+1
            linea = linea.rstrip()
            if len(linea)>0:
                cadena = ""
                nombre=linea.strip()
                print(nombre)     
                (info, nvar, nclaus) = leeArchivoGlobal(nombre)
                # signal.alarm(600)

                t1 = time()

                dp = varclau()
                dp.fromSimple(info)

                try:
                    dp.borra()
                except Exception:
                    print("Tiempo limite")
                t2= time()
                
                                    
                                    
                writer.write(nombre + " ; " + str(t2-t1)+"\n")
                
        writer.close()
        reader.close()
    


def eliminaincluidas(lista):
    lista.sort(key = lambda x :  len(x) )

    
    i=0
    while i <len(lista)-1:
        
        j = i+1
        while j < len(lista):
            # print("lista, i, j", len(lista), i, j)
            if lista[i] <= lista[j]:
                del lista[j]
            else:
                j+=1
        
        i+=1
    

class varclau:

        def __init__(self): #EDM

            self.tabla = dict()
            self.unit = set()
            self.contradict = False
                  
        def fromSimple(self,infor):
            self.unit = infor.unit.copy()
            for cl in infor.listclaus:
                self.insertar(cl)

        def anula(self):
            self.tabla = dict()
            self.unit = set()
            self.contradict = True

        def insertaru(self,v):
            self.reduce(v)
            self.unit.add(v)

        def getvars(self):
            res = set(map(abs,self.unit))
            for v in self.tabla:
                if self.tabla[v]:
                    res.add(abs(v))

            return res


        def trivial(self):
            if self.unit:
                return False
            if self.tabla:
                for v in self.tabla:
                    if self.tabla[v]:
                        return False
            return True

        

        def insertar(self,cl):
            if len(cl) == 0:
                self.anula()
                return
            if cl.intersection(self.unit):
                return
            if len(cl) == 1:
                v = cl.pop()
                cl.add(v)
                self.insertaru(v)
                return

            
            nu = set(map(lambda x: -x, self.unit))
            clf = cl - nu

            for x in clf:
                if not x in self.tabla:
                    self.tabla[x] = [clf]
                else:
                    self.tabla[x].append(clf)



            

            

        def reduce(self,v):
        
            if v in self.unit:
                self.unit.discard(v)
                return 
            elif -v in self.unit:
                self.anula()
                return 
            if v in self.tabla:
                lista = self.tabla[v].copy()
                for cl in lista:
                    self.elimina(cl)
                del self.tabla[v]
            
            if -v in self.tabla:
                lista = self.tabla[-v].copy()
                ana = []
                for cl in lista:
                    self.elimina(cl)
                    clv = cl - {-v}
                    ana.append(clv)
                del self.tabla[-v]
                for cl in ana:
                    self.insertar(cl)
            


            
            return 


        def copia(self):
            res = varclau()
            res.unit = self.unit.copy()
            res.contradict = self.contradict
            for x in self.tabla.keys():
                res.tabla[x] = self.tabla[x].copy()
            return res




        

        def createfromlista(self,l):
            for p in l:
                self.insertar(p)


        def elimina(self,cl):
            if cl == 1:
                v = cl.pop()
                cl.add(v)
                self.unit.discard(v)
                return
            for v in cl:
                self.tabla[v].remove(cl)

      

        def siguiente(self):

            if self.unit:
                x = self.unit.pop()
                self.unit.add(x)
                return abs(x)
            vars = self.getvars()
            miv = min(vars,key = lambda x: len(self.tabla.get(x,[]))*len(self.tabla.get(-x,[]))   )

            # print(miv,mav,len(self.tabla.get(miv)),len(self.tabla.get(mav)))

            return (miv)
                




        def borra(self, L=600):
            trabajo = self
            
            
            while trabajo.getvars() and not trabajo.contradict:
                v = trabajo.siguiente()
                # print(v,len(trabajo.getvars()))
                if v in trabajo.unit:
                    trabajo.unit.discard(v)
                    continue
                if -v in trabajo.unit:
                    trabajo.unit.discard(-v)
                    continue
                lista1 = trabajo.tabla.get(v,[]).copy()
                lista2 = trabajo.tabla.get(-v,[]).copy()

                for cl in lista1:
                    trabajo.elimina(cl)
                for cl in lista2:
                    trabajo.elimina(cl)
                
                eliminaincluidas(lista1)
                eliminaincluidas(lista2)

             

                for cl1 in lista1:
                    
                    for cl2 in lista2:
                        cl = cl1.union(cl2)-{v,-v}
                        cln = set(map(lambda x:-x,cl))
                        if not cl.intersection(cln):
                            trabajo.insertar(cl)

    