# encoding: utf8
# -----------------------------------------------------------------------------
# Project   : LambdaFactory
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ffctn.com>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 2006-11-02
# Last mod  : 2016-12-07
# -----------------------------------------------------------------------------

# TODO: Cleanup the code generation by moving the templates to the top
#       and creating better generic functions
# TODO: When constructor is empty, should assign default attributes anyway
# TODO: Support optional meta-data
# TODO: Provide a global rewrite operation

from   lambdafactory.modelwriter import AbstractWriter, flatten
import lambdafactory.interfaces as interfaces
import lambdafactory.reporter   as reporter
from   lambdafactory.splitter import SNIP
from   lambdafactory.languages.javascript.externs import ExternsWriter
import os.path, re, time, string, random, json

#------------------------------------------------------------------------------
#
#  GLOBALS
#
#------------------------------------------------------------------------------

RE_TEMPLATE        = re.compile("\$\{[^\}]+\}")
VALID_SYMBOL       = re.compile("^[\$_A-Za-z][\$_A-Za-z0-9]*$")
VALID_SYMBOL_CHARS = "_0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

# NOTE: This is not the complete list of keywords for JavaScript, we removed
# some such as typeof, null, which may be used as functions/values in code.
# NOTE: removed catch, as it clashes with the Promise
KEYWORDS = """abstract break
case class let
continue const debugger default
enum export extends
final finally for
function goto if implements
import in
interface native new
package private protected
public return short static
super switch synchronized
throw throws transient
try var void
volatile while with""".replace("\n", " ").split()

MODULE_VANILLA = "vanilla"
MODULE_UMD     = "umd"
MODULE_GOOGLE  = "google"

OPTION_EXTERNS        = "externs"
OPTION_NICE           = "nice"

OPTION_EXTEND_ITERATE = "iterate"

OPTIONS = {
	"ENABLE_METADATA" : False,
	"INCLUDE_SOURCE"  : False,
}

JS_OPERATORS = {
	"and"   :"&&",
	"is"    :"===",
	"is not":"!==",
	"not"   :"!",
	"or"    :"||"
}


#------------------------------------------------------------------------------
#
#  WRITER
#
#------------------------------------------------------------------------------

