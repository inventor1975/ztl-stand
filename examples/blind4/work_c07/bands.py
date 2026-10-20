from decimal import Decimal as D
def mk(w, ctrl_first=True):
    t=lambda c: str(D('273.15')+D(c))
    bands=[]; c=-20
    while c<60:
        n=c+w
        # a band crossing 0 or 40 would need splitting; w must divide 20
        b="0.4" if (c>=0 and n<=40) else "1"
        bands.append((t(c),t(n),b,"b_%+d_%+d"%(c,n)))
        c=n
    if ctrl_first:
        bands.sort(key=lambda z:(z[2]!="0.4"))
    return bands
