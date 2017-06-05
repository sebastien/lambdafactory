#8< ---[lambdafactory/environment.py]---
#!/usr/bin/env python
import sys
__module__ = sys.modules[__name__]
import os, stat, sys, pickle, hashlib, imp
from lambdafactory.reporter import DefaultReporter
from lambdafactory.modelbase import Factory
from lambdafactory.passes import PassContext
from lambdafactory.resolution import ClearDataFlow
__module_name__ = 'lambdafactory.environment'
def error (message):
	self=__module__
	sys.stderr.write('[!] {0}\n'.format(message))


def info (message):
	self=__module__
	sys.stderr.write('--- {0}\n'.format(message))


class Importer:
	""" The Environment importer class acts like a "hub" for language-specific
	 importers. It will try, according to the current environment settings,
	 to resolve a module absolute name and return a program model object
	 corresponding to the given module."""
	def __init__ (self, environment):
		self.environment = None
		self.environment = environment
	
	def findSugarModule(self, moduleName, paths=None):
		""" Finds the module with the given name in the given ppaths"""
		if paths is None: paths = None
		exts=['.sg', '.sjs', '.sjava', '.spnuts', '.spy']
		paths = ((paths or []) + self.environment.libraryPaths)
		if os.environ.get('SUGARPATH'):
			paths.extend(os.environ.get('SUGARPATH').split(':'))
		module_path=moduleName.replace('.', os.path.sep)
		for path in paths:
			path = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
			for ext in exts:
				file_path=os.path.join(path, (module_path + ext))
				if os.path.exists(file_path):
					return file_path
		return None
	
	def importModule(self, moduleName):
		module_path=self.findSugarModule(moduleName)
		if module_path:
			self.environment.report.trace('Importing module', moduleName, 'from', module_path)
			return self.importModuleFromFile(module_path, moduleName)
		elif True:
			self.environment.report.error('Module not found:', moduleName)
	
	def importModuleFromFile(self, modulePath, moduleName=None):
		if moduleName is None: moduleName = None
		self.environment.report.indent()
		module=self.environment.parseFile(modulePath)
		if module:
			if moduleName:
				module.setName(moduleName)
			module.setImported(True)
		elif True:
			self.environment.report.error('Cannot parse module:', moduleName)
		self.environment.report.dedent()
		return module
	

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
		assert name, "No language specified"
		self.basePath = self.basePath
		self.runtime = self.loadModule('runtime')
		self.importer = self.loadModule('importer')
		self.writer = self.loadModule('writer')
		self.reader = self.loadModule('reader')
		self.runner = self.loadModule('runner')
	
	def addRecognizedExtension(self, extension):
		self.readExtensions.append(extension.lower())
	
	def recognizes(self, path):
		extension=os.path.splitext(path)[-1][1:].lower()
		return (extension in self.readExtensions)
	
	def loadModule(self, moduleName):
		""" Dynamically loads the language (sub) module"""
		try:
			module=None
			module_name = "lambdafactory.languages." + self.name + "." + moduleName
			root_module = __import__(module_name)
			module      = getattr(getattr(getattr(root_module, "languages"), self.name), moduleName)
			return getattr(module, 'MAIN_CLASS')
		except Exception as e:
			error=str(e)
			if (not error.startswith('No module')):
				self.environment.report.error(((((('Language ' + str(self.name)) + ', cannot import module ') + str(moduleName)) + ': ') + str(e)))
			return None
	

class Cache:
	""" A cache that allows to store pre-compiled AST and modules.
	 Each compiled module is saved in two different locations:
	
	 modules/<modulename>.model
	 content/<sig>.model"""
	def __init__ (self):
		self.root = None
		cache_path=os.path.expanduser('~/.cache/lambdafactory')
		if ('LF_CACHE' in os.environ):
			cache_path = os.environ['LF_CACHE']
		self.setPath(cache_path)
	
	def setPath(self, root):
		if (not os.path.exists(root)):
			os.makedirs(root)
		self.root = root
		return self
	
	def key(self, content):
		return hashlib.sha256(content).hexdigest()
	
	def has(self, sig):
		return self._exists(self._getPathForSignature(sig))
	
	def get(self, sig):
		p=self._getPathForSignature(sig)
		if os.path.exists(p):
			f=open(p)
			try:
				res=pickle.load(f)
			except Exception as e:
				error('Cache. {0}: {1}'.format(sig, e))
				res = None
			f.close()
			return res
		elif True:
			return None
	
	def set(self, key, module):
		k=key
		p=self._getPathForSignature(k)
		f=open(p, 'wb')
		try:
			pickle.dump(module, f, pickle.HIGHEST_PROTOCOL)
			f.flush()
			os.fsync(f.fileno())
			f.close()
		except Exception as e:
			f.close()
			os.unlink(p)
			error('Cache.set {0}: {1}'.format(k, e))
			return None
		pm=self._getPathForModuleName(module.getAbsoluteName())
		if os.path.exists(pm):
			os.unlink(pm)
		os.symlink(p, pm)
		return p
	
	def clean(self):
		pass
	
	def _getPathForSignature(self, sig):
		return (((self.root + '/content-') + sig) + '.cache')
	
	def _getPathForModuleName(self, name):
		return (((self.root + '/module-') + name) + '.cache')
	
	def _exists(self, path):
		""" Tests if the given path exists and has been created less than 24h ago.
		 If it's too old, it will be removed."""
		if (not os.path.exists(path)):
			return False
		elif True:
			mtime = os.stat(path)[stat.ST_MTIME]
			if ((time.time() - mtime) < ((60 * 60) * 24)):
				return True
			elif True:
				os.unlink(path)
				return False
	

