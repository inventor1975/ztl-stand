import json,sys
# scenarios from the source's table (fig. 11): name, Tjmax, Rint, Rsa(or total RJA), RDS(mohm), published ID
S=[("s2","175","0.5","7","4.9","58.9","forced air, grease, Tj<=175"),
   ("s3","175","2.9","7","4.9","51.6","forced air, insulating pad, Tj<=175"),
   ("s4","150","2.9","7","4.5","48.6","forced air, insulating pad, Tj<=150"),
   ("s5","150","2.9","19","4.5","33.1","natural conv, insulating pad, Tj<=150"),
   ("s6","150",None,"40","4.5","24.7","D2PAK on PCB, RthJA(PCB)=40 max, Tj<=150")]
def build(mode):
    q={"Ta":{"role":"given","value":"40","unit":"C","why":"design assumption of the source: ambient 40 C","ground":"source text"}}
    laws=[];reqs=[];finds=[]
    for n,tj,rint,rsa,rds,pub,desc in S:
        q["ID_"+n]={"role":"given","value":"0","unit":"A","why":"searched: continuous current ("+desc+")"}
        q["Tj_"+n]={"role":"derived","unit":"C"}
        if mode=="nominal":
            q["RDS_"+n]={"role":"given","value":rds,"unit":"mohm","ground":"source fig.11"}
        else:
            q["RDS_"+n]={"role":"given","range":["0",rds],"unit":"mohm","ground":"source fig.11: built on the 3.0 mohm MAX, so an upper bound","why":"lower end 0 is mine, irrelevant to the worst case"}
        if n=="s6":
            if mode=="nominal":
                q["RJA_"+n]={"role":"given","value":rsa,"unit":"C/W","ground":"IRL3713 datasheet p1, PCB mount, max"}
            else:
                q["RJA_"+n]={"role":"given","range":["0",rsa],"unit":"C/W","ground":"IRL3713 datasheet p1: RthJA (PCB mount) MAX 40"}
            expr="Ta + ID_%s*ID_%s*RDS_%s*RJA_%s"%(n,n,n,n)
        else:
            if mode=="nominal":
                q["RJC_"+n]={"role":"given","value":"0.45","unit":"C/W","ground":"datasheet max"}
                q["RSA_"+n]={"role":"given","value":rsa,"unit":"C/W","ground":"source"}
            else:
                q["RJC_"+n]={"role":"given","range":["0","0.45"],"unit":"C/W","ground":"IRL3713 datasheet p1: RthJC MAX 0.45 (TO-220)","why":"lower end 0 is mine"}
                if n=="s5":
                    q["RSA_"+n]={"role":"given","value":rsa,"unit":"C/W","ground":"source table: 19 (natural convection, read from vendor chart)"}
                else:
                    q["RSA_"+n]={"role":"given","range":["0",rsa],"unit":"C/W","ground":"source text: 'a bit under 7' at 500 ft/min; upper end 7","why":"lower end 0 is mine"}
            if mode=="added" and rint=="2.9":
                q["PSI_"+n]={"role":"given","range":["25","100"],"unit":"","why":"ADDED BY ME: clamp pressure unknown, 25..100 psi (source table columns)"}
                q["Rint_"+n]={"role":"derived","unit":"C/W"}
                laws.append({"zfl":"Rint_%s == table(PSI_%s, 10, 3.96, 25, 3.41, 50, 2.90, 100, 2.53, 200, 2.32)*Ru"%(n,n),"source":"Sil-Pad 900S TO-220 thermal performance table (linear between columns = my interpolation)"})
                rint_name="Rint_"+n
            else:
                q["RINT_"+n]={"role":"given","value":rint,"unit":"C/W","ground":"IRL3713 greased typ 0.50 / Sil-Pad table at 50 psi 2.90"}
                rint_name="RINT_"+n
            expr="Ta + ID_%s*ID_%s*RDS_%s*(RJC_%s + %s + RSA_%s)"%(n,n,n,n,rint_name,n)
        laws.append({"zfl":"Tj_%s == %s"%(n,expr),"source":"P = I^2*RDS(on); Tj = Ta + P*(sum of series thermal resistances)"})
        reqs.append({"quantity":"Tj_"+n,"op":"<=","value":tj,"why":"Tj max "+tj+" C ("+desc+")","for_find":n})
        finds.append({"largest":"ID_"+n,"from":"0","to":"100","precision":"0.05","requirements":[{"quantity":"Tj_"+n,"op":"<=","value":tj,"why":"Tj max "+tj+" C ("+desc+"); published ID "+pub+" A"}]})
    for r in reqs: r.pop("for_find")
    if mode=="added":
        q["Ru"]={"role":"given","value":"1","unit":"C/W"}
    return {"stand":"ztl-stand/1","why":"real round 3, n02: largest continuous current of an IRL3713 per thermal scenario (DigiKey TechForum, 'A Thermal Management Example, part 2'); mode="+mode,
            "quantities":q,"slots":{},"laws":laws,"requirements":[reqs[0]] ,"catalog":{},"find":finds}
for m,f in (("main","brick.json"),("nominal","brick_nominal.json"),("added","brick_added.json")):
    json.dump(build(m),open(f,"w"),indent=1)
