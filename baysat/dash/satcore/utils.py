# -*- coding: utf-8 -*-
from .ClausesTable import *
from .TablesVar import *




def size(l):
    tot = set()
    if l:
        for h in l:
            tot.update(set(h.listvar))
        return len(tot)
    else:
        return 0    


def partev(list_,v):
    bor = []
    nl = []
    for p in list_:
        if p.trivial():
            bor.append(p)
            break 
        if v in p.listvar:
            l = p.decomposev(v)
            if len(l)>1:
                for q in l:
                    if not q.trivial():
                        nl.append(q)
                bor.append(p)
    for p in bor:
        list_.remove(p)
    list_.extend(nl)
    list_.sort(key = lambda x : len(x.listvar) )


def potdev(v):
    res = nodeTable([abs(v)])
    if v>0:
        res.table[0] = False
    else:
        res.table[1] = False
    return res


def calculaclusters1(list_,p,var):
    li = [set(q.listvar).union(p.listvar) - {var} for q in list_]
    deleteincluded(li)
    return li


def calculaclusters2(list_,var):
    li = []
    for p in list_:
        s = set(p.listvar)
        for q in list_:
            li.append(s.union(q.listvar)- {var})
    deleteincluded(li)
    return li


def deleteincluded(list_):
    list_.sort(key = lambda x : - len(x) )
    i=0
    while i <len(list_)-1:
        j = i+1
        while j < len(list_):
            con1 = list_[i]
            con2 = list_[j]
            if con2 <= con1:
                list_.remove(con2)
            else:
                j+=1
        i += 1


def orderandcombineincluded(list_,rela, vdelete = True, inter=False):
    list_.sort(key = lambda x : - len(x.listvar) )
    i=0
    while i <len(list_)-1:
        j = i+1
        while j < len(list_):
            if set(list_[j].listvar) <= set(list_[i].listvar):
                p = list_[i]
                q = list_[j]
                rela.deletepot(p)
                if vdelete:
                    rela.deletepot(q)
                t = p.combine(q)
                if t.contradict():
                    rela.annul()
                    print("contradiction ")
                    return 
                rela.insert(t)
                list_[i] = t
                if vdelete:
                    list_.remove(q)
                else:
                    j +=1
            else:
                if inter:
                    p = list_[i]
                    q = list_[j]
                    tp = p.upgrade(q)
                    tq = q.upgrade(p)
                    if tp.contradict() or tq.contradict():
                        rela.annul()
                        print("contradiction ")
                        return
                    rela.deletepot(p)
                    rela.deletepot(q)
                    list_[i] = tp
                    list_[j] = tq
                    rela.insert(tp)
                    rela.insert(tq)
                j+=1
        i+=1
    list_.reverse()
    
    
def groupsize(list_):
    list_.sort(key = lambda x : - len(x.listvar) )
    i=0
    while i <len(list_)-1:
        j = i+1
        while j < len(list_):
            s1 = set(list_[j].listvar)
            s2 = set(list_[i].listvar)
            if s1 <= s2 or ((len(s1) == len(s2) and (len(s1-s2) == 1))):
                p = list_[i]
                q = list_[j]
                t = p.combine(q)
                if t.contradict():
                    print("contradiction ")
                    return 
                list_[i] = t
                del list_[j]
            else:
                j+=1
        i+=1
    list_.reverse()


def createclusters (list_):
    listsets = []
    for cl in list_:
        va = set(map(abs,cl))
        encontrado = False
        for x in listsets:
            if va <= x:
                encontrado = True
                break
        if not encontrado:
            listsets.append(va)
    i = 0
    j = 1
    while (i<len(listsets)-1):
        if listsets[i] <= listsets[j]:
            del listsets[i]
            j = i+1
        elif listsets[j] <= listsets[i]:
            del listsets[j]
            if j >= len(listsets):
                i += 1
                j = i+1
        else:
            j += 1
            if j >= len(listsets):
                i += 1
                j = i+1
    listclaus = []
    for i in range(len(listsets)):
        listclaus.append([])
    for cl in list_:
        va = set(map(abs,cl))
        for i in range(len(listsets)):
            if va <= listsets[i]:
                listclaus[i].append(cl)
                break
    return(listsets,listclaus)