class Environment:
	"""
	 Passes
	 ======
	
	 Passes are lists of passes (see 'lambdafactory.passes') that transform the
	 program. The order of passe is important, as some passes depend on each other.
	 It is up to the 'lambdafactory.main.Command' subclass to set up the passes
	 appropriately."""
	ALIASES = {'javascript':['javascript', 'js', 'jscript'], 'ecmascript':['ecmascript', 'es', 'escript'], 'python':['python', 'py']}
	def __init__ (self):
		self.factory = None
		self.program = None
		self.parsers = {}
		self.passes = []
		self.writer = None
		self.report = DefaultReporter
		self.importer = None
		self.languages = {}
		self.libraryPaths = []
		self.options = {}
		self.cache = None
		self.useCache = True
		self.importer = Importer(self)
		self.factory = Factory()
		self.cache = Cache()
		self.program = self.factory.createProgram()
	
	def addLibraryPath(self, path):
		self.libraryPaths.append(path)
	
	def addParser(self, parser, extensions):
		for ext in extensions:
			self.parsers[ext.lower()] = parser
	
	def addPass(self, programPass):
		self.passes.append(programPass)
		programPass.setEnvironment(self)
	
	def getPass(self, name):
		name = name.lower()
		for p in self.passes:
			if (p.getName().lower() == name):
				return p
	
	def getPasses(self):
		return self.passes
	
	def runPasses(self, program):
		for p in self.passes:
			self.report.trace('Running pass {0}'.format(p.__class__.__name__))
			p.run(program)
	
	def getFactory(self):
		return self.factory
	
	def importModule(self, moduleName, importModule=None):
		if importModule is None: importModule = True
		assert(self.program)
		if (importModule and (not self.program.hasModuleWithName(moduleName))):
			module=self.importer.importModule(moduleName)
			if module:
				self.program.addModule(module)
			return module
		elif True:
			return self.program.getModule(moduleName)
	
	def parseFile(self, path, moduleName=None):
		if moduleName is None: moduleName = None
		f=open(path, 'rb')
		text=f.read()
		f.close()
		return self.parseString(text, path, moduleName)
	
	def parseString(self, text, path, moduleName=None):
		if moduleName is None: moduleName = None
		cache_key=self.cache.key(text)
		module=self.cache.get(cache_key)
		if ((not self.useCache) or (not module)):
			extension=path.split('.')[-1]
			parser=self.parsers.get(extension)
			if (not parser):
				parser = self.parsers.get('sg')
			source_and_module=parser.parseString(text, moduleName, path)
			module = source_and_module[1]
			assert((source_and_module[0] == text))
			if source_and_module[1]:
				res=source_and_module[1]
				res.setSource(text)
				if self.useCache:
					self.cache.set(cache_key, res)
			elif True:
				error(('Could not parse file: ' + path))
		elif True:
			assert((module.getDataFlow() is None))
		return module
	
	def listAvailableLanguages(self):
		""" Returns a list of available languages by introspecting the modules"""
		base_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'languages')
		languages=[]
		for name in os.listdir(base_dir):
			if (((not name.startswith('.')) and os.path.isdir(os.path.join(base_dir, name))) and (not name.startswith('_'))):
				languages.append(name)
		return languages
	
	def loadLanguages(self):
		for language in self.listAvailableLanguages():
			self.loadLanguage(language)
	
	def normalizeLanguage(self, name):
		for key_values in self.__class__.ALIASES.items():
			key=key_values[0]
			values=key_values[1]
			if (key == name):
				return key
			elif True:
				for v in values:
					if (v == name):
						return key
		return name
	
	def loadLanguage(self, name):
		""" Loads the given language plug-in and returns a dictionary containing
		 its features."""
		if ((name == 'none') or (not name)):
			return None
		name = self.normalizeLanguage(name)
		if (not (name in self.languages.keys())):
			language=Language(name, self)
			self.languages[name] = language
		return self.languages[name]
	

