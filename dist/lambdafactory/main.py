#8< ---[lambdafactory/main.py]---
#!/usr/bin/env python
# encoding: utf-8
""" Command-line interface and main module for LambdaFactory"""
import sys
__module__ = sys.modules[__name__]
import os, sys, optparse, tempfile
from lambdafactory.environment import Environment
from lambdafactory.splitter import FileSplitter
import lambdafactory.passes as passes
import lambdafactory.resolution as resolution
from io import BytesIO, TextIOBase
import sys
__module_name__ = 'lambdafactory.main'
def ensureOutput (value, output=None):
	self=__module__
	if output is None: output = None
	if sys.version_info.major >= 3:
		# For Python-3 we expect streams to take unicode
		if output and isinstance(output, TextIOBase):
			return value.decode("utf8") if isinstance(value, bytes) else value
		else:
			return value.encode("utf8") if not isinstance(value, bytes) else value
	else:
		# For Python-2 we expect streams to take bytes
		if isinstance(value,bytes): return str(value)
		return value.encode("utf8") if isinstance(value, unicode) else value


class Command:
	OPT_LANG = u'Specifies the target language (js, java, pnuts, actionscript)'
	OPT_OUTPUT = u'Specifies the output where the files will be generated (stdout, file or folder)'
	OPT_VERBOSE = u'Verbose parsing output (useful for debugging)'
	OPT_API = u'Generates SDoc API documentation (given the API filename)'
	OPT_TEST = u'Tells wether the source code is valid or not'
	OPT_DEFINE = u'Defines a specific target (for @specific)'
	OPT_OPTIONS = u'Options for program transformation passes'
	OPT_RUN = u'Directly runs the script (default)'
	OPT_COMPILE = u'Compiles the given code to the output (current) directory'
	OPT_RUNTIME = u'Outputs the runtime as well when compiled'
	OPT_VERSION = u'Ensures that Sugar is at least of the given version'
	OPT_SOURCE = u'Directly gives the source'
	OPT_INCLUDE_SOURCE = u'Includes source in compiled code'
	OPT_CACHE = u'Uses compilation cache'
	OPT_MODULE = u'Specifies the module name'
	OPT_LIB = u'Specifies a file to be used as a library or a library directory'
	OPT_INCLUDES = u'Specifies a file to be included in the copmilation output'
	OPT_PREPROC = u'Applies the given preprocessor to the source'
	OPT_PASSES = u'Specifies the passes used in the compilation process. Passes are identified by the class name which is expected to be found in either lambdafactory.passes or lambdafactory.resolution modules, or is given as an absolute class name.'
	def __init__ (self, programName=None):
		self.programName = None
		self.environment = None
		if programName is None: programName = u'lambdafactory'
		self.programName = programName
		self.createEnvironment()
		self.environment.loadLanguages()
		self.setupEnvironment()
	
	def runAsString(self, args):
		""" Runs Sugar, but instead of printing the result to the given
		 output, it returns a Python string with the result. It is very useful
		 when embedding LambdaFactory somewhere."""
		output=BytesIO()
		self.run(args, output)
		return output.getvalue().decode(u'utf-8')
	
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
		option_parser.add_option("-C", "--cache", action="store", dest="cache", default=True,
			help=self.OPT_CACHE)
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
		option_parser.add_option("-S", "--include-source", action="store_true", dest="includeSource",
			help=self.OPT_INCLUDE_SOURCE)
		option_parser.add_option("-D", "--define", action="append", dest="targets",
			help=self.OPT_DEFINE)
		option_parser.add_option("-O", "--options", action="append", dest="passOptions",
			help=self.OPT_OPTIONS)
		option_parser.add_option("-L", "--lib", action="append", dest="libraries",
			help=self.OPT_LIB)
		option_parser.add_option("-I", "--include", action="append", dest="includes",
			help=self.OPT_INCLUDES)
		option_parser.add_option("-P", "--passes", action="store", dest="passes",
			help=self.OPT_PASSES)
		option_parser.add_option("-V", None, action="store", dest="version",
			help=self.OPT_VERSION)
		options, args = option_parser.parse_args(args=arguments)
		language=options.lang
		program=self.environment.program
		if (options.cache in [u'no', u'none', u'false', u'/dev/null', False]):
			self.environment.useCache = False
		elif (options.cache in [u'yes', u'true', True]):
			self.environment.useCache = True
		elif True:
			self.environment.useCache = True
			self.environment.cache.setPath(options.cache)
		if os.environ.get(u'SUGAR_MODULES'):
			m=os.environ[u'SUGAR_MODULES']
			self.environment.options[u'modules'] = m
			self.environment.options[m] = True
		if os.environ.get(u'SUGAR_BACKEND'):
			self.environment.options[u'backend'] = os.environ[u'SUGAR_BACKEND']
		if options.targets:
			for option_target in options.targets:
				name_value=option_target.split(u'=', 1)
				if (len(name_value) == 1):
					self.environment.options[option_target] = True
				elif True:
					self.environment.options[name_target[0]] = name_target[1]
		if options.api:
			self.environment.addPass(passes.DocumentationPass())
		if options.includes:
			for i in options.includes:
				if os.path.isfile(i):
					parsed_module=self.parseFile(i)
					if parsed_module:
						program.addModule(parsed_module)
		if options.source:
			raise Exception(u'Not supported yet')
		elif True:
			if options.module:
				if (len(args) > 1):
					raise Exception(u'Only one source file is accepted with the -m option')
			for source_path in args:
				result_module=self.parseFile(source_path, options.module)
				if result_module:
					program.addModule(result_module)
				if (language == u'none'):
					language = None
				elif (not language):
					language = (self.environment.options.get(u'backend') or self.guessLanguage(source_path))
				elif True:
					language = self.environment.normalizeLanguage(language)
		if options.libraries:
			for l in options.libraries:
				if os.path.isfile(l):
					module=self.parseFile(l)
					if (not module):
						return None
					elif True:
						program.addModule(module)
						for name_and_value in module.getSlots():
							name_and_value[1].addAnnotation(self.environment.getFactory().annotation(u'shadow'))
				elif True:
					self.environment.addLibraryPath(l)
		if (language == u'none'):
			language = None
		if options.passes:
			self.setupPasses(language, options.passes.split(u','), (options.passOptions or []))
		elif True:
			self.setupPasses(language, None, (options.passOptions or []))
		if program.getModules():
			self.transformProgram(program)
		if options.api:
			doc_pass=self.environment.getPass(u'Documentation')
			doc_pass.setWriter(self.getWriter(u'js'))
			json_documentation = doc_pass.asJSON()
			if (options.api == u'-'):
				output.write(json_documentation)
			elif True:
				f=open(options.api, u'wb')
				f.write(ensureOutput(json_documentation, f))
				f.close()
		elif options.compile:
			program_source=self.writeProgram(program, language, options.runtime, options.includeSource)
			if (not options.output):
				output.write(ensureOutput(program_source, output))
				output.write(ensureOutput(u'\n', output))
			elif os.path.isdir(options.output):
				splitter=FileSplitter(options.output)
				splitter.fromString(program_source)
			elif True:
				f=open(options.output, u'ab')
				f.write(ensureOutput(program_source, f))
				f.close()
		elif options.run:
			program_source=self.writeProgram(program, language, True, options.includeSource)
			file_and_path=tempfile.mkstemp()
			f=open(file_and_path[0], u'wb')
			f.write(ensureOutput(program_source, f))
			f.close()
			args_str=u' '.join(args[1:])
			interpreter=None
			path=file_and_path[1]
			compilers=None
			command=None
			if (language in [u'js', u'javascript', u'es', u'ecmascript']):
				interpreter = (os.getenv(u'SUGAR_JS') or u'js')
				command = ((((interpreter + u' ') + path) + u' ') + args_str)
			elif (language in [u'python']):
				interpreter = (os.getenv(u'SUGAR_PYTHON') or u'python')
				command = ((((interpreter + u' ') + path) + u' ') + args_str)
			if command:
				status = ((os.system(command) / 256) or status)
			elif True:
				self.environment.report.error(u'No command defined to run language: {0}'.format(language))
			os.unlink(path)
		return program
	
	def parseFile(self, sourcePath, moduleName=None):
		if moduleName is None: moduleName = None
		return self.environment.parseFile(sourcePath, moduleName)
	
	def parseString(self, text, extension, moduleName=None):
		if moduleName is None: moduleName = None
		return self.environment.parseString(text, extension, moduleName)
	
	def transformProgram(self, program):
		self.environment.runPasses(program)
	
	def guessLanguage(self, sourcePath):
		for name_and_value in self.environment.languages.items():
			if name_and_value[1].recognizes(sourcePath):
				return name_and_value[0]
		return None
	
	def getWriter(self, language):
		if (not language):
			return None
		name=language
		language = self.environment.loadLanguage(language)
		if (language and language.writer):
			writer=language.writer()
			writer.report = self.environment.report
			writer.setEnvironment(self.environment)
			return writer
		elif True:
			self.environment.report.error(u'Language not defined: {0}'.format(name))
			return None
	
	def writeProgram(self, program, inLanguage, includeRuntime=None, includeSource=None):
		if includeRuntime is None: includeRuntime = False
		if includeSource is None: includeSource = False
		writer=self.getWriter(inLanguage)
		if writer:
			program_source=writer.run(program)
			if includeRuntime:
				program_source = (writer.getRuntimeSource() + program_source)
			return program_source
		elif True:
			return u''
	
	def createEnvironment(self):
		self.environment = Environment()
	
	def setupEnvironment(self):
		pass
	
	def setupPasses(self, language=None, withPasses=None, options=None):
		if language is None: language = None
		if withPasses is None: withPasses = None
		if options is None: options = None
		if (not withPasses):
			self.environment.addPass(passes.Importation())
			self.environment.addPass(passes.ControlFlow())
			self.environment.addPass(resolution.BasicDataFlow())
			self.environment.addPass(resolution.DataFlowBinding())
		elif True:
			for the_pass in withPasses:
				if (the_pass == u'std'):
					self.environment.addPass(passes.Importation())
					self.environment.addPass(passes.ControlFlow())
					self.environment.addPass(resolution.BasicDataFlow())
					self.environment.addPass(resolution.DataFlowBinding())
				elif (the_pass.find(u'.') == -1):
					pass_class=None
					if hasattr(passes, the_pass):
						pass_class = getattr(passes, the_pass)
					elif hasattr(resolution, the_pass):
						pass_class = getattr(resolution, the_pass)
					elif True:
						self.environment.report.error(u'LambdaFactory standard pass not found:', the_pass)
						assert(None)
					self.environment.addPass(pass_class())
				elif True:
					module_name=the_pass[0:the_pass.rfind(u'.')]
					exec((u'import ' + module_name))
					pass_class=eval(the_pass)
					if pass_class:
						self.environment.addPass(pass_class())
					elif True:
						self.environment.report.error(u'Custom pass not found:', the_pass)
						assert(None)
	