def marginalize(list_, var, Split_In, M=30, Q=20, see_messMar=True):
    if not list_:
        return (True,[],[])
    if Split_In:
        partev(list_,var)
    res = []
    si = []
    vars = set()
    deter = False
    for p in list_:
        if var in p.listvar:
            vars.update(p.listvar)
            si.append(p)
            if not deter:
                deter = p.checkdetermi(var)
                if deter: 
                    nv = set()
                    keyp = p.minimizedep(var,nv)
                    setkey = set(keyp.listvar)
        else:
            # print("warning: variable no in table")
            res.append(p)
    if not si:
        return (True,res,[nodeTable([var])])
    exact = True
    if deter:
        # if (see_messMar): print("\t\t\tdeterminista ")
        vars.discard(var)
        listp = [keyp]
        if len(vars) <= Q:
            r = nodeTable([])
            lc = calculaclusters1(si,keyp,var)
            while si:
                q = si.pop()
                r.combine(q,inplace=True)
            r.delete([var],inplace=True)
            if r.contradict():
                con = nodeTable([])
                con.annul()
                print("contradiction")
                return (True,[con],[keyp])
            for h in lc:
                rh = r.delete(list(vars-h)) 
                        
                if not rh.trivial():
                    res.append(rh)
        else:
            while si:
                q = si.pop() 
                if q == keyp:
                    r = q.delete([var],inplace = False)
                else:
                    if len(setkey.union(set(q.listvar))) < M+1:
                        r = q.combine(keyp,inplace = False, des = False)
                        r.delete([var],inplace = True)
                        if r.contradict():
                            con = nodeTable([])
                            con.annul()
                            return (True,[con],[])
                        if not r.trivial():
                            res.append(r)
                    else:
                        exact = False
    else:
            si.sort(key = lambda h: - len(h.listvar) )
            # if (see_messMar): print("deleted " , var, "method 2, n potentials", len(si))
            if len(si) >= 30:
                    groupsize(si)
            lc = calculaclusters2(si,var)
            vars.discard(var)
            sizes = 0.0
            for xx in lc:
                sizes += 2**len(xx)
            list_ = []
            if 2**(len(vars)-1) <= sizes and len(vars) <=31:
                # if (see_messMar): print ("\t\t\tglobal total ")
                r = nodeTable([])
                while si:
                    q = si.pop()
                    r.combine(q,inplace=True)
                listp = [r.copyto()]
                r.delete([var],inplace=True)
                if r.contradict():
                    con = nodeTable([])
                    con.annul()
                    return (True,[con],[])
                if not r.trivial():
                        res.append(r)
            elif len(vars)<= Q:
                # if (see_messMar): print("\t\t\tglobal ")
                r = nodeTable([])
                while si:
                    q = si.pop()
                    r.combine(q,inplace=True)
                listp = [r.copyto()]
                
                r.delete([var],inplace=True)
                if r.contradict():
                    con = nodeTable([])
                    con.annul()
                    return (True,[con],[])
                for h in lc:
                    rh = r.delete(list(vars-h)) 
                    if not rh.trivial():
                        res.append(rh)
            else:
                # if (see_messMar): print("\t\t\tno global", len(vars), vars)
                if (see_messMar): print("\t\t\tno global")
                si2 = si.copy()
                listp = si2
                while si:
                    q = si.pop()
                    for p in si2:
                        if len(set(q.listvar).union(set(p.listvar))) >M+1:
                            if (see_messMar): print( "\t\t\tno exacto")
                            exact = False
                        else:
                            r = p.combine(q)
                            r.delete([var], inplace = True)
                            if r.contradict():
                                con = nodeTable([])
                                con.annul()
                                r = nodeTable([var])
                                r.table[0] = False
                                r.table[1] = False
                                return (True, [con],listp)
                            if not r.trivial():
                                res.append(r)      
    return (exact,res,listp)


def calculamethod(list_,var):
            si = []    
            deter = False
            vars = set()
            if len(list_)<=2:
                return 1
            for p in list_:
                if var in p.listvar:
                        vars.update(p.listvar)
                        si.append(p)
                        if not deter:
                            deter = p.checkdetermi(var)
                            if deter: 
                                return 1
            return 2              