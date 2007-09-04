#8< ---[environment.py]---
import sys
__module__ = sys.modules[__name__]
import os
from reporter import DefaultReporter
__module_name__ = 'environment'
class Importer:
	"""The Environment importer class acts like a "hub" for language-specific
	importers. It will try, according to the current environment settings,
	to resolve a module absolute name and return a program model object
	corresponding to the given module."""
	def __init__ (self, environment):
		self.environment = environment
	
	def findSugarModule(self, moduleName):
		paths=[os.getcwd()]
		if os.environ.get("SUGARPATH"):
			paths.extend(os.environ.get("SUGARPATH").split(":"))
		module_path=moduleName.replace(".", "/")
		for path in paths:
			for ext in ".sg .sjs .sjava .spnuts .spy".split():
				if os.path.exists((module_path + ext)):
					return (module_path + ext)
		return None
	
	def importModule(self, moduleName):
		module_path=self.findSugarModule(moduleName)
		if module_path:
			self.environment.reporter.info("Importing module", moduleName, "from", module_path)
			module = self.environment.parseModule(module_path, moduleName)
			self.environment.getProgram().addModule(module)
			self.environment.reporter.info("done.")
	

class Environment:
	def __init__ (self, program):
		self.program = None
		self.parsers = {}
		self.passes = []
		self.writer = None
		self.reporter = DefaultReporter
		self.importer = None
		self.program = program
		self.importer = Importer(self)
	
	def addParser(self, parser, extensions):
		for ext in extensions:
			self.parsers[ext.lower()] = parser
	
	def addImporter(self, importer):
		pass
	
	def addPass(self, programPass):
		self_1188936253_1364=self.passes
		self_1188936253_1364.append(programPass)
	
	def getPass(self, name):
		for p in self.passes:
			if (p.getName() == name):
				return p
	
	def getPasses(self):
		return self.passes
	
	def getProgram(self):
		return self.program
	
	def getFactory(self):
		return self.program.getFactory()
	
	def importModule(self, name):
		return self.importer.importModule(name)
	
	def parseModule(self, path, name):
		extension=os.path.splitext(path)[-1][1:].lower()
		parser=self.parsers.get(extension)
		return parser.parse(path, name)[1]
	

