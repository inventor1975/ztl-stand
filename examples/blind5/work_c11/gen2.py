import json,sys,itertools,importlib.util
# build on gen.py's brick: load it
import subprocess
base=json.load(open("../c11.json")) if False else None
