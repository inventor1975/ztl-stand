import json,sys
for f in sys.argv[1:]:
    t=open(f).read()
    try: j=json.loads(t[__import__("re").search(r"(^|\n)\{",t).start():])
    except Exception as e:
        print(f,"PARSE FAIL",t[:600]); continue
    print("==",f,j.get("verdict"),"checked_by:",j.get("checked_by","")[:20])
    if "finds" in j:
        for x in j["finds"]:
            print("  find",{k:x.get(k) for k in ("quantity","largest","smallest","proved","beyond","beyond_is","verdict")})
    for d in j.get("designs",[]):
        if d["verdict"]!="REFUTED" or "finds" not in j:
            print("  ",d["design"][:48],d["verdict"],d.get("fails"))
    if "designs" in j: print("  counts",j.get("designs_count"))
    for k in ("guaranteed","design","note","reasons"):
        if k in j: print("  ",k,json.dumps(j[k])[:700])
