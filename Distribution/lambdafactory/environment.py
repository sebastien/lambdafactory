import sys
__module__ = sys.modules[__name__]
import os, sys
from lambdafactory.reporter import DefaultReporter
from lambdafactory.modelbase import Factory
from lambdafactory.passes import PassContext
__module_name__ = 'lambdafactory.environment'
class Importer:
	"""The Environment importer class acts like a "hub" for language-specific
	importers. It will try, according to the current environment settings,
	to resolve a module absolute name and return a program model object
	corresponding to the given module."""
	def __init__ (self, environment):
		self.environment = None
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
			self.environment.report.info("Importing module", moduleName, "from", module_path, "...")
			self.environment.report.indent()
			module=self.environment.parseFile(module_path)
			module.setImported(True)
			self.environment.report.dedent()
	

class Language:
	def __init__ (self, name, environment):
		self.name = None
		self.basePath = None
		self.runtime = None
		self.importer = None
		self.writer = None
		self.reader = None
		self.runner = None
		self.environment = None
		self.readExtensions = []
		self.environment = environment
		self.name = name
		self.basePath = self.basePath
		self.runtime = self.loadModule("runtime")
		self.importer = self.loadModule("importer")
		self.writer = self.loadModule("writer")
		self.reader = self.loadModule("reader")
		self.runner = self.loadModule("runner")
	
	def addRecognizedExtension(self, extension):
		self.readExtensions.append(extension.lower())
	
	def recognizes(self, path):
		extension=os.path.splitext(path)[-1][1:].lower()
		return (extension in self.readExtensions)
	
	def loadModule(self, moduleName):
		"""Dynamically loads the language module"""
		try:
			exec((((("import lambdafactory.languages." + self.name) + ".") + moduleName) + " as m"))
			module=eval("m")
			return getattr(module, "MAIN_CLASS")
		except Exception, e:
			error=str(e)
			if (not error.startswith("No module")):
				self.environment.report.error(((((("Language " + self.name) + ", cannot import module ") + moduleName) + ": ") + str(e)))
			return None
	

class Environment:
	def __init__ (self):
		self.factory = None
		self.program = None
		self.parsers = {}
		self.passes = []
		self.writer = None
		self.report = DefaultReporter
		self.importer = None
		self.languages = {}
		self.resolver = None
		self.importer = Importer(self)
		self.factory = Factory()
		self.program = self.factory.createProgram()
	
	def addParser(self, parser, extensions):
		for ext in extensions:
			self.parsers[ext.lower()] = parser
	
	def addImporter(self, importer):
		pass
	
	def addPass(self, programPass):
		self.passes.append(programPass)
	
	def getPass(self, name):
		for p in self.passes:
			if (p.getName() == name):
				return p
	
	def getPasses(self):
		return self.passes
	
	def runPasses(self):
		context=PassContext(self)
		context.run()
		return context
	
	def getProgram(self):
		return self.program
	
	def getFactory(self):
		return self.program.getFactory()
	
	def importModule(self, name):
		return self.importer.importModule(name)
	
	def parseFile(self, path):
		extension=os.path.splitext(path)[-1][1:].lower()
		parser=self.parsers.get(extension)
		source_and_module=parser.parse(path)
		return source_and_module[1]
	
	def listAvailableLanguages(self):
		"""Returns a list of available languages"""
		base_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "languages")
		languages=[]
		for name in os.listdir(base_dir):
			if os.path.isdir(os.path.join(base_dir, name)):
				languages.append(name)
		return languages
	
	def loadLanguages(self):
		for language in self.listAvailableLanguages():
			self.loadLanguage(language)
	
	def loadLanguage(self, name):
		"""Loads the given language plug-in and returns a dictionary containing
		its features."""
		if (not (name in self.languages.keys())):
			self.languages[name] = Language(name, self)
		return self.languages[name]
	