class Writer(AbstractWriter):

	# The following generates short random variables. Note that it's not thread
	# safe.
	RNDVARLETTERS = "ijklmonpqrstuvwxyzabcdefgh"

	def __init__( self ):
		AbstractWriter.__init__(self)
		self.jsPrefix                = ""
		self.jsCore                  = "extend."
		self.jsSelf                  = "self"
		self.jsModule                = "__module__"
		self._moduleType             = None
		self.supportedEmbedLanguages = ["ecmascript", "js", "javascript"]
		self.inInvocation            = False
		self.options                 = {} ; self.options.update(OPTIONS)
		self._generatedVars          = [0]
		self._isNice                  = False

	def _getRandomVariable( self ):
		s = "__"
		i = self._generatedVars[0]
		c = self.RNDVARLETTERS
		l = len(c)
		while i >= l:
				s += c[i % l]
				i  = i / l
		s += c[i]
		self._generatedVars[0] += 1
		return s

	# FIXME: This is still not good enough
	def XXXX_getRandomVariable(self, suffix=0):
		"""Generates a new random variable."""
		for _ in self.RNDVARLETTERS:
			s = _ if suffix == 0 else _ + str(suffix)
			if s not in self._generatedVars[-1] and not self.resolve(s)[1]:
				self._generatedVars[-1].append(s)
				return s
		return self._getRandomVariable(suffix+1)

	def _reserveVariableNames( self, *names ):
		pass
		#self._generatedVars[-1] += names

	def pushVarContext( self, value ):
		# FIXME: This does not work properly
		self._generatedVars.append([])

	def popVarContext( self ):
		self._generatedVars.pop()

	def _extendGetMethodByName(self, name):
		return self.jsSelf + ".getMethod('%s') " % (name)

	def _extendGetClass(self, variable=None):
		return "%s.getClass()" % (variable or self.jsSelf)

	def _isSymbolValid( self, string ):
		"""Tells if the name of the symbol is valid, ie. not a keyword
		and matching the symbol regexp."""
		# FIXME: Warn if symbol is typeof, etc.
		res = not self._isSymbolKeyword(string) and VALID_SYMBOL.match(string) != None
		return res

	def _isSymbolKeyword( self, string ):
		return string in KEYWORDS

	def _rewriteSymbol( self, string ):
		"""Rewrites the given symbol so that it can be expressed in the target language."""
		# FIXME: This is used by the hack in writeReference
		if self._isSymbolValid(string):
			return string
		res = "_LF_"
		for letter in string:
			if letter not in VALID_SYMBOL_CHARS:
				res += str(ord(letter))
			else:
				res += letter
		return res

	def getRuntimeSource(s):
		"""Returns the JavaScript code for the runtime that is necassary to run
		the program."""
		this_file = os.path.abspath(__file__)
		js_runtime = os.path.join(os.path.dirname(this_file), "runtime.js")
		f = file(js_runtime, 'r') ; text = f.read() ; f.close()
		return text

	# =========================================================================
	# NAMES
	# =========================================================================

	def getLocalName( self, element ):
		"""Returns the "local" name for the element, which means the
		last part of a dot-separated name."""
		return element.getName().split(".")[-1]

	def getAbsoluteName( self, element, asList=False ):
		"""Returns the absolute name for the given element. This is the '.'
		concatenation of the individual names of the parents."""
		names = element.getName().split(".")
		if len(names) > 1: return names if asList else ".".join(names)
		while element.getParent():
			element = element.getParent()
			# FIXME: Some elements may not have a name
			if isinstance(element, interfaces.IModule):
				# TODO: Should be able to detect a reference to the current module
				names = element.getName().split(".") + names
			elif not isinstance(element, interfaces.IProgram):
				names.insert(0, element.getName())
		return names if asList else ".".join(names)

	def getSafeName( self, element ):
		"""Returns the same as absolute name but with `_` instead of `_`."""
		return "_".join(self.getAbsoluteName(element, asList=True))

	def getResolvedName( self, element ):
		"""Returns the absolute name of the element, resolved in the current
		module. The rules are as follows:

		- If the element is in scope: local name
		- If the element is in scope but shadowed:
		  - if it belongs to the local module, it will be prefixed by the module
			name
		  - if it belongs to an imported module, it will be prefixed by the
		    imported module name
		  - otherwise its absolute name will be used.
		"""
		assert isinstance(element, interfaces.IReferencable)
		dataflow       = self.getCurrentDataFlow()
		local_name     = self.getLocalName(element)
		resolved_slot, resolved_value  = self.resolve(local_name)
		resolved       = resolved_value == element
		resolved_local = self.getCurrentDataFlow().getSlotValue(local_name) == element
		element_module = self.getModuleFor(element)
		if resolved_local:
			# If we can resolve the value locally, then we simply return
			# the slot name
			return local_name
		elif element == self.getCurrentModule():
			name = self.getSafeName(element_module)
			if self.isShadowed(name, element_module):
				return "__module__"
			else:
				return name
		elif element_module == self.getCurrentModule():
			# We're in the current module, then we used the resolved
			# name for the current module and append the local name
			name = self.getSafeName(element_module)
			if self.isShadowed(name, element_module):
				return "__module__." + local_name
			else:
				return name + "." + local_name
		elif element_module and element_module != element:
			parent_name = self.getResolvedName(element_module)
			if self.isShadowed(parent_name, element_module):
				parent_name = self.getAbsoluteName(element_module)
			return parent_name + "." + local_name
		else:
			return self.getAbsoluteName(element)

	# =========================================================================
	# MODULES
	# =========================================================================

	def onModule( self, moduleElement ):
		"""Writes a Module element."""
		# Detects the module type
		if self.environment.options.get(OPTION_EXTERNS):
			self._externs = ExternsWriter()
		else:
			self._externs = None
		self._isNice = self.environment.options.get(OPTION_NICE)
		if self.environment.options.get(MODULE_UMD):
			self._moduleType = MODULE_UMD
		elif self.environment.options.get(MODULE_GOOGLE):
			self._moduleType = MODULE_GOOGLE
		else:
			self._moduleType = MODULE_VANILLA
		self._withExtendIterate = self.environment.options.get(OPTION_EXTEND_ITERATE) and True or False
		module_name             = self.getSafeName(moduleElement)
		full_name               = self.getAbsoluteName(moduleElement)
		code = [
			"// " + SNIP % ("%s.js" % (self.getAbsoluteName(moduleElement).replace(".", "/"))),
		] + self._header() + [
			self._document(moduleElement),
			self.options["ENABLE_METADATA"] and "function __def(v,m){var ms=v['__def__']||{};for(var k in m){ms[k]=m[k]};v['__def__']=ms;return v}" or None,
		]
		# --- PREFIX ----------------------------------------------------------
		if self._moduleType == MODULE_UMD:
			code.extend(self.getModuleUMDPrefix(moduleElement))
		elif self._moduleType == MODULE_GOOGLE:
			code.extend(self.getModuleGooglePrefix(moduleElement))
		else:
			code.extend(self.getModuleVanillaPrefix(moduleElement))
		# --- VERSION ---------------------------------------------------------
		version = moduleElement.getAnnotation("version")
		if version:
			code.append("%s.__VERSION__='%s';" % (module_name, version.getContent()))
		# --- SLOTS -----------------------------------------------------------
		for name, value in moduleElement.getSlots():
			if isinstance(value, interfaces.IModuleAttribute):
				declaration = "{2}{0}.{1};".format(module_name, self.write(value), self._docextern(value))
			else:
				# NOTE: Some slot values may be shadowed, in which case they
				# won't return any value
				value_code = self.write(value)
				if value_code:
					slot_name     = name
					declaration   = ""
					if slot_name == interfaces.Constants.ModuleInit:
						slot_name = "init"
						if self._isNice:
							declaration = "\n".join(self._section("Module init")) + "\n"
					if slot_name == interfaces.Constants.MainFunction:
						# FIXME: Technically, this should be moved after the init
						slot_name = "main"
						if self._isNice:
							declaration = "\n".join(self._section("Module main")) + "\n"

					declaration   += "{3}{0}.{1} = {2}".format(module_name, slot_name, value_code, self._docextern(value))
			code.append(self._document(value))
			code.append(declaration)
		# --- INIT ------------------------------------------------------------
		# FIXME: Init should be only invoked once
		if self._moduleType != MODULE_VANILLA:
			code.extend(self.registerModuleInWindow(moduleElement))
		if self._isNice:
			code += self._section("Module initialization code")
			code += [
				"// NOTE: This is called after the registration, as init code might",
				"// depend on the module to be registered (eg. dynamic loading)."
			]
		code.append('if (typeof(%s.init)!="undefined") {%s.init();}' % (
			module_name,
			module_name
		))
		# --- SOURCE ----------------------------------------------------------
		# We append the source code
		if self.options.get("INCLUDE_SOURCE"):
			source = moduleElement.getSource()
			if source:
				# NOTE: The source is prefixed with the URL scheme
				source = source.split("://",1)[-1]
				if os.path.exists(source):
					with open(source) as f:
						code.append("%s.__source__=%s;" % (module_name, json.dumps(f.read())))
		# --- SUFFIX ----------------------------------------------------------
		# We add the suffix
		if self._moduleType == MODULE_UMD:
			code.extend(self.getModuleUMDSuffix(moduleElement))
		elif self._moduleType == MODULE_GOOGLE:
			code.extend(self.getModuleGoogleSuffix(moduleElement))
		else:
			code.extend(self.getModuleVanillaSuffix(moduleElement))
		# --- RESULT ----------------------------------------------------------
		return self._format(*code)

	# === VANILLA MODULES =====================================================

	def getModuleVanillaPrefix( self, moduleElement ):
		local_name  = self.getLocalName(moduleElement)
		full_name   = self.getAbsoluteName(moduleElement)
		module_name = self.getSafeName(moduleElement)
		safe_name   = module_name
		declaration = []
		names       = full_name.split(".")
		if len(names) == 1:
			declaration.append("var {0}=typeof(extend)!='undefined' ? "
				"extend.module('{0}') : (typeof({0})!='undefined' ? {0} : "
				"{{}});".format(local_name))
		else:
			parents = []
			current = names[-1]
			for i,prefix in enumerate(names):
				parents.append(prefix)
				parent_abs_name      = ".".join(parents)
				parent_safe_name = "_".join(parents)
				declaration.append(
					"var {0}=typeof(extend)!='undefined' ? "
					"extend.module('{1}') : (typeof({1})!='undefined' ? {1} : "
					"{{}});".format(parent_safe_name, parent_abs_name))
				if i > 0:
					declaration.append("if (typeof({0})==='undefined') {{{0}={1};}};".format(
						parent_abs_name,
						parent_safe_name,
					))


		# FIXME: This could be refactored to follow the other module types
		symbols = []
		for alias, module, slot, op in self.getImportedSymbols(moduleElement):
			if not slot:
				# Modules are already imported
				if alias:
					symbols.append("var {0} = {1};".format(alias or module, module))
			else:
				# Extend gets a special treatment
				if module != "extend" or alias:
					symbols.append("var {0} = {1}.{2};".format(alias or slot, module, slot))
		return [
			"// START:VANILLA_PREAMBLE",
		] + declaration + [
			"(function({0}){{".format(safe_name),
		] + symbols + [
			"var {0}={1};".format(self.jsModule, safe_name),
			"// END:VANILLA_PREAMBLE\n"
		]

	def getModuleVanillaSuffix( self, moduleElement ):
		safe_name = self.getAbsoluteName(moduleElement).replace(".", "_")
		return [
			"\n// START:VANILLA_POSTAMBLE",
			"return {0};}})({0});".format(safe_name),
			"// END:VANILLA_POSTAMBLE",
		]

	# === UMD MODULES =========================================================

	def getModuleUMDPrefix( self, moduleElement):
		# SEE: http://babeljs.io/docs/plugins/transform-es2015-modules-umd/
		module_name = self.getSafeName(moduleElement)
		abs_name    = self.getAbsoluteName(moduleElement)
		imported    = self.getImportedModules(moduleElement)
		imports     = (", " + ", ".join(['"' + _ + '"' for _ in imported])) if imported else ""
		preamble = """// START:UMD_PREAMBLE
		(function (global, factory) {
			if (typeof define === "function" && define.amd) {
				return define(["require", "exports" IMPORTS], factory);
			} else if (typeof exports !== "undefined") {
				return factory(require, exports);
			} else {
				var module  = {exports:{}};
				var require = function(_){
					_=_.split(".");_.reverse();
					var c=global;
					while (c && _.length > 0){c=c[_.pop()]}
					return c;
				}
				factory(require, module.exports);
				global.actual = module.exports;
				return module.exports;
			}
		})(this, function (require, exports) {""".replace(
			"MODULE", module_name
		).replace(
			"IMPORTS", imports
		).replace("\n\t\t", "\n")
		module_declaration = [
			"var __module__ = typeof(exports)==='undefined' ? {} : exports;",
			"var {0} = __module__;".format(module_name),
		]
		symbols = []
		for alias, module, slot, op in self.getImportedSymbols(moduleElement):
			safe_module = module.replace(".", "_")
			if not slot:
				# Modules are already imported
				if alias:
					symbols.append("var {0} = {1};".format(alias or safe_module, safe_module))
			else:
				# Extend gets a special treatment
				if module != "extend" or alias:
					symbols.append("var {0} = {1}.{2};".format(alias or slot, safe_module, slot))
		return [
			preamble.replace("MODULE", module_name).replace("IMPORT", imports),
		] + [
			"var {0} = require(\"{1}\");".format(_.replace(".","_"), _) for _ in imported
		] + symbols + module_declaration + ["// END:UMD_PREAMBLE\n"]

	def getModuleUMDSuffix( self, moduleElement ):
		module_name = self.getSafeName(moduleElement)
		abs_name    = self.getAbsoluteName(moduleElement)
		return [
			"\n// START:UMD_POSTAMBLE",
			"return {0}}})".format(module_name),
			"// END:UMD_POSTAMBLE"
		]

	# === GOOGLE MODULES ======================================================
	# https://github.com/google/closure-library/wiki/goog.module:-an-ES6-module-like-alternative-to-goog.provide

	def getModuleGooglePrefix( self, moduleElement):
		module_name = self.getSafeName(moduleElement)
		abs_name    = self.getAbsoluteName(moduleElement)
		# NOTE: We prevent modules from importing themselves
		modules     = ["var {1} = goog.require('{0}');".format(_, _.replace(".", "_")) for _ in self.getImportedModules(moduleElement) if _ != abs_name]
		symbols     = []
		for alias, module, slot, op in self.getImportedSymbols(moduleElement):
			if module == abs_name:
				continue
			elif not slot:
				# Modules are already imported
				if alias:
					symbols.append("var {0} = {1};".format(alias or module.replace(".", "_"), module.replace(".", "_")))
			else:
				# Extend gets a special treatment
				if module != "extend" or alias:
					symbols.append("var {0} = {1}.{2};".format(alias or slot, module.replace(".", "_"), slot))
		symbols = list(set(symbols))
		prefix  = []
		if self._isNice:
			prefix  = [
				"// Defines the gmodule, imports its dependencies and binds imported",
				"// imported symbols to corresponding slots within the module's namespace."
			]
		return [
			"// START:GOOGLE_PREAMBLE",
		] + prefix + [
			"goog.loadModule(function(exports){",
			"goog.module('{0}');".format(abs_name),
		] + modules + symbols + [
			"var {0} = exports;".format(module_name),
			"var __module__ = {0};".format(module_name),
			"// END:GOOGLE_PREAMBLE"
		]

	def getModuleGoogleSuffix( self, moduleElement ):
		module_name = self.getSafeName(moduleElement)
		abs_name    = self.getAbsoluteName(moduleElement)
		declaration = []
		return [
			"\n// START:GOOGLE_POSTAMBLE",
			"return __module__;})",
			"// END:GOOGLE_POSTAMBLE"
		]


	def registerModuleInWindow( self, moduleElement ):
		safe_name = self.getSafeName(moduleElement)
		names     = self.getAbsoluteName(moduleElement, asList=True)
		res       = ["var c = window;"]
		last      = len(names) - 1
		for i,name in enumerate(names):
			if i<last:
				line = "c = c.{0} = c.{0} || {{}};".format(name)
			else:
				line = "c.{0} = __module__".format(name)
			res.append(line)
		return (self._section("Module registration") if self._isNice else []) + [
			"// Registers the module in `extend`, if available" if self._isNice else None,
			"if (typeof extend !== 'undefined') {{extend.module(\"{0}\", {1})}}".format(".".join(names), safe_name),
			"// Registers the module in the globals, creating any submodule if necessary" if self._isNice else None,
			"if (typeof window !== 'undefined') {",
			res,
			"}"
		]

	# =========================================================================
	# IMPORTS
	# =========================================================================

	def onImportOperation( self, importElement):
		return self._format("")

	# =========================================================================
	# CLASS
	# =========================================================================

	def onClass( self, classElement ):
		"""Writes a class element."""
		parents = self.getClassParents(classElement)
		parent  = "undefined"
		if len(parents) == 1:
			parent_class = parents[0]
			if isinstance(parent_class, interfaces.IClass):
				parent = self.getResolvedName(parent_class)
			else:
				assert isinstance(parent_class, interfaces.IReference)
				parent = self.write(parent_class)
		elif len(parents) > 1:
			raise Exception("JavaScript back-end only supports single inheritance")
		# We create a map of class methods, including inherited class methods
		# so that we can copy the implementation of these
		classOperations = {}
		# NOTE: This is not necessary since Extend-3.1
		# for name, method in classElement.getInheritedClassMethods().items():
		# 	# FIXME: Maybe use wrapper instead
		# 	classOperations[name] = self._writeClassMethodProxy(classElement, method)
		# Here, we've got to cheat a little bit. Each class method will
		# generate an '_imp' suffixed method that will be invoked by the
		for meth in classElement.getClassMethods():
			classOperations[self._rewriteSymbol(meth.getName())] = meth
		classOperations = list(classOperations.values())
		classAttributes = {}
		for attribute in classElement.getClassAttributes():
			classAttributes[self._rewriteSymbol(attribute.getName())] = self.write(attribute)
		classAttributes = list(classAttributes.values())
		# === RESULT ==========================================================
		result = []
		result.append(           "name  :'%s'," % (self.getAbsoluteName(classElement)))
		if parent: result.append("parent: %s," % (parent))
		# We collect class attributes
		attributes   = classElement.getAttributes()
		constructors = classElement.getConstructors()
		destructors  = classElement.getDestructors()
		methods      = classElement.getInstanceMethods()
		if classAttributes:
			result += self._group("Class attributes", 1)
			written_attrs = ",\n".join(map(self.write, classAttributes))
			result.append("shared: {")
			result.append([written_attrs])
			result.append("},")
		if attributes:
			# In attributes, we only print the name, ans use Undefined as the
			# value, because properties will be instanciated at construction
			result += self._group("Properties", 1)
			written_attrs = ",\n".join(["%s:undefined" % (self._rewriteSymbol(e.getName())) for e in attributes])
			result.append("properties: {")
			result.append([written_attrs])
			result.append("},")
		if classOperations:
			result += self._group("Class methods", 1)
			written_ops = ",\n".join(map(self.write, classOperations))
			result.append("operations:{")
			result.append([written_ops])
			result.append("},")
		if constructors:
			result += self._group("Constructor", 1)
			assert len(constructors) == 1, "Multiple constructors are not supported yet"
			result.append("%s," % (self.write(constructors[0])))
		else:
			# We write the default constructor, see 'onConstructor' for for
			# details.
			constructor_attributes    = []
			invoke_parent_constructor = None
			# FIXME: Implement proper attribute initialization even in
			# subclasses
			if len(parents) > 0:
				# We have to do the following JavaScript code because we're not
				# sure to know the parent constructors arity -- this is just a
				# way to cover our ass. We encapsulate the __super__ declaration
				# in a block to avoid scoping problems.
				invoke_parent_constructor = "".join([
					"// Invokes the parent constructor ― this requires the parent to be an extend.Class class",
					"\tif (true) {var __super__=",
					"%s.getSuper(%s.getParent());" % (self.jsSelf, self.getResolvedName(classElement)),
					"__super__.initialize.apply(__super__, arguments);}"
				])
			for a in classElement.getAttributes():
				if not a.getDefaultValue(): continue
				constructor_attributes.append(
					"// Default value for property `{0}`".format(a.getName())
				)
				constructor_attributes.append(
					"if (typeof(%s.%s)=='undefined') {%s.%s = %s;};" % (
						self.jsSelf, self._rewriteSymbol(a.getName()),
						self.jsSelf, self._rewriteSymbol(a.getName()),
						self.write(a.getDefaultValue())
				))
			# We only need a default constructor when we have class attributes
			# declared and no constructor declared
			default_constructor = self._format(
				(
					self.options["ENABLE_METADATA"] and "initialize: __def(function(){" \
					or "initialize: function(){"
				),
				["var %s = this;" % (self.jsSelf)],
				constructor_attributes or None,
				invoke_parent_constructor,
				(
					(not self.options["ENABLE_METADATA"] and "},") or \
					"}, {arguments:[]),"
				)
			)
			# in case no constructor is given, we create a default constructor
			result += self._group("Constructor", 1)
			result.append(default_constructor)
		if destructors:
			result += self._group("Destructor", 1)
			assert len(destructors) == 1, "Multiple destructors are not supported"
			result.append("%s," % (self.write(destructors[0])))
		if methods:
			result += self._group("Methods", 1)
			written_meths = ",\n\n".join(map(self.write, methods))
			result.append("methods: {")
			result.append([written_meths])
			result.append("},")
		if result[-1][-1] == ",":result[-1] =result[-1][:-1]
		return self._format(
			"extend.Class({",
			result,
			"})"
		)

	def onAttribute( self, element ):
		default_value = element.getDefaultValue()
		if default_value: default_value = self.write(default_value)
		else: default_value="undefined"
		return self._format(
			self._document(element),
			"%s: %s" % (self._rewriteSymbol(element.getName()), default_value)
		)

	def onClassAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			res = "%s: %s" % (self._rewriteSymbol(element.getName()), self.write(default_value))
		else:
			res = "%s: undefined" % (self._rewriteSymbol(element.getName()))
		return self._format(self._document(element), res)

	def onModuleAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			default_value = self.write(default_value)
			return self._format(
				self._document(element),
				"%s = %s" % (self._rewriteSymbol(element.getName()), default_value)
			)
		else:
			return self._format(
				self._document(element),
				"%s;" % (self._rewriteSymbol(element.getName()))
			)

	def onMethod( self, methodElement ):
		"""Writes a method element."""
		self.pushVarContext(methodElement)
		method_name = self._rewriteSymbol(methodElement.getName())
		if method_name == interfaces.Constants.Constructor: method_name = "init"
		if method_name == interfaces.Constants.Destructor:  method_name = "cleanup"
		res = self._format(
			self._document(methodElement),
			(
				self.options["ENABLE_METADATA"] and "%s:__def(function(%s) {" \
				or "%s: function(%s) {"
			) % (
				method_name,
				", ".join(map(self.write, methodElement.getParameters()))
			),
			["var %s = this;" % (self.jsSelf)],
			self._writeClosureArguments(methodElement),
			self.writeFunctionWhen(methodElement),
			self.writeFunctionPre(methodElement),
			list(map(self.write, methodElement.getOperations())),
			(
				(not self.options["ENABLE_METADATA"] and "}") or \
				"}, %s)" % ( self._writeFunctionMeta(methodElement))
			)
		)
		self.popVarContext()
		return res

	def _writeFunctionMeta( self, function ):
		arguments = []
		arity     = 0
		for arg in function.getParameters():
			a = {"name":self._rewriteSymbol(arg.getName())}
			if arg.isOptional():
				a["flags"] = "?"
			elif arg.isRest():
				a["flags"] = "*"
			elif arg.isKeywordsRest():
				a["flags"] = "**"
			elif arg.getDefaultValue():
				a["flags"] = "="
			arguments.append(a)
		return "{arguments:%s}" % (arguments)

	def _writeLValue( self, lvalue ):
		if isinstance(lvalue, interfaces.IAccessOperation):
			target = lvalue.getOpArgument(0)
			index  = lvalue.getIndex()
			if isinstance(index, interfaces.IString) or (isinstance(index, interfaces.INumber) and index.getActualValue() >= 0):
				return "{0}[{1}]".format(self.write(target), self.write(index))
			elif isinstance(index, interfaces.INumber):
				return "{0}[extend.len({0}) {1}]".format(self.write(lvalue.getOpArgument(0)), self.write(index))
			else:
				# FIXME: This does not work all the time
				# return "var __lf_a={0};__lf_a[extend.offset(__lf_a,{1})]".format(self.write(lvalue.getOpArgument(0)), self.write(index))
				return self.write(lvalue)
		else:
			return self.write(lvalue)

	def writeFunctionWhen(self, methodElement):
		return [self.write(
			"if (!({0})) {{return undefined}};".format(self.write(_.content))
		) for _ in methodElement.getAnnotations("when")]

	def writeFunctionPre(self, methodElement):
		return ["extend.assert({0}, 'Precondition failed in {1}):".format(self.write(_.content), self.getScopeName()) for _ in methodElement.getAnnotations("pre")]

	def onClassMethod( self, methodElement ):
		"""Writes a class method element."""
		self.pushVarContext(methodElement)
		method_name = self._rewriteSymbol(methodElement.getName())
		args        = methodElement.getParameters()
		res = self._format(
			self._document(methodElement),
			(
				self.options["ENABLE_METADATA"] and "%s:__def(function(%s){" \
				or "%s: function( %s ){"
			) % (method_name, ", ".join(map(self.write, args))),
			["var %s = this;" % (self.jsSelf)], #, self.getAbsoluteName(methodElement.getParent()))],
			self._writeClosureArguments(methodElement),
			self.writeFunctionWhen(methodElement),
			list(map(self.write, methodElement.getOperations())),
			(
				(not self.options["ENABLE_METADATA"] and "}") or \
				"},%s)" % ( self._writeFunctionMeta(methodElement))
			)
		)
		self.popVarContext()
		return res

	def _writeClassMethodProxy(self, currentClass, inheritedMethodElement):
		"""This function is used to wrap class methods inherited from parent
		classes, so that inheriting operations from parent classes works
		properly. This may look a bit dirty, but it's the only way I found to
		implement this properly"""
		method_name = self._rewriteSymbol(inheritedMethodElement.getName())
		method_args = inheritedMethodElement.getParameters()
		return self._format(
			(
				self.options["ENABLE_METADATA"] and "%s:__def(function(%s){" \
				or "%s: function( %s ){"
			) % (method_name, ", ".join(map(self.write, method_args))),
			["return %s.%s.apply(%s, arguments);" % (
				self.getAbsoluteName(inheritedMethodElement.getParent()),
				method_name,
				self.getAbsoluteName(currentClass)
			)],
			(
				(not self.options["ENABLE_METADATA"] and "}") or \
				"}, %s)" % ( self._writeFunctionMeta(inheritedMethodElement))
			)
		)

	def onConstructor( self, element ):
		"""Writes a constructor element"""
		self.pushVarContext(element)
		current_class = self.getCurrentClass()
		attributes    = []
		# FIXME: Same as onClass
		for a in current_class.getAttributes():
			if not a.getDefaultValue(): continue
			name = self._rewriteSymbol(a.getName())
			attributes.append("// Default initialization of property `{0}`".format(name))
			attributes.append("if (typeof(%s.%s)=='undefined') {%s.%s = %s;};" % (
				self.jsSelf, name,
				self.jsSelf, name,
				self.write(a.getDefaultValue()))
			)
		res = self._format(
			self._document(element),
			(
				self.options["ENABLE_METADATA"] and "initialize: __def(function( %s ){" \
				or "initialize: function( %s ){"
			)  % (
				", ".join(map(self.write, element.getParameters()))
			),
			["var %s = this;" % (self.jsSelf)],
			self._writeClosureArguments(element),
			attributes or None,
			list(map(self.write, element.getOperations())),
			(
				(not self.options["ENABLE_METADATA"] and "}") or \
				"}, %s)" % ( self._writeFunctionMeta(element))
			)
		)
		self.popVarContext()
		return res

	# =========================================================================
	# FUNCTIONS
	# =========================================================================

	def onFunctionWhen(self, function ):
		res = []
		for a in function.getAnnotations(withName="when"):
			res.append("if (!(%s)) {return}" % (self.write(a.getContent())))
		return self._format(res) or None

	def onFunctionPost(self, function ):
		res = []
		for a in function.getAnnotations(withName="post"):
			res.append("if (!(%s)) {throw new Exception('Assertion failed')}" % (self.write(a.getContent())))
		return self._format(res) or None

	def onFunction( self, function ):
		"""Writes a function element."""
		self.pushVarContext(function)
		parent = function.getParent()
		name   = self._rewriteSymbol( function.getName() )
		if parent and isinstance(parent, interfaces.IModule):
			res = [
				(
					self.options["ENABLE_METADATA"] and "__def(function(%s) {" \
					or "function(%s){"
				)  % (
					", ".join(map(self.write, function.getParameters()))
				),
				[self._document(function)],
				['var %s = %s;' % (self.jsSelf, self.getResolvedName(function.parent))],
				self._writeClosureArguments(function),
				self.writeFunctionWhen(function),
				list(map(self.write, function.getOperations())),
				(
					(not self.options["ENABLE_METADATA"] and "}") or \
					"}, %s)" % ( self._writeFunctionMeta(function))
				)
			]
		else:
			res = [
				self._document(function),
				(
					self.options["ENABLE_METADATA"] and "__def(function(%s) {" \
					or "function(%s) {"
				)  % (
					", ".join(map(self.write, function.getParameters()))
				),
				self._writeClosureArguments(function),
				self.writeFunctionWhen(function),
				list(map(self.write, function.getOperations())),
				(
					(not self.options["ENABLE_METADATA"] and "}") or \
					"}, %s)" % ( self._writeFunctionMeta(closure))
				)
			]
		if function.getAnnotations(withName="post"):
			res[0] = "var __wrapped__ = " + res[0] + ";"
			if parent and isinstance(parent, interfaces.IModule):
				res.insert(0, 'var %s=%s;' % (self.jsSelf, self.getAbsoluteName(parent)))
			res.append("var result = __wrapped__.apply(%s, arguments);" % (self.jsSelf))
			res.append(self.writeFunctionPost(function))
			res.append("return result;")
		self.popVarContext()
		return self._format(*res)

	# =========================================================================
	# CLOSURES
	# =========================================================================

	def onClosure( self, closure, bodyOnly=False, transpose=None ):
		"""Writes a closure element. The `transpose` element is used
		to rename parameters when there is an `encloses` annotation in
		an iteration loop.
		"""
		operations = closure.getOperations ()
		if bodyOnly:
			result = [self.write(_) + ";" for _ in operations]
		else:
			result   = [
				self._document(closure),
				(
					self.options["ENABLE_METADATA"] and "__def(function(%s) {" \
					or "function(%s) {"
				) % ( ", ".join(map(self.write, closure.getArguments()))),
				self._writeClosureArguments(closure),
				list(map(self.write, operations)),
				(
					(not self.options["ENABLE_METADATA"] and "}") or \
					"}, %s)" % ( self._writeFunctionMeta(closure))
				)
			]
		# We format the result as a string
		result = self._format(*result)
		# If the closure has `encloses` annotation, it means that we need
		# to capture its environment, because JS only has function-level
		# scoping.
		encloses = closure.getAnnotation("encloses")
		if encloses:
			# The scope will be a map containing the current enclosed values. We
			# get the list of names of enclosed variables.
			transpose = transpose or {}
			enclosed = list(encloses.content.keys())
			# There might be a `transpose` parameter to rename the variables
			transposed = [transpose.get(_) or _ for _ in enclosed]
			# We create a scope in which we're going to copy the value of the variables
			# This is *fairly ugly*, but it's easier for now as otherwise we
			# would need to do rewriting of variables/arguments
			# NOTE: We do not return the result, it should be managed in the
			# code itself.
			# If the closure body terminates, we return the value as well
			#if operations and isinstance(operations[-1], interfaces.ITermination):
			if not bodyOnly: result = "return ("+result+")"
			result = "(function({0}){{{2}}}({1}))".format(
				", ".join(enclosed),
				", ".join(transposed),
				result
			)
		return result

	def onClosureBody(self, closure):
		return self._format('{', list(map(self.write, closure.getOperations())), '}')

	def _writeClosureArguments(self, closure):
		# NOTE: Don't forget to update in AS backend as well
		i = 0
		l = len(closure.getParameters())
		result = []
		for param in closure.getParameters():
			arg_name = self.write(param)
			if param.isRest():
				assert i >= l - 2
				result.append("%s = %s(arguments,%d)" % (
					arg_name,
					self.jsPrefix + self.jsCore + "sliceArguments",
					i
				))
			if not (param.getDefaultValue() is None):
				result.append("if ({0} === undefined) {{{0}={1}}}".format(
					arg_name,
					self.write(param.getDefaultValue()),
				))
			i += 1
		return result


	# =========================================================================
	# BLOCKS
	# =========================================================================

	def onBlock( self, block ):
		"""Writes a block element."""
		return self._format(list(map(self.write, block.getOperations())))

	def onParameter( self, param ):
		"""Writes a parameter element."""
		return "%s" % (self._rewriteSymbol(param.getName()))

	def onReference( self, element ):
		"""Writes an argument element."""
		symbol_name = element.getReferenceName()
		slot, value = self.resolve(symbol_name)
		if slot:
			scope = slot.getDataFlow().getElement()
		else:
			scope = None
		if symbol_name == "self":
			return self.jsSelf
		elif symbol_name == "target":
			return "this"
		elif symbol_name == "__class__":
			# FIXME: Submodule support
			return self._rewriteSymbol(self.getCurrentClass().getName())
		elif symbol_name == "__module__":
			return "__module__"
		elif symbol_name == "__scope__":
			return json.dumps(self.getScopeName())
		elif symbol_name == "__name__":
			return json.dumps(self.getCurrentName(-1) or "''")
		elif symbol_name == "Undefined":
			return "undefined"
		elif symbol_name == "True":
			return "true"
		elif symbol_name == "False":
			return "false"
		elif symbol_name == "None":
			return "null"
		elif symbol_name == "super":
			if self.isIn(interfaces.IClassAttribute) or self.isIn(interfaces.IClassMethod):
				c = self.getCurrentClass()
				p = self.getClassParents(c)
				# FIXME: Submodule support
				if p:
					return self.getAbsoluteName(p[0])
				else:
					return symbol_name
			else:
				assert self.resolve("self"), "Super must be used inside method"
				# FIXME: Should check that the element has a method in parent scope
				# FIXME: Submodule support
				return "%s.getSuper(%s.getParent())" % (
					self.jsSelf,
					self.getResolvedName(self.getCurrentClass())
				)
		elif value == self.getCurrentModule():
			return "__module__"

		if not self._isSymbolValid(symbol_name):
			# FIXME: This is temporary, we should have an AbsoluteReference
			# operation that uses symbols as content
			symbol_name = ".".join(map(self._rewriteSymbol, symbol_name.split(".")))

		# If there is no scope, then the symmbol is undefined
		if not scope:
			if symbol_name == "print": return self.jsPrefix + self.jsCore + "print"
			else: return symbol_name
		# If the slot is imported
		elif slot.isImported():
			return self._onImportedReference(symbol_name, slot)
		# It is a method of the current class
		elif self.getCurrentClass() == scope or scope in self.getCurrentClassAncestors():
			if isinstance(value, interfaces.IInstanceMethod):
				# Here we need to wrap the method if they are given as values (
				# that means used outside of direct invocations), because when
				# giving a method as a callback, the 'this' pointer is not carried.
				if self.inInvocation:
					return "%s.%s" % (self.jsSelf, symbol_name)
				else:
					return self._extendGetMethodByName(symbol_name)
			elif isinstance(value, interfaces.IClassMethod):
				if self.isIn(interfaces.IInstanceMethod):
					return self._extendGetClass() + ".getOperation('%s')" % (symbol_name)
				else:
					return "%s.%s" % (self.jsSelf, symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				if self.isIn(interfaces.IClassMethod):
					return "%s.%s" % (self.jsSelf, symbol_name)
				else:
					return self._extendGetClass() + "." + symbol_name
			else:
				return self.jsSelf + "." + symbol_name
		# It is a local variable
		elif self.getCurrentFunction() == scope:
			return symbol_name
		# It within the current module
		elif self.getCurrentModule() == scope:
			return "__module__." + symbol_name
		# It is a property of a module
		elif isinstance(scope, interfaces.IModule):
			names = [self._rewriteSymbol(scope.getName()), symbol_name]
			while scope.getParent():
				scope = scope.getParent()
				if not isinstance(scope, interfaces.IProgram):
					names.insert(0, self._rewriteSymbol(scope.getName()))
			return ".".join(names)
		# It is a property of a class
		elif isinstance(scope, interfaces.IClass):
			# And the class is one of the parent class
			if scope in self.getCurrentClassAncestors():
				return self.jsSelf + "." + symbol_name
			# Otherwise it is an outside class, and we have to check that the
			# value is not an instance slot
			else:
				return ".".join((self.getAbsoluteName(scope),symbol_name))
		# FIXME: This is an exception... iteration being an operation, not a
		# context...
		elif isinstance(scope, interfaces.IIteration):
			return symbol_name
		elif isinstance(scope, interfaces.IClosure):
			return symbol_name
		elif isinstance(scope, interfaces.IProgram):
			return symbol_name
		elif isinstance(scope, interfaces.IBlock):
			return symbol_name
		else:
			raise Exception("Unsupported scope:" + str(scope))

	def _onImportedReference( self, name, slot ):
		"""Helper for the 'onReference' method"""
		# We proces the importation to convert the slot to an absolute name
		symbol_name = name
		o = slot.origin[0]
		if isinstance(o, interfaces.IImportModuleOperation):
			return o.getImportedModuleName()
		elif isinstance(o, interfaces.IImportModulesOperation):
			return name
		elif isinstance(o, interfaces.IImportSymbolOperation):
			module_name = o.getImportOrigin()
			symbol_name = o.getImportedElement()
			return module_name + "." + symbol_name
		elif isinstance(o, interfaces.IImportSymbolsOperation):
			module_name = o.getImportOrigin()
			return module_name + "." + symbol_name
		else:
			raise Exception("Import operation not supported yet: {0}".format(o))

	def onOperator( self, operator ):
		"""Writes an operator element."""
		o = operator.getReferenceName()
		o = JS_OPERATORS.get(o) or o
		return "%s" % (o)

	# =========================================================================
	# LITTERALS
	# =========================================================================

	def onNumber( self, number ):
		"""Writes a number element."""
		return "%s" % (number.getActualValue())

	def onString( self, element ):
		"""Writes a string element."""
		return json.dumps(element.getActualValue())

	def onList( self, element ):
		"""Writes a list element."""
		return '[%s]' % (", ".join([
			self.write(e) for e in element.getValues()
		]))

	def _writeDictKey( self, key ):
		if isinstance(key, interfaces.IString):
			return self.write(key)
		else:
			# FIXME: Raise an error, because JavaScript only allow strings as keys
			return "(%s)" % (self.write(key))

	def onDict( self, element ):
		# We test the keys and see if we only have litterals or not
		only_litterals = True
		for k,v in element.getItems():
			if not isinstance(k, interfaces.ILiteral):
				only_litterals = False
				break
		# If we only have litterals, we can create the map "as is"
		if only_litterals:
			return '{%s}' % (", ".join([
				"%s:%s" % ( self._writeDictKey(k),self.write(v))
				for k,v in element.getItems()
				])
			)
		# Otherwise we'll use extend.createMapFromItems method
		else:
			return "%s%screateMapFromItems(%s)" % (
				self.jsPrefix,
				self.jsCore,
				",".join("[%s,%s]" % ( self.write(k),self.write(v)) for k,v in element.getItems())
			)

	# =========================================================================
	# OPERATIONS
	# =========================================================================

	def onAllocation( self, allocation ):
		"""Writes an allocation operation."""
		s = allocation.getSlotToAllocate()
		v = allocation.getDefaultValue()
		if v:
			return "var %s = %s;" % (self._rewriteSymbol(s.getName()), self.write(v))
		else:
			return "var %s;" % (self._rewriteSymbol(s.getName()))

	def onAssignment( self, assignation ):
		"""Writes an assignation operation."""
		# TODO: If assignment target is an  access, we should rewrite it with
		# explicit length
		parent = self.context[-2]
		suffix = ";" if isinstance(parent, interfaces.IBlock) or isinstance(parent, interfaces.IProcess) else ""
		return "%s = %s%s" % (
			self._writeLValue(assignation.getTarget()),
			self.write(assignation.getAssignedValue()),
			suffix
		)

	def onEnumeration( self, operation ):
		"""Writes an enumeration operation."""
		start = operation.getStart()
		end   = operation.getEnd()
		if isinstance(start, interfaces.ILiteral): start = self.write(start)
		else: start = "(%s)" % (self.write(start))
		if isinstance(end, interfaces.ILiteral): end = self.write(end)
		else: end = "(%s)" % (self.write(end))
		res = self.jsPrefix + self.jsCore + "range(%s,%s)" % (start, end)
		step = operation.getStep()
		if step: res += " step " + self.write(step)
		return res

	def onResolution( self, resolution ):
		"""Writes a resolution operation."""
		# We just want the raw reference name here, if we use _write() instead,
		# we'll have improper scoping.
		resolved_name = resolution.getReference().getReferenceName()
		if not self._isSymbolValid(resolved_name):
			resolved_name = self._rewriteSymbol(resolved_name)
		if resolution.getContext():
			if resolved_name == "super":
				return "%s.getSuper()" % (self.write(resolution.getContext()))
			else:
				return "%s.%s" % (self.write(resolution.getContext()), resolved_name)
		else:
			return "%s" % (resolved_name)

	def onComputation( self, computation ):
		"""Writes a computation operation."""
		# FIXME: For now, we supposed operator is prefix or infix
		operands = [x for x in computation.getOperands() if x!=None]
		operator = computation.getOperator()
		# FIXME: Add rules to remove unnecessary parens
		if len(operands) == 1:
			res = "%s %s" % (
				self.write(operator),
				self.write(operands[0])
			)
		else:
			if operator.getReferenceName() == "has":
				res = '(!(%s.%s===undefined))' % (
					self.write(operands[0]),
					self.write(operands[1])
				)
			elif operator.getReferenceName() == "in":
				res = '(%sisIn(%s,%s))' % (
					self.jsPrefix + self.jsCore,
					self.write(operands[0]),
					self.write(operands[1])
				)
			elif operator.getReferenceName() == "not in":
				res = '(!(%sisIn(%s,%s)))' % (
					self.jsPrefix + self.jsCore,
					self.write(operands[0]),
					self.write(operands[1])
				)
			else:
				res = "%s %s %s" % (
					self.write(operands[0]),
					self.write(operator),
					self.write(operands[1])
				)
		if self.isIn(interfaces.IComputation):
			res = "(%s)" % (res)
		return res

	def _closureIsRewrite(self, closure):
		"""Some invocations/closures are going to be rewritten based on the
		backend"""
		embed_templates_for_backend = []
		others = []
		if not isinstance(closure, interfaces.IClosure):
			return False
		for op in closure.getOperations():
			if isinstance(op, interfaces.IEmbedTemplate):
				lang = op.getLanguage().lower()
				if lang == "javascript":
					embed_templates_for_backend.append(op)
				continue
		if embed_templates_for_backend and not others:
			return embed_templates_for_backend
		else:
			return ()

	def _rewriteInvocation(self, invocation, closure, template):
		"""Rewrites an invocation based on an embedding template."""
		arguments  = tuple([self.write(a) for a in invocation.getArguments()])
		parameters = tuple([self._rewriteSymbol(a.getName()) for a  in closure.getParameters()])
		args = {}
		for i in range(len(arguments)):
			args[parameters[i]] = arguments[i]
		target = invocation.getTarget()
		# To have the 'self', the invocation target must be a resolution on an
		# object
		assert isinstance(target, interfaces.IResolution)
		args["self"] = "self_" + str(time.time()).replace(".","_") + str(random.randint(0,100))
		args["self_once"] = self.write(target.getContext())
		vars = []
		for var in self.RE_TEMPLATE.findall(template):
			var = var[2:-1]
			vars.append(var)
			if var[0] == "_":
				if var not in args:
					args[var] = "var_" + str(time.time()).replace(".","_") + str(random.randint(0,100))
		return "%s%s" % (
			"self" in vars and "%s=%s\n" % (args["self"],self.write(args["self_once"])) or "",
			string.Template(template).substitute(args)
		)

	def onInvocation( self, invocation ):
		"""Writes an invocation operation."""
		self.inInvocation = True
		# FIXME: Target may not be a reference
		t = self.write(invocation.getTarget())
		target_type = invocation.getTarget().getResultAbstractType()
		if target_type:
			concrete_type = target_type.concreteType()
			rewrite        = self._closureIsRewrite(concrete_type)
		else:
			rewrite = ""
		parent = self.context[-2]
		suffix = ";" if isinstance(parent, interfaces.IBlock) or isinstance(parent, interfaces.IProcess) else ""
		res = None
		if rewrite:
			return self._rewriteInvocation(invocation, concrete_type, "\n".join([r.getCode() for r in rewrite]))
		else:
			self.inInvocation = False
			if t == "extend.assert":
				args      = invocation.getArguments()
				predicate = self.write(args[0])
				rest      = args[1:]
				# TODO: We should include the offsets
				return "!({0}) && extend.assert(false, {1}, {2}, {3}){4}".format(
					predicate,
					json.dumps(self.getScopeName() + ":"),
					", ".join(self.write(_) for _ in rest) or '""',
					json.dumps("(failed `" + predicate + "`)"),
					suffix
				)
			elif invocation.isByPositionOnly():
				return "%s(%s)%s" % (
					t,
					", ".join(map(self.write, invocation.getArguments())),
					suffix
					)
			else:
				normal_arguments = []
				extra_arguments  = {}
				current          = normal_arguments
				for param in invocation.getArguments():
					if  param.isAsMap():
						current = extra_arguments
						current["**"] = self.write(param.getValue())
					elif param.isAsList():
						current = extra_arguments
						current["*"] = self.write(param.getValue())
					elif param.isByName():
						current = extra_arguments
						current[self._rewriteSymbol(param.getName())] = self.write(param.getValue())
					else:
						assert current == normal_arguments
						current.append(self.write(param.getValue()))
				normal_str = "[%s]" % (",".join(normal_arguments))
				extra_str  = "{%s}" % (",".join("%s:%s" % (k,v) for k,v in list(extra_arguments.items())))
				return "extend.invoke(%s,%s,%s,%s)%s" % (
					self.jsSelf,
					t,
					normal_str,
					extra_str,
					suffix
				)

	def onArgument( self, argument ):
		r = self.write(argument.getValue())
		if argument.isAsMap():
			return "{'**':(%s)}" % (r)
		elif argument.isAsList():
			return "{'*':(%s)}" % (r)
		elif argument.isByName():
			# FIXME: Maybe rewrite name
			return "{'^':%s,'=':(%s)}" % (repr(self._rewriteSymbol(argument.getName())), r)
		else:
			return r

	def onInstanciation( self, operation ):
		"""Writes an invocation operation."""
		return "new %s(%s)" % (
			self.write(operation.getInstanciable()),
			", ".join(map(self.write, operation.getArguments()))
		)

	def onChain( self, chain ):
		target = self.write(chain.getTarget())
		v      = self._getRandomVariable()
		groups = chain.getGroups() or None
		return [
			"var {0}={1};".format(v, target),
		]

	def onSelection( self, selection ):
		# If-expressions are not going to be with a process or block as parent.
		in_process = isinstance(self.context[-2], interfaces.IProcess) or isinstance(self.context[-2], interfaces.IBlock)
		if not in_process and selection.hasAnnotation("if-expression"):
			return self._writeSelectionInExpression(selection)
		rules = selection.getRules()
		result = []
		for i in range(0,len(rules)):
			rule = rules[i]
			if isinstance(rule, interfaces.IMatchProcessOperation):
				process = rule.getProcess()
				is_expression = False
			else:
				assert isinstance(rule, interfaces.IMatchExpressionOperation)
				process  = rule.getExpression()
				is_expression = True
			body      = ("\t" if is_expression else "") + self.write(process) + (";" if is_expression else "")
			predicate = rule.getPredicate()
			is_else   = rule.hasAnnotation("else") or isinstance(predicate, interfaces.IReference) and predicate.getName() == "True"
			condition = self._format(self.write(predicate)).strip()
			if condition[0] == "(" and condition[-1] == ")": condition = condition[1:-1].strip()
			if i==0:
				# NOTE: This is an edge case (more like a bug, really) where two
				# branches of 1 selection are output as 2 selections with 1 branch.
				rule_code = [
					"else {" if is_else else "if (%s) {" % (condition) ,
					body,
					"}"
				]
			elif is_else or rule.hasAnnotation("else"):
				rule_code = [
					"} else {",
					body,
					"}"
				]
			else:
				rule_code = [
					"} else if (%s) {" % (condition),
					body,
					"}"
				]
			if not result:
				result = rule_code
			else:
				result = result[:-1] + rule_code
		if selection.hasAnnotation("assignment"):
			result = ["// This is a conditional assignment (default value)"] + result
		return self._format(*result)

	def _writeSelectionInExpression( self, selection ):
		"""Writes an embedded if expression"""
		rules  = selection.getRules()
		result = []
		text   = ""
		has_else = False
		for rule in rules:
			#assert isinstance(rule, interfaces.IMatchExpressionOperation)
			if isinstance(rule, interfaces.IMatchExpressionOperation):
				expression = rule.getExpression()
			else:
				expression = rule.getProcess()
			if rule.hasAnnotation("else"):
				text += self.write(expression)
				has_else = True
			else:
				text += "(%s ? %s : " % (
					self.write(rule.getPredicate()),
					self.write(expression)
				)
		if not has_else: text += "undefined)"
		text += (len(rules) - 1) * ")"
		return text

	def onNOP( self, nop ):
		return "/* pass */"

	def onIteration( self, iteration ):
		"""Writes a iteration operation."""
		iterator    = iteration.getIterator()
		if iteration.isRangeIteration():
			return self._writeRangeIteration(iteration)
		else:
			return self._writeObjectIteration(iteration)

	def onMapIteration( self, iteration ):
		return "extend.map({0}, {1})".format(self.write(iteration.getIterator()), self.write(iteration.getClosure()))

	def onFilterIteration( self, iteration ):
		i= iteration.getIterator()
		c = iteration.getClosure()
		p = iteration.getPredicate()
		if c and p:
			return "extend.map(extend.filter({0}, {1}), {2})".format(self.write(i), self.write(p), self.write(c))
		elif c:
			return "extend.map({0}, {1})".format(self.write(i), self.write(c))
		else:
			return "extend.filter({0}, {1})".format(self.write(i), self.write(p))

	def _writeRangeIteration( self, iteration ):
		iterator = iteration.getIterator()
		closure  = iteration.getClosure()
		start    = self.write(iterator.getStart())
		end      = self.write(iterator.getEnd())
		step     = self.write(iterator.getStep()) or "1"
		# We ensure there's no clash with the radom variables
		# FIXME: Sometimes the dataflow is empty, which seems odd
		dataflow            = (closure and closure.dataflow or iteration.dataflow)
		reserved_slot_names = [_.getName() for _ in dataflow.getSlots()] if dataflow else []
		self._reserveVariableNames(*reserved_slot_names)
		if "." in start or "." in end or "." in step: filt = float
		else: filt = int
		comp = "<"
		start, end, step = list(map(filt, (start, end, step)))
		# If start > end, then step < 0
		if start > end:
			if step > 0: step =  -step
			comp = ">"
		# If start <= end then step >  0
		else:
			if step < 0: step = -step
		args  = [self._rewriteSymbol(a.getName()) for a in closure.getParameters()]
		if len(args) == 0: args.append(self._getRandomVariable())
		if len(args) == 1: args.append(self._getRandomVariable())
		i = args[1]
		v = args[0]
		return self._format(
			"for ( var %s=%s ; %s %s %s ; %s += %s ) {" % (i, start, i, comp, end, i, step),
			"var %s=%s;" % (v,i),
			self.onClosure(closure, bodyOnly=True),
			"}"
		)

	def _writeObjectIteration( self, iteration ):
		# NOTE: This would return the "regular" iteration
		if self._withExtendIterate:
			return self.write("extend.iterate({0}, {1})".format(
				self.write(iteration.getIterator()),
				self.write(iteration.getClosure())
			))
		# Now, this requires some explanation. If the iteration is annotated
		# as `force-scope`, this means that there is a nested closure that references
		# some variable that is going to be re-assigned here
		closure = iteration.getClosure()
		# We ensure there's no clash with the radom variables
		# FIXME: Sometimes the dataflow is empty, which seems odd
		dataflow            = (closure and closure.dataflow or iteration.dataflow)
		reserved_slot_names = [_.getName() for _ in dataflow.getSlots()] if dataflow else []
		self._reserveVariableNames(*reserved_slot_names)
		args    = [self._rewriteSymbol(a.getName()) for a in closure.getParameters()] if isinstance(closure, interfaces.IClosure) else []
		if len(args) == 0: args.append(self._getRandomVariable())
		if len(args) == 1: args.append(self._getRandomVariable())
		v  = args[0]
		i  = args[1]
		l  = self._getRandomVariable()
		k  = self._getRandomVariable()
		ki = self._getRandomVariable()
		kl = self._getRandomVariable()
		iterator = self.write(iteration.getIterator())
		prefix     = None
		encloses   = None
		if isinstance(closure, interfaces.IClosure):
			encloses = {}
			for _ in closure.getAnnotations("encloses") or (): encloses.update(_.content)
			if v in encloses:
				w = self._getRandomVariable()
				closure = self.onClosure(closure, bodyOnly=True, transpose={v:w})
				v = w
			else:
				closure = self.onClosure(closure, bodyOnly=True)
		else:
			closure = self.handle(closure) + "({0}, {1}, {2})".format(v,i,l)
		# If there is no scope forcing, then we can do a simple iteration
		# over the array/object
		# TODO: Use for of https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/for...of
		return self._format(
			# OK, so it is a bit complicated here. We start by storing a reference
			# to the iterated expression
			"// Iterates over `{0}`. This works on array,objects and null/undefined".format(self.write(iterator)),
			"var {l}={iterator};".format(l=l, iterator=iterator),
			"var {k}={l} instanceof Array ? {l} : Object.getOwnPropertyNames({l}||{{}});".format(k=k, l=l),
			"var {kl}={k}.length;".format(k=k, kl=kl),
			# Now if the iterated expression is not an array, we get its keys
			"for (var {ki}=0;{ki}<{kl};{ki}++){{".format(ki=ki, kl=kl),
			# If `k` is not the array, then it means we're iterating over an
			# object
			(
				"var {i}=({k}==={l})?{ki}:{k}[{ki}];".format(i=i,k=k,l=l,ki=ki),
				"var {v}={l}[{i}];".format(v=v,l=l,i=i),
				"// This is the body of the iteration with (value={0}, key/index={1}) in {2}".format(
					v,i,l
				),
				closure,
			),
			"}"
		)

	def onRepetition( self, repetition ):
		return self._format(
			"while (%s) {" % (self.write(repetition.getCondition())),
			self.write(repetition.getProcess()),
			"}",
		)

	def onAccessOperation( self, operation ):
		target = operation.getTarget()
		index  = operation.getIndex()
		if isinstance(index, interfaces.INumber) and index.getActualValue() < 0:
			return self._format(
				"%s%saccess(%s,%s)" % (self.jsPrefix, self.jsCore, self.write(target), self.write(index))
			)
		else:
			return self._format(
				"%s[%s]" % (self.write(target), self.write(index))
			)

	def onSliceOperation( self, operation ):
		start = operation.getSliceStart()
		end   = operation.getSliceEnd()
		if start:
			start = self.write(start)
		else:
			start = "0"
		if end:
			end = self.write(end)
		else:
			end = "undefined"
		return self._format(
			"%s%sslice(%s,%s,%s)" % (
				self.jsPrefix,
				self.jsCore,
				self.write(operation.getTarget()),
				start,
				end
		))

	def onEvaluation( self, operation ):
		"""Writes an evaluation operation."""
		return "%s" % ( self.write(operation.getEvaluable()) )

	def onTermination( self, termination ):
		"""Writes a termination operation."""
		closure = self.context[self.lastIndexInContext(interfaces.IClosure)]
		prefix  = "&&".join(
			self.write(_.content) for _ in closure.getAnnotations("post")
		)
		result = self.write(termination.getReturnedEvaluable())
		if prefix:
			return "return ({0} || true) ? {1} : undefined;".format(prefix, result)
		else:
			return "return {0};".format(result)

	def onBreaking( self, breaking ):
		"""Writes a break operation."""
		if self._withExtendIterate:
			closure_index   = self.indexLikeInContext(interfaces.IClosure)
			iteration_index = self.indexLikeInContext(interfaces.IIteration)
			if iteration_index >= 0 and iteration_index > closure_index and not self.context[iteration_index].isRangeIteration():
				return "return extend.FLOW_BREAK;"
			else:
				return "break"
		else:
			return "break"

	def onContinue( self, breaking ):
		"""Writes a continue operation."""
		if self._withExtendIterate:
			closure_index   = self.indexLikeInContext(interfaces.IClosure)
			iteration_index = self.indexLikeInContext(interfaces.IIteration)
			if iteration_index >= 0 and iteration_index > closure_index and not self.context[iteration_index].isRangeIteration():
				return "return extend.FLOW_CONTINUE;"
			else:
				return "continue"
		else:
			return "continue"

	def onExcept( self, exception ):
		"""Writes a except operation."""
		return "throw " + self.write(exception.getValue()) + ";"

	def onInterception( self, interception ):
		"""Writes an interception operation."""
		try_block   = interception.getProcess()
		try_catch   = interception.getIntercept()
		try_finally = interception.getConclusion()
		res         = ["try {", list(map(self.write, try_block.getOperations())), "}"]
		if try_catch:
			res[-1] += " catch(%s) {" % ( self.write(try_catch.getArguments()[0]))
			res.extend([
				list(map(self.write, try_catch.getOperations())),
				"}"
			])
		if try_finally:
			res[-1] += " finally {"
			res.extend([list(map(self.write, try_finally.getOperations())), "}"])
		return self._format(*res)

	def onEmbed( self, embed ):
		lang = embed.getLanguage().lower().strip()
		if not lang in self.supportedEmbedLanguages:
			self.environment.report.error ("JavaScript writer cannot embed language:", lang)
			res = [ "// Unable to embed the following code" ]
			for l in embed.getCode().split("\n"):
				res.append("// " + l)
			return "\n".join(res)
		else:
			return embed.getCode()

	# =========================================================================
	# NICE HELPERS
	# =========================================================================

	def _header( self, project=None, source=None ):
		if not self._isNice: return []
		return [
			"// ---------------------------------------------------------------------------",
			"// Project   : ${PROJECT}",
			"// ---------------------------------------------------------------------------",
			"// License   : ${LICENSE}",
			"// ---------------------------------------------------------------------------",
			"// Creation  : ${CREATED}",
			"// Last mod  : ${UPDATED}",
			"// ---------------------------------------------------------------------------",
			"// NOTE: This file is produced by Sugar/LambdaFactory, and as such should",
			"// not be edited directly if you have access to the  original Sugar code.",
			"// If you plan to continue support in JavaScript, then this file provide a good",
			"// starting point. If you are targetting another language, you",
			"// might consider writing a new backend for LambdaFactory.",
			"",
		]

	def _section( self, name ):
		if not self._isNice: return []
		return [
			"",
			"// ---------------------------------------------------------------------------",
			"//",
			"// " + name.upper(),
			"//",
			"// ---------------------------------------------------------------------------",
			"",
		]


	def _group( self, name, depth=0 ):
		if not self._isNice: return []
		c = (79 - 3) - depth * 4 ; sep = "// " + "=" * c
		return [
			"",
			sep,
			"// " + name.upper(),
			sep,
			"",
		]

	# =========================================================================
	# HELPERS
	# =========================================================================

	def _docextern( self, element ):
		if not self._externs: return ""
		if isinstance(element, interfaces.IFunction):
			return self._externs._docfunction(element, declaration=False)
		else:
			return ""

	def _document( self, element ):
		res = None
		if isinstance(element, interfaces.IClass):
			res = "\n".join(self._section(element.getName()))
		if element.getDocumentation():
			doc = element.getDocumentation()
			r   = ["/**"]
			for line in doc.getContent().split("\n"):
				r.append("  * " + line)
			r.append("*/")
			res = (res or "") + "\n".join(r)
		return res

MAIN_CLASS = Writer

# EOF - vim: tw=80 ts=4 sw=4 noet