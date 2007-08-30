# This is a stub module that will compile the Sugar code into python and
# populate this module with it. It is a good example of how to write a Python
# module in Sugar 
#
# To use it, simply replace model by the name of your module, which must have
# the same name as your python module, except with the 'spy' extension:
#
# mymodule.py              (this file with model=mymodule)
# mymodule.spy             (the Sugar file)
#
# Now, when importing 'mymodule' from Python, 'mymodule.spy' will be compiled to
# the '_mymodule.py' module, which will then be loaded by the 'mymodule.py'
# module.
import os, stat
import sugar.sugar as sugar
if not os.path.exists("_model.py") \
or os.stat("model.spy")[stat.ST_MTIME] > os.stat("_model.py")[stat.ST_MTIME]:
	f = file("_model.py","w")
	f.write(sugar.runAsString(["-clpy", "model.spy"]))
	f.close()
from _model import *
if __name__ == "__main__":
	import sys
	sys.exit(_model.__main__(sys.argv))
# EOF
