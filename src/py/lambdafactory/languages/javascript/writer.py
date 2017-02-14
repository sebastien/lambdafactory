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
OPTION_NOPARENS       = "noparens"
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

RE_STRING_FORMAT = re.compile("\{((\d+)|([\w_]+))\s*(:\s*(\w+))?\}")

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
		self.runtimePrefix                = ""
		self.jsCore                  = "extend."
		self.jsSelf                  = "self"
		self.jsModule                = "__module__"
		self.jsInit                  = "__init__"
		self._moduleType             = None
		self.supportedEmbedLanguages = ["ecmascript", "js", "javascript"]
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
				i  = int(i / l)
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


	def _isSymbolValid( self, string ):
		"""Tells if the name of the symbol is valid, ie. not a keyword
		and matching the symbol regexp."""
		# FIXME: Warn if symbol is typeof, etc.
		res = not self._isSymbolKeyword(string) and VALID_SYMBOL.match(string) != None
		return res

	def _isSymbolKeyword( self, string ):
		return string in KEYWORDS

	def _isSuperInvocation( self, element ):
		target = element.getTarget()
		return (
			isinstance(target,              interfaces.IResolution) and
			isinstance(target.getContext(), interfaces.IReference)  and
			target.getContext().getReferenceName() == "super"
		)

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
		f = open(js_runtime, 'r') ; text = f.read() ; f.close()
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
		# TODO: We should have a special handling for the current module
		# if element == self.getCurrentModule() and self.resolve(element.getName())[1] != element:
		# 	return ["__module__"] if asList else "__module__"
		if isinstance( element, interfaces.ITypeReference ):
			# FIXME: This is a bit of a hack
			return self.write(element)
		while element.getParent():
			element = element.getParent()
			# Transient scope elements do not participate in the naming
			if element.hasTransientScope():
				continue
			# FIXME: Some elements may not have a name
			if isinstance(element, interfaces.IModule):
				# TODO: Should be able to detect a reference to the current module
				names = element.getName().split(".") + names
			elif not isinstance(element, interfaces.IProgram):
				names.insert(0, element.getName())
		return names if asList else ".".join(names)

	def getSafeName( self, element ):
		"""Returns the same as absolute name but with `_` instead of `_`."""
		if self._moduleType == MODULE_VANILLA:
			return self.getAbsoluteName(element)
		else:
			return "_".join(self.getAbsoluteName(element, asList=True))

	def getSafeSuperName( self, element ):
		parent = element.getParent()
		name   = element.getName()
		if parent == self.getCurrentModule():
			if self.resolve(self.getLocalName(parent))[1] == parent:
				return self.getLocalName(parent) + "." + name
			else:
				return "__module__" + "." + name
		else:
			return self.getSafeName(parent) + "." + name

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
		resolved_local = self.getCurrentDataFlow().getSlotValue(local_name)
		shadowed       = resolved_local and resolved_local != element
		element_module = self.getModuleFor(element)
		if resolved and not shadowed:
			# If we can resolve the value locally, then we simply return
			# the slot name
			return local_name
		elif isinstance(element, interfaces.IModule):
			return self.getSafeName(element)
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
			return self.getSafeName(element)

	# =========================================================================
	# MODULES
	# =========================================================================

	def onModule( self, moduleElement ):
		"""Writes a Module element."""
		# Detects the module type
		self._withExterns = self.environment.options.get(OPTION_EXTERNS) and True or False
		self._isNice      = self.environment.options.get(OPTION_NICE)
		self._isUnambiguous = not self.environment.options.get(OPTION_NOPARENS)
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
			'"use strict";'
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
		code.extend(self._runtimePreamble())
		# --- VERSION ---------------------------------------------------------
		version = moduleElement.getAnnotation("version")
		if version:
			code.append("%s.__VERSION__='%s';" % (module_name, version.getContent()))
		# --- SLOTS -----------------------------------------------------------
		for name, value, accessor, mutator in moduleElement.getSlots():
			if isinstance(value, interfaces.IModuleAttribute):
				declaration = u"{0}.{1};".format(module_name, self.write(value))
			else:
				# NOTE: Some slot values may be shadowed, in which case they
				# won't return any value
				value_code = self.write(value)
				if value_code:
					slot_name     = name
					declaration   = ""
					if slot_name == interfaces.Constants.ModuleInit:
						slot_name = self.jsInit
						if self._isNice:
							declaration = "\n".join(self._section("Module init")) + "\n"
					if slot_name == interfaces.Constants.MainFunction:
						# FIXME: Technically, this should be moved after the init
						slot_name = "main"
						if self._isNice:
							declaration = "\n".join(self._section("Module main")) + "\n"

					declaration   += u"{0}.{1} = {2}".format(module_name, slot_name, value_code)
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
		code.append('if (typeof(%s.%s)!="undefined") {%s.%s();}' % (
			module_name, self.jsInit,
			module_name, self.jsInit
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
			"(function({0}){{".format(self.jsModule),
		] + symbols + [
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
				line = "c.{0} = __module__;".format(name)
			res.append(line)
		return (self._section("Module registration") if self._isNice else []) + [
			"// Registers the module in `extend`, if available" if self._isNice else None,
			"if (typeof extend !== 'undefined') {{extend.module(\"{0}\", {1});}}".format(".".join(names), safe_name),
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

	def onSingleton( self, element ):
		return self.onClass(element)

	def onTrait( self, element ):
		return self.onClass(element)

	def onClass( self, classElement ):
		"""Writes a class element."""
		parents = self.getClassParents(classElement)
		parent  = "undefined"
		if len(parents) == 1:
			parent_class = parents[0]
			if isinstance(parent_class, interfaces.IClass):
				parent = self.getSafeSuperName(parent_class)
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
				invoke_parent_constructor = u"".join([
					"// Invokes the parent constructor - this requires the parent to be an extend.Class class\n",
					"\tif (true) {var __super__=",
					# FIXME: Make sure that that the module name is not shadowed
					# by something else
					"%s.getSuper(%s.getParent());" % (self._runtimeSelfReference(classElement), self.getSafeSuperName(classElement)),
					"__super__.initialize.apply(__super__, arguments);}"
				])
			for a in classElement.getAttributes():
				if not a.getDefaultValue(): continue
				constructor_attributes.append(
					"// Default value for property `{0}`".format(a.getName())
				)
				constructor_attributes.append(
					"if (typeof(%s.%s)=='undefined') {%s.%s = %s;};" % (
						self._runtimeSelfReference(classElement), self._rewriteSymbol(a.getName()),
						self._runtimeSelfReference(classElement), self._rewriteSymbol(a.getName()),
						self.write(a.getDefaultValue())
				))
			# We only need a default constructor when we have class attributes
			# declared and no constructor declared
			default_constructor = self._format(
				(
					self.options["ENABLE_METADATA"] and "initialize: __def(function(){" \
					or "initialize: function(){"
				),
				["var %s = this;" % (self._runtimeSelfReference(classElement))],
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
		if classOperations:
			result += self._group("Class methods", 1)
			written_ops = ",\n".join(map(self.write, classOperations))
			result.append("operations:{")
			result.append([written_ops])
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
				"%s = %s" % (self._rewriteSymbol(element.getName()), default_value)
			)
		else:
			return self._format(
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
			["var %s = this;" % (self._runtimeSelfReference(methodElement))],
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
			["var %s = this;" % (self._runtimeSelfReference(methodElement))], #, self.getAbsoluteName(methodElement.getParent()))],
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
				self._runtimeSelfReference(element), name,
				self._runtimeSelfReference(element), name,
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
			["var %s = this;" % (self._runtimeSelfReference(element))],
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

	def onInitializer( self, element ):
		return self.onFunction(element)

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
				['var %s = %s;' % (self._runtimeSelfReference(function), self.getResolvedName(function.parent))],
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
				res.insert(0, 'var %s=%s;' % (self._runtimeSelfReference(function), self.getAbsoluteName(parent)))
			res.append("var result = __wrapped__.apply(%s, arguments);" % (self._runtimeSelfReference(function)))
			res.append(self.writeFunctionPost(function))
			res.append("return result;")
		res = self.writeDecorators(function, res)
		self.popVarContext()
		return self._format(*res)

	def writeDecorators( self, element, lines ):
		d = []
		a = element.getAnnotations(withName="decorator")
		l = len(a) - 1
		for i,_ in enumerate(a):
			t = self.write(_.getContent())
			if i != l:
				t = "_ = " + t
			else:
				t = "return " + t
			d.append(t)
		if len(d) > 0:
			return ["(function(_){",d,"}(",lines,"))"]
		else:
			return lines

	# =========================================================================
	# CLOSURES
	# =========================================================================

	def onClosure( self, closure, bodyOnly=False, transpose=None ):
		"""Writes a closure element. The `transpose` element is used
		to rename parameters when there is an `encloses` annotation in
		an iteration loop.
		"""
		operations = closure.getOperations()
		implicits  = [_ for _ in self._writeImplicitAllocations(closure)]
		if bodyOnly:
			result = implicits + [self.write(_) + ";" for _ in operations]
		else:
			result = [
				self._document(closure),
				(
					self.options["ENABLE_METADATA"] and "__def(function(%s) {" \
					or "function(%s) {"
				) % ( ", ".join(map(self.write, closure.getArguments()))),
				self._writeClosureArguments(closure),
				implicits,
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
		# The `encloses` tag is useful for iterations so that there's no
		# propagation of iteration-local variables back to a parent scope.
		# However, when we're using `_withExtendIterate`  this is not
		# relevant anymore, as everything is wrapped in a closure.
		iterate_bypass = self._withExtendIterate and self.isIn(interfaces.IIteration)
		if encloses and not iterate_bypass:
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

	# FIXME: Deprecate
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
					self.runtimePrefix + self.jsCore + "sliceArguments",
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

	def onImplicitReference( self, element ):
		scope = element.getElement()
		slot  = scope.dataflow.getImplicitSlotFor(scope)
		return slot.getName()

	def onReference( self, element ):
		"""Writes an argument element."""
		symbol_name = element.getReferenceName()
		slot, value = self.resolve(symbol_name)
		if slot:
			scope = slot.getDataFlow().getElement()
		else:
			scope = None
		if symbol_name == "self":
			return self._runtimeSelfReference(element)
		elif symbol_name == "__target__":
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
			return self._runtimeSuper(element)
		elif value == self.getCurrentModule():
			return "__module__"
		if not self._isSymbolValid(symbol_name):
			# FIXME: This is temporary, we should have an AbsoluteReference
			# operation that uses symbols as content
			symbol_name = ".".join(map(self._rewriteSymbol, symbol_name.split(".")))
		# If there is no scope, then the symmbol is undefined
		if not scope:
			if symbol_name == "print": return self.runtimePrefix + self.jsCore + "print"
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
				invocation = self.findInContext(interfaces.IInvocation)
				if invocation and invocation.getTarget() == element:
					return self._runtimeGetMethodByName(symbol_name, value, element)
				else:
					return self._runtimeWrapMethodByName(symbol_name, value, element)
			elif isinstance(value, interfaces.IClassMethod):
				# FIXME: Same as above
				if self.isIn(interfaces.IInstanceMethod):
					return self._runtimeWrapMethodByName(symbol_name, value, element)
				else:
					return "%s.%s" % (self._runtimeSelfReference(value), symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				# FIXME: Same as above
				if self.isIn(interfaces.IClassMethod):
					return "%s.%s" % (self._runtimeSelfReference(value), symbol_name)
				else:
					return self._runtimeCurrentGetClass() + "." + symbol_name
			else:
				return self._runtimeSelfReference(value) + "." + symbol_name
		# It is a local variable
		elif self.getCurrentFunction() == scope:
			return symbol_name
		# It within the current module
		elif self.getCurrentModule() == scope:
			# NOTE: We need the current module scope so as not to shadow
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
				return self._runtimeSelfReference(value) + "." + symbol_name
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
		# FIXME: Get the output proper
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
				self.runtimePrefix,
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

	def onInterpolation( self, operation ):
		"""Writes an interpolation operation."""
		s = operation.getString().getActualValue()
		c = operation.getContext()
		o = 0
		r = []
		# NOTE: The parsing could be done at the compiler level, but for now
		# the semantics are left to the backend.
		is_multiple = False
		occ         = []
		for m in RE_STRING_FORMAT.finditer(s):
			r.append(json.dumps(s[o:m.start()]))
			ki = m.group(2) # Index
			ks = m.group(3)
			f  = m.group(4) # Formatter
			v  = json.dumps(ks) if ks else ki # Value
			r.append("extend.sprintf(_[{0}],{1})".format(v, json.dumps(f)) if f else "_[{0}]".format(v))
			o = m.end()
		r.append(json.dumps(s[o:]))
		# FIXME: Optimize so that no function has to be called if the arguments
		# are not repeated, or use implicits.
		return r[0] if len(r) == 1 else "(function(_){return " + "+".join(r) + "})(" + self.write(c) + ")"

	def onEnumeration( self, operation ):
		"""Writes an enumeration operation."""
		start = operation.getStart()
		end   = operation.getEnd()
		if isinstance(start, interfaces.ILiteral): start = self.write(start)
		else: start = "(%s)" % (self.write(start))
		if isinstance(end, interfaces.ILiteral): end = self.write(end)
		else: end = "(%s)" % (self.write(end))
		res = self.runtimePrefix + self.jsCore + "range(%s,%s)" % (start, end)
		step = operation.getStep()
		if step: res += " step " + self.write(step)
		return res

	def onResolution( self, resolution ):
		"""Writes a resolution operation."""
		# We just want the raw reference name here, if we use _write() instead,
		# we'll have improper scoping.
		reference    = resolution.getReference()
		context      = resolution.getContext()
		context_name = self.write(context) if isinstance(context, interfaces.IReference) else None
		if isinstance(reference, interfaces.IAbsoluteReference):
			return self.onReference(reference)
		elif not context:
			# NOTE: Not sure why it is not reference
			return self._rewriteSymbol(reference.getReferenceName())
		elif context_name == "super":
			return self._runtimeSuperResolution(resolution)
		else:
			return self.write(context) + "." + self._rewriteSymbol(reference.getReferenceName())

	def onComputation( self, computation ):
		"""Writes a computation operation."""
		# FIXME: For now, we supposed operator is prefix or infix
		operands = [x for x in computation.getOperands() if x!=None]
		operator = computation.getOperator()
		# FIXME: Add rules to remove unnecessary parens
		if len(operands) == 1:
			res = "%s%s" % (
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
				res = self._runtimeIsIn(operands[0], operands[1])
			elif operator.getReferenceName() == "not in":
				res = "!(" + self._runtimeIsIn(operands[0], operands[1]) + ")"
			else:
				res = "%s %s %s" % (
					self.write(operands[0]),
					self.write(operator),
					self.write(operands[1])
				)
		#if self.isIn(interfaces.IComputation) and computation.hasAnnotation("parens") or self._isUnambiguous:
		if computation.hasAnnotation("parens") or self._isUnambiguous:
			res = "(%s)" % (res)
		return res

	def onInvocation( self, invocation ):
		"""Writes an invocation operation."""
		parent            = self.context[-2]
		suffix            = ";" if isinstance(parent, interfaces.IBlock) or isinstance(parent, interfaces.IProcess) else ""
		# FIXME: Special handling of assert
		if False and "extend.assert":
			return self._runtimeAssert(invocation) + suffix
		elif invocation.isByPositionOnly():
			if self._isSuperInvocation(invocation):
				return self._runtimeSuperInvocation(invocation) + suffix
			else:
				return self._runtimeInvocation(invocation) + suffix

		else:
			raise NotImplementedError


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
		i = operation.getInstanciable()
		t = self.write(i)
		# Invocation targets can be expressions
		if not isinstance(i, interfaces.IReference): t = "(" + t + ")"
		return "new %s(%s)" % (
			t,
			", ".join(map(self.write, operation.getArguments()))
		)

	def onChain( self, chain ):
		target = self.write(chain.getTarget())
		v      = self._getRandomVariable()
		groups = chain.getGroups()
		implicit_slot = chain.dataflow.getImplicitSlotFor(chain)
		prefix        = ""
		op            = self.write(chain.getOperator())
		if op == ":":
			prefix = implicit_slot.getName() + "="
		return [
			"// Chain on " + implicit_slot.getName(),
			implicit_slot.getName() + "=" + self.write(chain.getTarget()) + ";",
		] + [
			prefix + self._format(self.write(g)) for g in groups
		]

	def onSelection( self, selection ):
		# If-expressions are not going to be with a process or block as parent.
		in_process = isinstance(self.context[-2], interfaces.IProcess) or isinstance(self.context[-2], interfaces.IBlock)
		if not in_process and selection.hasAnnotation("if-expression"):
			return self._format(self._writeSelectionInExpression(selection))
		rules     = selection.getRules()
		implicits = [_ for _ in self._writeImplicitAllocations(selection)]
		result    = []
		last      = len(rules) - 1
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
			# An else has to be last, and never the first
			is_last   = i == last and i > 0
			is_else   = rule.hasAnnotation("else") or is_last and isinstance(predicate, interfaces.IReference) and predicate.getName() == "True"
			condition = self._format(self.write(predicate)).strip()
			if self._isUnambiguous and condition[0] == "(" and condition[-1] == ")": condition = condition[1:-1].strip()
			if i==0:
				if selection.getImplicitValue():
					implicit_slot = selection.dataflow.getImplicitSlotFor(selection)
					condition = "((({0}={1}) || true) && ({2}))".format(
						implicit_slot.getName(),
						self.write(selection.getImplicitValue()),
						condition
					)
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
		result = implicits + result
		if selection.hasAnnotation("assignment"):
			result = ["// This is a conditional assignment (default value)"] + result
		return self._format(*result)

	def _writeSelectionInExpression( self, selection ):
		"""Writes an embedded if expression"""
		# TODO: This should be re-written to have a more elegant output
		rules  = selection.getRules()
		text   = ""
		has_else = False
		for i, rule in enumerate(rules):
			#assert isinstance(rule, interfaces.IMatchExpressionOperation)
			if isinstance(rule, interfaces.IMatchExpressionOperation):
				expression = rule.getExpression()
			else:
				expression = rule.getProcess()
			if rule.hasAnnotation("else"):
				text += self.write(expression)
				has_else = True
			else:
				prefix = ""
				if i==0 and selection.getImplicitValue():
					implicit_slot = selection.dataflow.getImplicitSlotFor(selection)
					prefix = "(\n\t({0}={1}) || true) && ".format(
						implicit_slot.getName(),
						self.write(selection.getImplicitValue()),
					)
				text += "(%s%s ?\n\t%s :\n\t" % (
					prefix,
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
		if isinstance(iteration.parent, interfaces.IOperation):
			return self._runtimeIterate(
				iteration.getIterator(),
				iteration.getClosure(),
				iteration,
			)
		else:
			iterator    = iteration.getIterator()
			if iteration.isRangeIteration():
				return self._writeRangeIteration(iteration)
			else:
				return self._writeObjectIteration(iteration)

	def onMapIteration( self, iteration ):
		return self._runtimeMap(
			iteration.getIterator(),
			iteration.getClosure()
		)

	def onFilterIteration( self, iteration ):
		i= iteration.getIterator()
		c = iteration.getClosure()
		p = iteration.getPredicate()
		if c and p:
			return self._runtimeMap(
				self._runtimeFilter(i, p),
				c
			)
		elif c:
			return self._runtimeMap(i,c)
		else:
			return self._runtimeFilter(i,p)


	def onReduceIteration( self, iteration ):
		return self._runtimeReduce(
			iteration.getIterator(),
			iteration.getClosure(),
			iteration.getInitialValue()
		)

	def _writeRangeIteration( self, iteration ):
		iterator = iteration.getIterator()
		closure  = iteration.getClosure()
		start    = self.write(iterator.getStart())
		end      = self.write(iterator.getEnd())
		step     = self.write(iterator.getStep()) or "1"
		iteration.addAnnotation("direct-iteration")
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
		if isinstance(closure, interfaces.IClosure):
			args  = [self._rewriteSymbol(a.getName()) for a in closure.getParameters()]
		elif isinstance(closure, interfaces.IReference):
			args = []
		else:
			raise NotImplementedError
		if len(args) == 0: args.append(self._getRandomVariable())
		if len(args) == 1: args.append(self._getRandomVariable())
		i = args[1]
		v = args[0]
		return self._format(
			"for ( var %s=%s ; %s %s %s ; %s += %s ) {" % (i, start, i, comp, end, i, step),
			"var %s=%s;" % (v,i),
			self.onClosure(closure, bodyOnly=True) if isinstance(closure,
			interfaces.IClosure) \
			else closure.getReferenceName() + "({0}, {1})".format(*args),
			"}"
		)

	def _writeObjectIteration( self, iteration ):
		# NOTE: This would return the "regular" iteration
		if self._withExtendIterate:
			return self._runtimeIterate(
				iteration.getIterator(),
				iteration.getClosure(),
				iteration,
			)
		# Now, this requires some explanation. If the iteration is annotated
		# as `force-scope`, this means that there is a nested closure that references
		# some variable that is going to be re-assigned here
		closure = iteration.getClosure()
		iteration.addAnnotation("direct-iteration")
		closure.addAnnotation("direct-iteration")
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
			# We might need to prevent leaking of scope if an inner loop mutates
			# a variable defined in an outer loop. This is not a problem when
			# using iterate, as it always wraps in a closure.
			encloses = {}
			for _ in closure.getAnnotations("encloses") or (): encloses.update(_.content)
			if not self._withExtendIterate and v in encloses:
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
		is_direct = isinstance(index, interfaces.IString) or isinstance(index, interfaces.INumber) and index.getActualValue() >= 0
		is_lvalue = operation.hasAnnotation("lvalue") or self.hasAnnotationInContext("lvalue") >= 0
		if is_lvalue or is_direct:
			return self._format(
				"%s[%s]" % (self.write(target), self.write(index))
			)
		else:
			return self._format(self._runtimeAccess(
				self.write(target), self.write(index)
			))

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
		return self._format(self._runtimeSlice(
			self.write(operation.getTarget()),
			start,
			end
		))


	def onTypeIdentification( self, element ):
		lvalue = self.write(element.getTarget())
		t      = element.getType()
		# FIXME: We should probably resolve the name, or try at least..
		rvalue = t.getName()
		operation = "instanceof"
		# TODO: We should resolve the type in the namespace
		if not t.parameters or len(t.parameters) == 0:
			if rvalue == "String":
				return "(typeof {0} === 'string')".format(lvalue)
			elif rvalue == "Number":
				return "(!isNaN({0}))".format(lvalue)
			elif rvalue == "Undefined":
				return "(typeof {0} === 'undefined')".format(lvalue)
			elif rvalue == "None":
				return "({0} === null)".format(lvalue)
			else:
				slot, value = self.resolve(t.getReferenceName())
				if value:
					rvalue = self.getSafeName(value)
					if isinstance(value, interfaces.ISymbolType):
						operation = "==="
		return ("({0} {2} {1})".format(lvalue, rvalue, operation))

	def onEvaluation( self, operation ):
		"""Writes an evaluation operation."""
		return "%s" % ( self.write(operation.getEvaluable()) )

	def onTermination( self, termination ):
		"""Writes a termination operation."""
		# If we're in a closure, we look for post-conditions and store
		# them in a prefix
		i       = self.lastIndexInContext(interfaces.IClosure)
		closure = self.context[i] if i >= 0 else None
		prefix  = "&&".join(self.write(_.content) for _ in
				closure.getAnnotations("post")) if closure else None
		# We format the result
		result = self.write(termination.getReturnedEvaluable())
		if prefix:
			result = "(({0}) || true) ? {1} : undefined".format(prefix, result)
		else:
			result = "{0}".format(result)

		iteration = self.findInContext(interfaces.IIteration)
		if termination.hasAnnotation("in-iteration") and not iteration.hasAnnotation("direct-iteration"):
			# If the termination is in an iteration, and that the
			# iteration is in an expression, then we need to wrap the
			# return value so that the iteration function can unwrap the result.
			iteration = self.findInContext(interfaces.IIteration)
			# We only do it for iteration, not for map/filter/reduce
			if (isinstance(iteration, interfaces.IFilterIteration)
			or isinstance(iteration, interfaces.IMapIteration)
			or isinstance(iteration, interfaces.IReduceIteration)):
				return "return " + result
			else:
				return self._runtimeReturnValue(result)
		else:
			return "return " + result

	def onBreaking( self, breaking ):
		"""Writes a break operation."""
		if self._withExtendIterate:
			closure_index   = self.indexLikeInContext(interfaces.IClosure)
			iteration_index = self.indexLikeInContext(interfaces.IIteration)
			if iteration_index >= 0 and iteration_index > closure_index and not self.context[iteration_index].isRangeIteration():
				return self._runtimeReturnBreak()
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
				return self._runtimeReturnContinue()
			else:
				return "continue"
		else:
			return "continue"

	def onExcept( self, exception ):
		"""Writes a except operation."""
		res = "throw " + self.write(exception.getValue())
		if isinstance(exception, interfaces.IOperation):
			# We can throw in an exception
			return "(function(){" + res +"}())"
		else:
			return res + ";"


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
	# TYPES
	# =========================================================================

	def onType( self, element ):
		parents = [self.getSafeName(_) for _ in element.parents]
		if element.isConcrete():
			slots = [_ for _ in element.constraints if isinstance(_, interfaces.ISlotConstraint)]
			args  = ", ".join(_.getName() for _ in slots)
			yield "class (" + args + "){"
			yield "}"

	def onEnumerationType( self, element ):
		symbols = [_.getName() for _ in element.getSymbols()]
		m = self._runtimeModuleName(element)
		yield "function(_){"
		yield "\treturn " + " || ".join("(_==={0}.{1})".format(m,_) for _ in symbols) + ";"
		yield "};"
		for _ in symbols:
			# NOTE: Symbol is not supported yet, but would be preferrable
			yield "{0}.{1} = new String(\"{2}\");".format(m, _, _)

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
	# EXTERNS HELPERS
	# =========================================================================

	def _extern( self, element, prefix=None, inInstance=False ):
		res = []
		if isinstance(element, interfaces.IFunction):
			params = self._extractParameters(element)
			for p in params:
				res.append("@param {{{0}{2}}} {1}".format(p["type"], p["name"], "=" if p["optional"] else ""))
		elif isinstance(element, interfaces.IValue):
			res.append("@type {Object}")
		return res

	def _extractParameters( self, element ):
		params = []
		for param in element.getParameters():
			params.append(dict(
				name     = param.getName(),
				type     = "Object",
				optional = param.getDefaultValue()
			))
		return params

	# =========================================================================
	# HELPERS
	# =========================================================================

	def getDocumentationLines( self, element ):
		"""Returns a list of strings corresonding to each line of documentation
		in the original element."""
		doc    = element.getDocumentation()
		body   = []
		suffix = []
		if doc:
			body = doc.getContent().split("\n") + [""]
		elif self._isNice or self._withExterns:
			body = ["Missing documentation for element `{0}`".format(element.getName()), ""]
		if self._withExterns:
			suffix += self._extern(element)
		return body + suffix

	def _document( self, element ):
		res = None
		if isinstance(element, interfaces.IClass):
			res = "\n".join(self._section(element.getName()))
		if element.getDocumentation():
			r   = ["/**"]
			for line in self.getDocumentationLines(element):
				r.append("  * " + line)
			r.append("*/")
			res = (res or "") + "\n".join(r)
		return res

	def _writeImplicitAllocations( self, element ):
		# FIXME: assert(element.dataflow) fails sometimes
		if element and element.dataflow:
			# NOTE: Implicits can sometimes be declared twice
			l = [_.getName() for _ in element.dataflow.slots if _.isImplicit()]
			if l:
				yield "var {0}; /* implicits */".format(", ".join(l))

	# =========================================================================
	# RUNTIME
	# =========================================================================

	def _runtimeSuper( self, element ):
		if self.isIn(interfaces.IClassAttribute) or self.isIn(interfaces.IClassMethod):
			c = self.getCurrentClass()
			p = self.getClassParents(c)
			# FIXME: Submodule support
			if p:
				return self.getAbsoluteName(p[0])
			else:
				return "self"
		else:
			assert self.resolve("self"), "Super must be used inside method"
			# FIXME: Should check that the element has a method in parent scope
			# FIXME: Submodule support
			return "%s.getSuper(%s.getParent())" % (
				self._runtimeSelfReference(element),
				self.getSafeSuperName(self.getCurrentClass())
			)

	def _runtimeSuperResolution( self, relement, reference ):
		return "{0}.getSuper().{1}".format(
			self.runtimePrefix,
			self._rewriteSymbol(resolution.getReference().getReferenceName())
		)

	def _runtimeGetMethodByName(self, name, value=None, element=None):
		return self._runtimeSelfReference(value) + "." + name

	def _runtimeWrapMethodByName(self, name, value=None, element=None):
		if isinstance(value, interfaces.IClassMethod):
			return self._runtimeCurrentGetClass() + ".getOperation('%s')" % (symbol_name)
		else:
			return self._runtimeSelfReference(value) + ".getMethod(" + name + ")"

	def _runtimeOp( self, name, *args ):
		args = [self.write(_) if isinstance(_,interfaces.IElement) else _ for _ in args]
		return "extend." + name + "(" + ", ".join(args) + ")"

	def _runtimeIsIn( self, element, collection ):
		return self._runtimeOp("isIn", element, collection)

	def _runtimeModuleName( self, element=None ):
		return "__module__"

	def _runtimeMap( self, lvalue, rvalue ):
		return self._runtimeOp("map", lvalue, rvalue)

	def _runtimeReduce( self, lvalue, rvalue, initial=None ):
		if initial is None:
			return self._runtimeOp("reduce", lvalue, rvalue)
		else:
			return self._runtimeOp("reduce", lvalue, rvalue, initial)

	def _runtimeFilter( self, lvalue, rvalue ):
		return self._runtimeOp("filter", lvalue, rvalue)

	def _runtimeIterate( self, lvalue, rvalue, iteration=None ):
		result =  self._runtimeOp("iterate", lvalue, rvalue)
		if iteration and iteration.hasAnnotation("terminates"):
			return "var {0}={1};if ({0} instanceof {2}) {{return {0}.value;}};".format(
				self._getRandomVariable(),
				result,
				self._runtimeReturnType(),
			)
		else:
			return result

	def _runtimeAssert( self, invocation ):
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

	def _runtimeReturnType( self ):
		return self.runtimePrefix + "FLOW_RETURN"

	def _runtimeReturnBreak( self ):
		return "return " + self.runtimePrefix + "FLOW_BREAK;"

	def _runtimeReturnContinue( self ):
		return "return " + self.runtimePrefix + "FLOW_CONTINUE;"

	def _runtimeReturnValue( self, value ):
		return "return new " + self._runtimeReturnType() + "(" + value + ");"

	def _runtimeSelfReference( self, element=None ):
		return self.jsSelf

	def _runtimeSelfBinding( self, element=None ):
		return "var self = this;"

	def _runtimeInvocation( self, element ):
		return "{0}({1})".format(
			self.write(element.getTarget()),
			", ".join(map(self.write, element.getArguments())),
		)

	def _runtimeSuperInvocation( self, element ):
		return "{0}({1})".format(
			self.write(element.getTarget()),
			", ".join(map(self.write, element.getArguments())),
		)

	def _runtimePreamble( self ):
		return []

	def _runtimeAccess( self, target, index ):
		return "%s%saccess(%s,%s)" % (
			self.runtimePrefix, self.jsCore,
			target, index
		)

	def _runtimeSlice( self, target, start, end ):
		return "%s%sslice(%s,%s,%s)" % (
			self.runtimePrefix,
			self.jsCore,
			target,
			start,
			end
		)

	def _ensureSemicolon( self, block ):
		if isinstance(block, tuple) or isinstance(block, list):
			if block:
				block = list(block)
				block[-1] = self._ensureSemicolon(block[-1])
		elif isinstance(block, str) or isinstance(block, unicode):
			if not block.endswith(";"):
				block += ";"
		return block

MAIN_CLASS = Writer

# EOF - vim: tw=80 ts=4 sw=4 noet
