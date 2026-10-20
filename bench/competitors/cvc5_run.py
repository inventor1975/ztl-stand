"""Run one SMT-LIB file through cvc5's Python API (the pip wheel has no CLI): print sat / unsat / unknown."""
import sys
import cvc5

tm = cvc5.TermManager()
s = cvc5.Solver(tm)
s.setOption("produce-models", "true")
p = cvc5.InputParser(s)
p.setFileInput(cvc5.InputLanguage.SMT_LIB_2_6, sys.argv[1])
sm = p.getSymbolManager()
while True:
    cmd = p.nextCommand()
    if cmd.isNull():
        break
    out = cmd.invoke(s, sm)
    if out.strip():
        print(out.strip(), flush=True)
