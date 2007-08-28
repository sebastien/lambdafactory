# This is a stub module that will compile the Sugar code into python and
# populate this module with it. It is a good example of how to write a Python
# module in Sugar 
import os, stat
import sugar.sugar as sugar
if not os.path.exists("_passes.py") \
or os.stat("passes.spy")[stat.ST_MTIME] > os.stat("_passes.py")[stat.ST_MTIME]:
	f = file("_passes.py","w")
	f.write(sugar.runAsString(["-clpy", "passes.spy"]))
	f.close()
from _passes import *
if __name__ == "__main__":
	import sys
	sys.exit(_passes.__main__(sys.argv))
# EOF
