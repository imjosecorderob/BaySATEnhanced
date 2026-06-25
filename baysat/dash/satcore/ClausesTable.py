# -*- coding: utf-8 -*-
from xmlrpc.client import boolean
from . import utils as u

import numpy as np
from itertools import product

class nodeTable:
    def __init__(self, list_):
        self.listvar = list_
        n = len(list_)
        t = (2,)*n
        self.table = np.ones( dtype = boolean, shape = t)


    def copyto(self):
        result = nodeTable(self.listvar.copy())
        result.table = self.table.copy()
        return result
    
    def getClauses(self):
        lsets = []
        res= []
        for v in self.listvar:
            lsets.append([-v,v])
        for h in product(*lsets):
            t = self.getvalue(h)
            if not t:
                clau = set(map(lambda x:-x, h))
                res.append(clau)
        return res




    def decomposev(self,v):
        res = []
        h = self.delete([v], inplace = False)
        t = self.minimize(h, pro = {v})
        if len(t.listvar) ==len(self.listvar):
            res.append(self)
        else:
            res.append(t)
            res.append(h)
        return res

    def getvalue(self, val):
        
        values = filter(lambda x: abs(x) in  self.listvar, val)
        vars = map(abs,val)

        rest = set(self.listvar) - set(vars)
        if rest:
            return -1

        values = [
                (abs(var), 0 if var<0 else 1) for var in values
            ]

        var_index_to_del = []
        slice_ = [slice(None)] * len(self.listvar)
        for var, state in values:
            var_index = self.listvar.index(var)
            slice_[var_index] = state
            var_index_to_del.append(var_index)

        return self.table[tuple(slice_)]
    

    def neg(self,inplace=False):
        newtable = np.logical_not(self.table)
        if inplace:
            self.table = newtable
            res = self
        else:
            res = nodeTable(self.listvar.copy())
            res.table = newtable
        return res
    
    
    def impliedby(self,p):
        if self.sum(p.neg()).trivial():
            return True
        else:
            return False


    def minimize(self, con  , pro = set()):
        rest =  set(self.listvar)-pro
        if not rest:
            return self
        else:
            v = rest.pop()
            h = self.delete([v], inplace=False)
            if self.impliedby(h.combine(con)):
                return h.minimize(con,pro)
            else:
                pro.add(v)
                return self.minimize(con,pro)


    def combine(self,op,inplace = False, des= False):
        result = self if inplace else self.copyto()
        if isinstance(op,boolean):
            if op:
                return result
            else:
                result.table = result.table & op
                return result
        if not des:
            op = op.copyto()
        extra = set(op.listvar) - set(result.listvar)
        if extra:
                slice_ = [slice(None)] * len(result.listvar)
                slice_.extend([np.newaxis] * len(extra))
                result.table = result.table[tuple(slice_)]
                result.listvar.extend(extra)
        extra = set(result.listvar) - set(op.listvar)
        if extra:
                slice_ = [slice(None)] * len(op.listvar)
                slice_.extend([np.newaxis] * len(extra))
                op.table = op.table[tuple(slice_)]
                op.listvar.extend(extra)
                # No need to modify cardinality as we don't need it.
            # rearranging the axes of phi1 to match phi
        for axis in range(result.table.ndim):
            exchange_index = op.listvar.index(result.listvar[axis])
            op.listvar[axis], op.listvar[exchange_index] = (
                op.listvar[exchange_index],
                op.listvar[axis],
            )
            op.table = op.table.swapaxes(axis, exchange_index)
        result.table = result.table & op.table    
        if not inplace:
            return result


    def checkdetermi(self,v):
        if v not in self.listvar:
            return False
        t0 = self.reduce([v])
        t1 = self.reduce([-v])
        t = t0.combine(t1, inplace=False)
        if t.contradict():
            return True
        else:
            return False


    def minimizedep(self,v, seg = set()):
        vars = set(self.listvar) - seg
        vars.remove(v)
        if not vars:
            return self
        nv = vars.pop()
        np = self.delete([nv])
        if not np.trivial() and np.checkdetermi(v):
            return np.minimizedep(v, seg.copy())
        else:
            seg.add(nv)
            return self.minimizedep(v,seg)


    def upgrade(self,q):
            vars = list(set(q.listvar) - set(self.listvar))
            res = self.combine(q.delete(vars))
            return res


    def sum(self,op,inplace = False, des= False):
        result = self if inplace else self.copyto()
        if isinstance(op,boolean):
            if op:
                return result
            else:
                result.table = result.table | op
                return result
        if not des:
            op = op.copyto()
        extra = set(op.listvar) - set(result.listvar)
        if extra:
                slice_ = [slice(None)] * len(result.listvar)
                slice_.extend([np.newaxis] * len(extra))
                result.table = result.table[tuple(slice_)]
                result.listvar.extend(extra)
        extra = set(result.listvar) - set(op.listvar)
        if extra:
                slice_ = [slice(None)] * len(op.listvar)
                slice_.extend([np.newaxis] * len(extra))
                op.table = op.table[tuple(slice_)]
                op.listvar.extend(extra)
                # No need to modify cardinality as we don't need it.
            # rearranging the axes of phi1 to match phi
        for axis in range(result.table.ndim):
            exchange_index = op.listvar.index(result.listvar[axis])
            op.listvar[axis], op.listvar[exchange_index] = (
                op.listvar[exchange_index],
                op.listvar[axis],
            )
            op.table = op.table.swapaxes(axis, exchange_index)
        result.table = result.table | op.table    
        if not inplace:
            return result


    def reduce(self, val, inplace=False):
        values = filter(lambda x: abs(x) in  self.listvar, val)
        phi = self if inplace else self.copyto()
        values = [
                (abs(var), 0 if var<0 else 1) for var in values
            ]
        var_index_to_del = []
        slice_ = [slice(None)] * len(self.listvar)
        for var, state in values:
            var_index = phi.listvar.index(var)
            slice_[var_index] = state
            var_index_to_del.append(var_index)
        var_index_to_keep = sorted(
            set(range(len(phi.listvar))) - set(var_index_to_del)
        )
        # set difference is not guaranteed to maintain ordering
        phi.listvar = [phi.listvar[index] for index in var_index_to_keep]
        phi.table= phi.table[tuple(slice_)]
        return phi

    
    def introducelist(self,list_):
        for cl in list_:
            self.introduceclau(cl)
    
    
    def introduceclau(self, values):
        for var in values:
            if abs(var) not in self.listvar:
                raise ValueError(f"La variable: {abs(var)} no está en el potencial")
        values = [
                (abs(var), 1 if var<0 else 0) for var in values
            ]
        slice_ = [slice(None)] * len(self.listvar)
        for var, state in values:
            var_index = self.listvar.index(var)
            slice_[var_index] = state
        # set difference is not guaranteed to maintain ordering
        self.table[tuple(slice_)] = False
    

    def delete(self,variables, inplace=False):
        phi = self if inplace else self.copyto()   
        for var in variables:
            if var not in phi.listvar:
                raise ValueError(f"{var} no está en la list_.")
        var_indexes = [phi.listvar.index(var) for var in variables]
        index_to_keep = sorted(set(range(len(self.listvar))) - set(var_indexes))
        phi.listvar = [phi.listvar[index] for index in index_to_keep]
        phi.table = np.amax(phi.table, axis=tuple(var_indexes))
        if not inplace:
            return phi


    def contradict(self):
        return not np.amax(self.table)


    def annul(self):
        self.listvar = []
        self.table = False


    def trivial(self):
        return  np.amin(self.table)


