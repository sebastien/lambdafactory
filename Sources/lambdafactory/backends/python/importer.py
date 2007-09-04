#8< ---[importer.py]---
import sys
__module__ = sys.modules[__name__]
__module_name__ = 'importer'
class Importer:
	"""Imports Python module into the current environment."""
	def __init__ (self, environment):
		self.environment = environment
	
	def importModule(self, moduleName):
		print ("IMPORT", moduleName)
		try:
			exec "import %s" % (moduleName)
			
		except Exception, e:
			print (e)
			return False
		python_module=eval(moduleName)
		for slot in dir(python_module):
			print ("SLOT")
	

