from tablaClausulas  import *
from baysat.dash.satcore.utils import *

def creadesdetabla(t, Q=15):
        # r = t.minimiza(con = nodoTabla([]))
            res = arbol()
            if t.trivial():
                res.value =  nodoTabla([])
                res.var = 0
            elif t.contradict():
                res.value =  nodoTabla([])
                res.var = 0
                res.value.tabla = False
            elif len(t.getvars())<=Q:
                res.value= t
                res.var = 0
            else:

                v = t.minentropia()
                res.var = v
                t0 = t.reduce([-v], inplace = False)
                t1 = t.reduce([v], inplace = False)
               
                l0 = creadesdetabla(t0, Q)
                l1 = creadesdetabla(t1, Q)
                res.hijos[0] = l0
                res.hijos[1] = l1 
            return res

class arbol:
    def __init__(self):
        self.var = 0
        self.value = nodoTabla([])
        self.hijos = [None,None]

    def contradict(self):
        if self.value.contradict():
            return True
        if self.var == 0:
            return False
        if self.hijos[0].contradict() and self.hijos[1].contradict():
            return True
        return False
    
    def copia(self):
        res = arbol()
        res.var = self.var
        res.value = self.value.copia()
        if not res.var == 0:
            res.hijos[0] = self.hijos[0].copia()
            res.hijos[1] = self.hijos[1].copia()
        return res


    def size(self):
        if self.var==0:
            return 1
        else:
            return self.hijos[0].size()+self.hijos[1].size()+1
        

    def neg(self):
        result = arbol()
        if self.var == 0:
            result.value = self.value.neg()
        else:
            result.var = self.var
            result.hijos[0] = self.hijos[0].neg()
            result.hijos[1] = self.hijos[1].neg()
        return result



    def getvars(self):
        res = set()
        if self.var ==0:
            return set(self.value.listavar)
        res = set(self.value.listavar)
        res.add(self.var)
        res.update(self.hijos[0].getvars())
        res.update(self.hijos[1].getvars())
        return list(res)
    

    def trivial(self):
        if not self.value.trivial():
            return False
        if self.var == 0:
            return True
        if self.hijos[0].trivial() and self.hijos[1].trivial():
            return True
        return False
    
    def totable(self):
        if self.var == 0:
            return self.value
        else:
            v = self.var
            t0 = self.hijos[0].totable()
            t1 = self.hijos[1].totable()
            h0 = t0.suma(potdev(v))
            h1 = t1.suma(potdev(-v))
            return h0.combina(h1)




    def equivalente(self,p):
       
       
        if self.suma(p.neg()).trivial() and p.suma(self.neg()).trivial():
            return True
        else:
            return False
        

    def poda(self,Q=15):
        
        if self.var == 0:
            if len(self.value.listavar)<= Q:
                return
            else:
                h = creadesdetabla(self.value,Q)
                self.value = h.value
                self.var = h.var
                self.hijos = h.hijos
                return
        self.hijos[0].poda(Q)
        self.hijos[1].poda(Q)

        if self.hijos[0].var ==0 and self.hijos[1].var ==0:
            if self.hijos[0].value.contradict() and self.hijos[1].value.contradict():
                self.var = 0
                self.hijos = [None,None]
                self.value.anula()
                return

            if self.hijos[0].value.trivial() and self.hijos[1].value.trivial():
                self.var = 0
                self.hijos = [None,None]
                self.value= nodoTabla([])

                return

            if self.hijos[0].value.contradict() or self.hijos[1].value.contradict():
                return 

            if len(set(self.hijos[0].value.listavar).union(set(self.hijos[1].value.listavar)))<=Q-1:
                v = self.var
                self.var = 0
                r0 = self.hijos[0].value.suma(potdev(v))
                r1 = self.hijos[1].value.suma(potdev(-v))
                self.hijos = [None,None]
                self.value = r0.combina(r1)
                return
        
    def simpli(self,Q=15, eps=0.4):

        
        if self.var == 0:
            if (not isinstance(self.value.tabla,boolean)) and (self.value.tabla.sum() > (1-eps)*2**(len(self.value.listavar))):
                self.value = nodoTabla([])
                return
            else:
                return

        ne = min(eps,1.0)

                
        self.hijos[0].simpli(Q,ne)
        self.hijos[1].simpli(Q,ne)

        if self.hijos[0].var ==0 and self.hijos[1].var ==0:
            if self.hijos[0].value.contradict() and self.hijos[1].value.contradict():
                self.var = 0
                self.hijos = [None,None]
                self.value.anula()
                return

            if self.hijos[0].value.trivial() and self.hijos[1].value.trivial():
                self.var = 0
                self.hijos = [None,None]
                self.value= nodoTabla([])

                return
            
            if isinstance(self.value.tabla,boolean):
                return

            if len(set(self.hijos[0].value.listavar).union(set(self.hijos[1].value.listavar)))<=Q-1:
                v = self.var
                self.var = 0
                r0 = self.hijos[0].value.suma(potdev(v))
                r1 = self.hijos[1].value.suma(potdev(-v))
                self.hijos = [None,None]
                self.value = r0.combina(r1)
                self.simpli()
                return
        

    def reduce(self,lv):
        if self.var == 0:
            # print(self.value,self.value.listavar,self.value.tabla)
            t = self.value.reduce(lv)
            
            res = arbol()
            res.value = t
            return res
        
        v = self.var
        if v in lv:
            return self.hijos[1].reduce(lv)
        if -v in lv:
            return self.hijos[0].reduce(lv)

        res = arbol()
        res.var=v
        res.hijos[0] = self.hijos[0].reduce(lv)
        res.hijos[1] = self.hijos[1].reduce(lv)
        return res

    def combina(self,t, Q=25,con = []):
        res = arbol()
    

        if isinstance(t,nodoTabla):
            if self.var == 0:
                        value = self.value.combina(t.reduce(con))
                        if value.contradict():
                            res.value.anula()
                            return res
                        else:
                            resq = creadesdetabla(value,Q)
                            res.var = resq.var
                            res.value = resq.value
                            res.hijos = resq.hijos
                        
                            return res
            else:
                res.var = self.var
                con.append(-self.var)
                res.hijos[0] = self.hijos[0].combina(t,Q,con)
                con.pop()
                con.append(self.var)

                res.hijos[1] = self.hijos[1].combina(t,Q,con)
                con.pop()
                return res
        if t.var ==0:
            return self.combina(t.value,Q, con)
        
        if self.var == 0:
            h = t.reduce(con)
            h.poda(Q)
            return h.combina(self)
        

        res.var = self.var
        con.append(-self.var)
        res.hijos[0] = self.hijos[0].combina(t,Q,con)
        con.pop()
        con.append(self.var)

        res.hijos[1] = self.hijos[1].combina(t,Q,con)
        con.pop()

        return res
            
            
        




    def suma(self,t, Q=15,con = []):
        res = arbol()
    

        if isinstance(t,nodoTabla):
            if self.var == 0:
                        value = self.value.suma(t.reduce(con))
                        if value.trivial():
                            res.value = nodoTabla([])
                            return res
                        else:
                            resq = creadesdetabla(value,Q)
                            res.var = resq.var
                            res.value = resq.value
                            res.hijos = resq.hijos
                        
                            return res
            else:
                res.var = self.var
                con.append(-self.var)
                res.hijos[0] = self.hijos[0].suma(t,Q,con)
                con.pop()
                con.append(self.var)

                res.hijos[1] = self.hijos[1].suma(t,Q,con)
                con.pop()
                return res
        if t.var ==0:
            return self.suma(t.value,Q, con)
        
        if self.var == 0:
            h = t.reduce(con)
            h.poda(Q)
            return h.suma(self)
        

        res.var = self.var
        con.append(-self.var)
        res.hijos[0] = self.hijos[0].suma(t,Q,con)
        con.pop()
        con.append(self.var)

        res.hijos[1] = self.hijos[1].suma(t,Q,con)
        con.pop()

        return res
            
            
        
                    
    def borra(self,lv,Q=25):
        res =  arbol()
        if self.var ==0:
            nlv = list(set(lv).intersection(set(self.value.listavar)))
            res.value = self.value.borra(nlv)
            if res.value.trivial():
                res.value = nodoTabla([])
            return res
        v = self.var
        if v in lv:
            res = self.hijos[0].suma(self.hijos[1],Q)
            return res
        else:
            res.var = v
            res.hijos[0] = self.hijos[0].borra(lv,Q)
            res.hijos[1] = self.hijos[1].borra(lv,Q)
            return res

    def checkdetermi(self,v):
        
        t0 = self.reduce([v])
        t1 = self.reduce([-v])

        t = t0.combina(t1, Q=20)

        if t.contradict():
            return True
        else:
            return False

    def minimizadep(self,v, seg = set()):
        vars = set(self.getvars()) - seg
        vars.remove(v)

        if not vars:
            return self
        nv = vars.pop()

        np = self.borra([nv])

    

        if not np.trivial() and np.checkdetermi(v):
            return np.minimizadep(v, seg.copy())
        else:
            seg.add(nv)
            return self.minimizadep(v,seg)




    def imprime(self, str = ''):

            print (str +"variable ",self.var)
            if self.var==0:
                print(str + "valor " , self.value)
            else:
                print(str +"hijo 1")
                self.hijos[0].imprime(str  + '   ')
                print(str +"hijo 2")
                self.hijos[1].imprime(str  + '   ')     