class PotentialTable:
        def __init__(self):
            self.unit = set()
            self.listp = []
            self.contradict = False


        def annul(self):
            self.unit = set()
            self.listp = []
            self.contradict = True
        
        
        def trivial(self):
            if not self.unit and not self.listp:
                return True
            else:
                return False
        

        def copyto(self):
            res = PotentialTable()
            res.unit = self.unit.copy()
            for p in self.listp:
                res.listp.append(p.copyto())
            return res


        def getvars(self):
            res = set()
            res.update(set(map(abs,self.unit)))
            for p in self.listp:
                res.update(set(p.listvar))
            return res


        def getvarsp(self):
            res = set()
            for p in self.listp:
                res.update(set(p.listvar))
            return res


        def getvarspv(self,v):
            res = set()
            for p in self.listp:
                if v in p.listvar:
                    res.update(set(p.listvar))
            return res


        def computefromsimple(self,simple):
            self.unit = simple.unit.copy()
            (sets,clusters) = u.createclusters(simple.listclaus)
            for i in range(len(sets)):
                x = nodeTable(list(sets[i]))
                x.introducelist(clusters[i])
                self.listp.append(x)


        def insert(self,p):
            self.listp.append(p)

 
        def localUpgrade(self,M=25,Q=10):
            for p in self.listp:
                if len(p.listvar)<=Q:
                    old = np.sum(p.table)
                    vars = set(p.listvar)
                    tvars = set(p.listvar)
                    list_ = []
                    for q in self.listp:
                        if not q==p:
                            qv = set(q.listvar)
                            if set(qv.intersection(vars)):
                                if len(tvars.union(qv))<=M:
                                    tvars.update(qv)
                                    list_.append(q)
                    vars = tvars.copy()
                    for q in self.listp:
                        if not q==p:
                            qv = set(q.listvar)
                            if set(qv.intersection(vars)):
                                if len(tvars.union(qv))<=M:
                                    tvars.update(qv)
                                    list_.append(q)
                    r = nodeTable([])
                    for q in list_:
                        r.combine(q,inplace=True)
                    r.delete(list(tvars-set(p.listvar)),inplace=True)
                    p.combine(r,inplace=True)
                    ns = np.sum(p.table)


        def insertunit(self,x):
            if -x in self.unit:
                self.annul()
                return set()
            self.reduce({x}, inplace=True)
            if not self.contradict:
                self.unit.add(x)
           

        def reduce(self, val, inplace = False):
            res = self if inplace else self.copyto()   
            varv = set(map(abs,val))
            for x in self.unit:
                if -x in val:
                    res.contradict = True
                    return res
            res.unit.difference_update(set(val))
            bor = []
            un = set()
            for p in res.listp:
                if varv.intersection(set(p.listvar)):
                    p.reduce(val,inplace = True)
        
                    if len(p.listvar)<= 1:
                        if p.trivial():
                            bor.append(p)
                        if p.contradict():
                            res.annul()
                            return res
                        if len(p.listvar) == 1:
                            if not p.table[0]:
                                un.add(p.listvar[0])
                                bor.append(p)
                            elif not p.table[1]:
                                un.add(-p.listvar[0])
                                bor.append(p)
            for p in bor:
                res.listp.remove(p)
            for x in un:
                res.insertunit(x)
            if not inplace:
                return res


        def reducenv(self, val, l, inplace = False):
            res = PotentialTable()
            if -val in self.unit:
                    res.annul()
                    return res
            res.unit = self.unit-{val}
            for p in self.listp:
                if abs(val) in p.listvar:
                    q = p.reduce([val],inplace)
                    res.listp.append(q)
                    l.append(q)
                elif not inplace:
                     res.listp.append(p.copyto())
                else:
                    res.listp.append(p)
            return res

                        
        def marginalize(self,var, inplace = False):
            if not inplace:
                res = PotentialTable()
                if self.contradict:
                    res.contradict = True
                    return res
                for x in self.unit:
                    if x == var:
                        res.unit = self.unit-{var}
                        res.listp = self.listp.copy()
                        return res
                    elif x== -var:
                        res.unit = self.unit-{-var}
                        res.listp = self.listp.copy()
                        return res
                    else:
                        res.unit.add(x)
                si = self.listp.copy()
                if si:
                        si.sort(key = lambda h: - len(h.listvar) )
                        p = si.pop()
                        self.listp.remove(p)
                        while si:
                            q = si.pop()
                            self.listp.remove(q)
                            p.combine(q,inplace = True, des =True)
                        r = p.delete([var], inplace=False)
                        self.listp.append(p)
                        res.listp.append(r)
                return res


        def atable(self,un):
            res = nodeTable([])
            for p in self.listp:
                res.combine(p, inplace=True)
            for x in un:
                parcial = nodeTable([abs(x)])
                if x>0:
                    parcial.table[0] = False
                else:
                    parcial.table[1] = False
                res.combine(parcial, inplace=True)
            return res


        def sum(self, opera, inplace = False):
            inter = self.unit.intersection(opera.unit)
            res = PotentialTable()
            res.unit = inter
            t0 = self.atable(self.unit-inter)
            t1 = opera.atable(opera.unit-inter)
            tt = t0.sum(t1,inplace=True)
            res.listp = [tt]
            return res
        
