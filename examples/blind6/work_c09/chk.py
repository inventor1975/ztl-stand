import itertools, math
g=9.81
S={'S1':(1500,350,12),'S2':(2500,450,19),'S3':(5000,650,38)}
M={'M0':((.30,.40),0),'M1':((.55,.65),140),'M2':((.70,.75),260)}
def worst(s,n,mat,m_hi=8400,m_lo=7600):
    LC,STF,pr=S[s]; (mlo,mhi),mp=M[mat]
    w={'F':1e99,'R':1e99}
    for mu,m,f,al,kf in itertools.product((mlo,mhi),(m_lo,m_hi),(.85,1.15),(62,75),(.85,1.0)):
        Fv=f*STF*10*math.sin(math.radians(al))*(1+kf)
        base=mu*(0.8*m*g+n*Fv)
        w['F']=min(w['F'],base-0.8*m*g); w['R']=min(w['R'],base-0.5*m*g)
    ok3 = 1.15*STF<=0.5*LC
    return w, ok3, n*pr+mp
if __name__=="__main__":
    res=[]
    for s in S:
        for n in range(11):
            for mat in M:
                w,ok3,c=worst(s,n,mat)
                if w['F']>=0 and w['R']>=0 and ok3: res.append((c,s,n,mat,w))
    res.sort(key=lambda r:r[0])
    for r in res[:8]: print(r)
    print(len(res))
