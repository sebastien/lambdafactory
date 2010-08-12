#!/usr/bin/env python
"""Command-line interface and main module for LambdaFactory"""
import sys
__module__ = sys.modules[__name__]
import os, sys, optparse, tempfile
from lambdafactory.environment import Environment
from lambdafactory.splitter import FileSplitter
import lambdafactory.passes as passes
import lambdafactory.resolution as resolution
from StringIO import StringIO
__module_name__ = 'lambdafactory.main'
class Command:
	OPT_LANG = 'Specifies the target language (js, java, pnuts, actionscript)'
	OPT_OUTPUT = 'Specifies the output where the files will be generated (stdout, file or folder)'
	OPT_VERBOSE = 'Verbose parsing output (useful for debugging)'
	OPT_API = 'Generates SDoc API documentation (given the API filename)'
	OPT_TEST = 'Tells wether the source code is valid or not'
	OPT_DEFINE = 'Defines a specific target (for @specific)'
	OPT_OPTIONS = 'Options for program transformation passes'
	OPT_RUN = 'Directly runs the script (default)'
	OPT_COMPILE = 'Compiles the given code to the output (current) directory'
	OPT_RUNTIME = 'Outputs the runtime as well when compiled'
	OPT_VERSION = 'Ensures that Sugar is at least of the given version'
	OPT_SOURCE = 'Directly gives the source'
	OPT_MODULE = 'Specifies the module name'
	OPT_LIB = 'Specifies a file to be used as a library or a library directory'
	OPT_PREPROC = 'Applies the given preprocessor to the source'
	OPT_PASSES = 'Specifies the passes used in the compilation process. Passes are identified by the class name which is expected to be found in either lambdafactory.passes or lambdafactory.resolution modules, or is given as an absolute class name.'
	def __init__ (self, programName=None):
		self.programName = None
		self.environment = None
		if programName is None: programName = 'lambdaf'
		self.programName = programName
		self.createEnvironment()
		self.environment.loadLanguages()
		self.setupEnvironment()
	
	def runAsString(self, args):
		"""Runs Sugar, but instead of printing the result to the given
		output, it returns a Python string with the result. It is very useful
		when embedding LambdaFactory somewhere."""
		output=StringIO()
		self.run(args, output)
		return ('' + output.getvalue())
	
	def run(self, arguments, output=None):
		if output is None: output = sys.stdout
		if (type(arguments) != list):
			arguments = list(arguments)
		status=0
		option_parser=optparse.OptionParser()
		options=[]
		args=[]
		option_parser.add_option("-r", "--run",  action="store_true", dest="run", default=True,
			help=self.OPT_RUN)
		option_parser.add_option("-c", "--compile", action="store_true", dest="compile",
		help=self.OPT_COMPILE)
		option_parser.add_option("-R", "--runtime", action="store_true", dest="runtime",
		help=self.OPT_RUNTIME)
		option_parser.add_option("-l", "--lang", action="store", dest="lang",
			help=self.OPT_LANG)
		option_parser.add_option("-o", "--output", action="store", dest="output", 
			help=self.OPT_OUTPUT)
		option_parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
			help=self.OPT_VERBOSE)
		option_parser.add_option("-m", "--module", action="store", dest="module",
			help=self.OPT_MODULE)
		option_parser.add_option("-a", "--api", action="store", dest="api",
			help=self.OPT_API)
		option_parser.add_option("-p", "--preprocess", action="append", dest="preprocess", 
			help=self.OPT_PREPROC)
		option_parser.add_option("-t", "--test", action="store_true", dest="test", 
			help=self.OPT_TEST)
		option_parser.add_option("-s", "--source", action="store", dest="source", 
			help=self.OPT_SOURCE)
		option_parser.add_option("-D", "--define", action="append", dest="targets", 
			help=self.OPT_DEFINE)
		option_parser.add_option("-O", "--options", action="append", dest="passOptions", 
			help=self.OPT_OPTIONS)
		option_parser.add_option("-L", "--lib", action="append", dest="libraries", 
			help=self.OPT_LIB)
		option_parser.add_option("-P", "--passes", action="store", dest="passes", 
			help=self.OPT_PASSES)
		option_parser.add_option("-V", None, action="store", dest="version", 
			help=self.OPT_VERSION)
		options, args = option_parser.parse_args(args=arguments)
		
		language=options.lang
		if options.targets:
			for option_target in options.targets:
				self.environment.options[option_target] = True
		if options.api:
			self.environment.addPass(passes.DocumentationPass())
		if options.source:
			self.parseSource(args[0], options.source, options.module)
		elif True:
			if options.module:
				if (len(args) > 1):
					throw.Exception('Only one source file is accepted with the -m option')
			if options.libraries:
				for lib in options.libraries:
					if os.path.isfile(lib):
						self.parseFile(lib)
			for source_path in args:
				self.parseFile(source_path, options.module)
				if (not language):
					language = self.guessLanguage(source_path)
				elif True:
					language = self.environment.normalizeLanguage(language)
		if options.libraries:
			for l in options.libraries:
				self.environment.addLibraryPath(l)
		if (not language):
			raise ERR_NO_LANGUAGE_SPECIFIED
		if options.passes:
			self.setupPasses(language, options.passes.split(','), (options.passOptions or []))
		elif True:
			self.setupPasses(language, None, (options.passOptions or []))
		self.transformProgram()
		if options.api:
			html_documentation = self.environment.getPass('Documentation').asHTML()
			if (options.api == '-'):
				output.write(html_documentation)
			elif True:
				f=file(options.api, mode=('w'))
				f.write(html_documentation)
				f.close()
		elif options.compile:
			program_source=self.writeProgram(language, options.runtime)
			if (not options.output):
				output.write((program_source + '\n'))
			elif os.path.isdir(options.output):
				splitter=FileSplitter(options.output)
				splitter.fromString(program_source)
			elif True:
				f=file(options.output, mode=('a'))
				f.write(program_source)
		elif options.run:
			program_source=self.writeProgram(language, True)
			file_and_path=tempfile.mkstemp()
			os.write(file_and_path[0], program_source)
			os.close(file_and_path[0])
			args_str=' '.join(args[1:])
			interpreter=None
			path=file_and_path[1]
			compilers=None
			if (language in ['js', 'javascript']):
				interpreter = (os.getenv('SUGAR_JS') or 'rhino')
				command = ((((interpreter + ' ') + path) + ' ') + args_str)
			elif (language in ['pnuts']):
				interpreter = (os.getenv('SUGAR_PNUTS') or 'pnuts')
				command = ((((interpreter + ' ') + path) + ' ') + args_str)
			elif (language in ['python']):
				interpreter = (os.getenv('SUGAR_PYTHON') or 'python')
				command = ((((interpreter + ' ') + path) + ' ') + args_str)
			elif True:
				raise ERR_NO_RUNTIME_AVAILABLE(language)
			status = ((os.system(command) / 256) or status)
			os.unlink(path)
	
	def parseFile(self, sourcePath, moduleName=None):
		if moduleName is None: moduleName = None
		return self.environment.parseFile(sourcePath, moduleName)
	
	def parseSource(self, source, extension, moduleName=None):
		if moduleName is None: moduleName = None
		return self.environment.parseSource(source, extension, moduleName)
	
	def transformProgram(self):
		self.environment.runPasses()
	
	def guessLanguage(self, sourcePath):
		for name_and_value in self.environment.languages.items():
			if name_and_value[1].recognizes(sourcePath):
				return name_and_value[0]
		return None
	
	def setProgram(self, program):
		return self.environment.setProgram(program)
	
	def getProgram(self):
		return self.environment.getProgram()
	
	def writeProgram(self, inLanguage, includeRuntime=None):
		if includeRuntime is None: includeRuntime = False
		language=self.environment.loadLanguage(inLanguage)
		writer=language.writer()
		writer.report = self.environment.report
		writer.setEnvironment(self.environment)
		program_source=writer.run()
		if includeRuntime:
			program_source = (writer.getRuntimeSource() + program_source)
		return program_source
	
	def createEnvironment(self):
		self.environment = Environment()
	
	def setupEnvironment(self):
		pass
	
	def setupPasses(self, language=None, withPasses=None, options=None):
		if language is None: language = None
		if withPasses is None: withPasses = None
		if options is None: options = None
		if (not withPasses):
			if (((language == 'javascript') or (language == 'actionscript')) and (not ('NORUNTIME' in options))):
				self.environment.addPass(passes.ExtendJSRuntime())
			self.environment.addPass(passes.Importation())
			self.environment.addPass(resolution.BasicDataFlow())
			self.environment.addPass(resolution.DataFlowBinding())
		elif True:
			for the_pass in withPasses:
				if (the_pass.find('.') == -1):
					pass_class=None
					if hasattr(passes, the_pass):
						pass_class=getattr(passes, the_pass)
					elif hasattr(resolution, the_pass):
						pass_class=getattr(resolution, the_pass)
					elif True:
						self.environment.report.error('LambdaFactory standard pass not found:', the_pass)
						assert(None)
					self.environment.addPass(pass_class())
				elif True:
					module_name=the_pass[0:the_pass.rfind('.')]
					exec(('import ' + module_name))
					pass_class=eval(the_pass)
					if pass_class:
						self.environment.addPass(pass_class())
					elif True:
						self.environment.report.error('Custom pass not found:', the_pass)
						assert(None)
	

