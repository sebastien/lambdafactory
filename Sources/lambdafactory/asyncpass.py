# This is a stub module that will compile the Sugar code into python and
# populate this module with it. It is a good example of how to write a Python
# module in Sugar 
import os, stat
import sugar.sugar as sugar
if not os.path.exists("_asyncpass.py") \
or os.stat("asyncpass.spy")[stat.ST_MTIME] > os.stat("_asyncpass.py")[stat.ST_MTIME]:
	f = file("_asyncpass.py","w")
	f.write(sugar.runAsString(["-clpy", "asyncpass.spy"]))
	f.close()
from _asyncpass import *
if __name__ == "__main__":
	import sys
	sys.exit(_asyncpass.__main__(sys.argv))
# EOF
