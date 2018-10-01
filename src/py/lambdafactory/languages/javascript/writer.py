# encoding: utf8
# -----------------------------------------------------------------------------
# Project   : LambdaFactory
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ffctn.com>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 2006-11-02
# Last mod  : 2017-10-30
# -----------------------------------------------------------------------------

# TODO: Cleanup the code generation by moving the templates to the top
#       and creating better generic functions
# TODO: When constructor is empty, should assign default attributes anyway
# TODO: Support optional meta-data
# TODO: Provide a global rewrite operation
# TODO: Use const whenever possible

from   lambdafactory.modelwriter import AbstractWriter, flatten
import lambdafactory.interfaces as interfaces
import lambdafactory.reporter   as reporter
from   lambdafactory.splitter import SNIP
import os.path, re, time, string, random, json, sys

PYTHON2 = sys.version_info[0] < 3
if not PYTHON2:
	unicode = str

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
continue const default
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
OPTION_TESTS          = "tests"
OPTION_NOBINDING      = "nobinding"

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

UNIT_OPERATORS = {
	"=="     : "equals",
	"!="     : "different",
	">"      : "greater",
	"<"      : "smaller",
	"<="     : "smallerOrEqual",
	">="     : "greaterOrEqual",
	"is"     : "same",
	"is not" : "notSame",
	"is?"    : "ofType",
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
	RNDVARLETTERS  = "ijklmonpqrstuvwxyzabcdefgh"
	UNIT_OPERATORS = UNIT_OPERATORS
	RUNTIME_OPS = {
		"isIn"   :"__in__",
		"map"    :"__map__",
		"filter" :"__filter__",
		"reduce" :"__reduce__",
		"reducer":"__reduce_right__",
		"iterate":"__iterate__"
	}

	def __init__( self ):
		AbstractWriter.__init__(self)
		# If the runtime functions have a prefix
		self.runtimePrefix           = "runtime."
		# Only used in the declration of constructs (class, trait, singleton)
		self.declarePrefix           = "runtime_oop."
		self.jsSelf                  = "self"
		self.jsModule                = "__module__"
		self.jsInit                  = "__init__"
		self._moduleType             = None
		self.supportedEmbedLanguages = ["ecmascript", "js", "javascript"]
		self.options                 = {} ; self.options.update(OPTIONS)
		self._generatedVars          = [0]
		self._isNice                 = False
		self._withUnits              = False
		self.runtimeModules          = [self.runtimePrefix[:-1], self.declarePrefix[:-1].replace("_", ".")]

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
		) or (isinstance(target, interfaces.IReference) and target.getReferenceName() == "super")

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
		if not element or not element.getName(): return None
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
				n = element.getName()
				if n:
					names.insert(0, n)
		return names if asList else ".".join(names)

	def getSafeName( self, element ):
		"""Returns the same as absolute name but with `_` instead of `_`."""
		if self._moduleType == MODULE_VANILLA:
			return self.getAbsoluteName(element).replace("/", ".").replace(":", ".")
		else:
			if isinstance(element, interfaces.IProgram) or isinstance(element, interfaces.IModule):
				return self.getAbsoluteName(element).replace(".", "_").replace("/", ".").replace(":", ".")
			else:
				name = self.getName()
				return self.getSafeSuperName(element) + ("." + name if name else "")

	def getSafeSuperName( self, element ):
		"""Returns the absolute name of the given element's parent."""
		parent = element.getParent()
		name   = element.getName()
		if not parent:
			return name
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
		self._withUnits     = self.environment.options.get(OPTION_TESTS)
		self._noBinding     = self.environment.options.get(OPTION_NOBINDING)
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
					declaration   += u"{0}.{1} = {2}".format(module_name, slot_name, self._format(value_code))
					if isinstance(value, interfaces.IClass):
						self.pushContext(value)
						declaration += ";\n" + self._format(self._onClassPostamble(value, module_name + "." + slot_name))
						self.popContext()
			code.append(self._document(value))
			code.append(declaration)
		# --- INIT ------------------------------------------------------------
		# FIXME: Init should be only invoked once
		if self._moduleType != MODULE_VANILLA and not self._noBinding:
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
		for _ in self._writeUnitTests(moduleElement):
			code.append(_)
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
			pass
			# NOTE: Disabled for now
			declaration.append("const {0}=typeof(runtime)!='undefined' ? "
				"{1}module('{0}') : (typeof({0})!='undefined' ? {0} : "
				"{{}});".format(local_name, self.runtimePrefix))
		else:
			parents = []
			current = names[-1]
			for i,prefix in enumerate(names):
				parents.append(prefix)
				parent_abs_name      = ".".join(parents)
				parent_safe_name = "_".join(parents)
				declaration.append(
					"const {0}=typeof({2})!='undefined' ? "
					"{2}module('{1}') : (typeof({1})!='undefined' ? {1} : "
					"{{}});".format(parent_safe_name, parent_abs_name, self.runtimePrefix))
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
					symbols.append("const {0} = {1};".format(alias or module, module))
			else:
				# Extend gets a special treatment
				if alias:
					symbols.append("const {0} = {1}.{2};".format(alias or slot, module, slot))
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
		imported    = list(set(self.runtimeModules + [_ for _ in self.getImportedModules(moduleElement)]))
		imports     = (", " + ", ".join(['"' + _ + '"' for _ in imported])) if imported else ""
		preamble = """// START:UMD_PREAMBLE
		(function (global, factory) {
			\"use strict\";
			if (typeof define === "function" && define.amd) {
				return define(["require", "exports" IMPORTS], factory);
			} else if (typeof exports !== "undefined") {
				return factory(require, exports);
			} else {
				var _module  = {exports:{}};
				var _require = function(_){
					_=_.split(".");_.reverse();
					var c=global;
					while (c && _.length > 0){c=c[_.pop()]}
					return c;
				}
				factory(_require, _module.exports);
				global.actual = _module.exports;
				return _module.exports;
			}
		})(this, function (require, exports) {""".replace(
			"MODULE", module_name
		).replace(
			"IMPORTS", imports
		).replace("\n\t\t", "\n")
		module_declaration = [
			"const __module__ = typeof(exports)==='undefined' ? {} : exports;",
			"const {0} = __module__;".format(module_name),
		]
		symbols = []
		for alias, module, slot, op in self.getImportedSymbols(moduleElement):
			safe_module = module.replace(".", "_")
			if not slot:
				# Modules are already imported
				if alias:
					symbols.append("const {0} = {1};".format(alias or safe_module, safe_module))
			else:
				pass
				# NOTE: Disabled 2017-05-08, as references to imported symbols
				# are always absolute.
				# Extend gets a special treatment
				# if module != "extend" or alias:
				# 	symbols.append("var {0} = {1}.{2};".format(alias or slot, safe_module, slot))
		return [
			preamble.replace("MODULE", module_name).replace("IMPORT", imports),
		] + [
			"const {0} = require(\"{1}\");".format(_.replace(".","_"), _) for _ in imported
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
				pass
				# NOTE: Disabled 2017-05-08
				# Extend gets a special treatment
				#if module != "extend" or alias:
				#	symbols.append("var {0} = {1}.{2};".format(alias or slot, module.replace(".", "_"), slot))
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
			"const {0} = exports;".format(module_name),
			"const __module__ = {0};".format(module_name),
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
				line = "if (typeof (c.{0}) === 'undefined') {{ c.{0} = __module__; }}".format(name)
			res.append(line)
		return (self._section("Module registration") if self._isNice else []) + [
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
		return self.onClass(element, "Singleton")

	def onTrait( self, element ):
		return self.onClass(element, "Trait")

	def _onClassPostamble( self, element, name=None ):
		classAttributes = element.getClassAttributes()
		name = name or self.getAbsoluteName(element).replace(".", "_")
		for attr in classAttributes:
			self.pushContext(attr)
			default_value = attr.getDefaultValue()
			yield "{0}.{1} = {2};".format(
				name,
				self._rewriteSymbol(attr.getName()),
				self.write(default_value) if default_value else "undefined"
			)
			self.popContext()

	def onClass( self, classElement, classType="Class" ):
		"""Writes a class element."""
		parents, traits = self.getClassParentAndTraits(classElement)
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
		for meth in classElement.getClassMethods():
			classOperations[self._rewriteSymbol(meth.getName())] = meth
		classOperations = list(classOperations.values())
		classAttributes = classElement.getClassAttributes()
		# === RESULT ==========================================================
		result = []
		result.append(           "name  :'%s'," % (self.getAbsoluteName(classElement)))
		if parent: result.append("parent: %s," % (parent))
		if traits: result.append("traits: [{0}],".format(", ".join(self.getSafeName(_) for _ in traits)))
		# We collect class attributes
		attributes   = classElement.getAttributes()
		constructors = classElement.getConstructors()
		destructors  = classElement.getDestructors()
		methods      = classElement.getInstanceMethods()
		accessors    = classElement.getAccessors()
		mutators     = classElement.getMutators()
		# NOTE: We need to defer the shared attrs in case we create a value
		# that depends on a class
		if attributes:
			# In attributes, we only print the name, ans use Undefined as the
			# value, because properties will be instanciated at construction
			result += self._group("Properties", 1)
			# written_attrs = ",\n".join(["%s:%sNOTHING" % (self._rewriteSymbol(e.getName()), self.declarePrefix) for e in attributes])
			attributes = []
			for a in classElement.getAttributes():
				default_value = a.getDefaultValue()
				name = self._rewriteSymbol(a.getName())
				attributes.append("{0}.{1} = {2};".format(
					self._runtimeSelfReference(classElement), name,
					self.write(default_value) if default_value else "undefined",
					self.declarePrefix
				))
			result.append("properties: (function(){var self=this;")
			result.append(attributes)
			result.append("}),")
		if constructors:
			result += self._group("Constructor", 1)
			assert len(constructors) == 1, "Multiple constructors are not supported yet"
			result.append(self._format(self.write(constructors[0])) + ",")
		else:
			# We write the default constructor, see 'onConstructor' for for
			# details.
			constructor_attributes    = []
			invoke_parent_constructor = None
			# FIXME: Implement proper attribute initialization even in
			# subclasses
			if len(parents) > 0:
				# NOTE: The runtime takes care of initializing traits
				# We have to do the following JavaScript code because we're not
				# sure to know the parent constructors arity -- this is just a
				# way to cover our ass. We encapsulate the __super__ declaration
				# in a block to avoid scoping problems.
				invoke_parent_constructor = u"\n".join(
					#"if ({0} && {0}.__init__) {{ {0}.__init__.apply(self, arguments); }}".format(self.getSafeSuperName(_)) for _ in parents
					"if ({0}) {{ {0}.apply(self, arguments); }}".format(self.getSafeSuperName(_)) for _ in parents
				)

			# We only need a default constructor when we have class attributes
			# declared and no constructor declared
			default_constructor = (
				(
					self.options["ENABLE_METADATA"] and "initialize: __def(function(){" \
					or "initialize: function(){"
				),
				["const %s = this;" % (self._runtimeSelfReference(classElement))],
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
		if accessors:
			result.append("accessors:{")
			result.extend([",\n\n".join(self._format(self.onMethod(_)) for _ in accessors)])
			result.append("},")
		if mutators:
			result.append("mutators:{")
			result.extend([",\n\n".join(self._format(self.onMethod(_)) for _ in mutators)])
			result.append("},")
		if methods:
			result += self._group("Methods", 1)
			written_meths = ",\n\n".join(self._format(self.write(_)) for _ in methods)
			result.append("methods: {")
			result.append([written_meths])
			result.append("},")
		if classOperations:
			result += self._group("Class methods", 1)
			written_ops = ",\n\n".join(self._format(self.write(_)) for _ in classOperations)
			result.append("operations:{")
			result.append([written_ops])
			result.append("},")
		if result[-1][-1] == ",":result[-1] =result[-1][:-1]
		res =  [
			self.declarePrefix + classType + "({",
			result,
			"})"
		]
		return res

	def onAttribute( self, element ):
		default_value = element.getDefaultValue()
		if default_value: default_value = self.write(default_value)
		else: default_value = "undefined"
		return (
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
		return (self._document(element), res)

	def onModuleAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			default_value = self.write(default_value)
			return (
				"%s = %s" % (self._rewriteSymbol(element.getName()), default_value)
			)
		else:
			return (
				"%s;" % (self._rewriteSymbol(element.getName()))
			)

	def onConstructor( self, element ):
		"""Writes a constructor element"""
		self.pushVarContext(element)
		current_class = self.getCurrentClass()
		res = (
			self._document(element),
			(
				self.options["ENABLE_METADATA"] and "initialize: __def(function( %s ){" \
				or "initialize: function( %s ){"
			)  % (
				", ".join(map(self.write, element.getParameters()))
			),
			list(self._writeAllocations(element)),
			["const %s = this;" % (self._runtimeSelfReference(element))],
			self._writeClosureArguments(element),
			list(map(self._writeStatement, element.getOperations())),
			(
				(not self.options["ENABLE_METADATA"] and "}") or \
				"}, %s)" % ( self._writeFunctionMeta(element))
			)
		)
		self.popVarContext()
		return res

	def onMethod( self, element ):
		"""Writes a method element."""
		return self._onFunctionBody(element, prefix="\"{0}\": ".format(
			(element.getName())))

	def onClassMethod( self, element ):
		"""Writes a class method element."""
		return self._onFunctionBody(element, prefix="\"{0}\": ".format(
			(element.getName())))

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

	def writeFunctionWhen(self, methodElement):
		return [self.write(
			"if (!({0})) {{return undefined}};".format(self.write(_.content))
		) for _ in methodElement.getAnnotations("when")]

	def writeFunctionPre(self, methodElement):
		# FIXME
		return ["extend.assert({0}, 'Precondition failed in {1}):".format(self.write(_.content), self.getScopeName()) for _ in methodElement.getAnnotations("pre")]

	# =========================================================================
	# FUNCTIONS
	# =========================================================================

	def onFunctionWhen(self, function ):
		res = []
		for a in function.getAnnotations(withName="when"):
			res.append("if (!(%s)) {return}" % (self.write(a.getContent())))
		return (res) or None

	def onFunctionPost(self, function ):
		res = []
		for a in function.getAnnotations(withName="post"):
			res.append("if (!(%s)) {throw new Exception('Assertion failed')}" % (self.write(a.getContent())))
		return (res) or None

	def onInitializer( self, element ):
		return self.onFunction(element)

	def onFunction( self, function ):
		"""Writes a function element."""
		return self._onFunctionBody(function)

	def _onFunctionBody( self, element, prefix="" ):
		"""Writes the body of a function."""
		self.pushVarContext(element)
		res         = []
		parent      = element.getParent()
		name        = self._rewriteSymbol( element.getName() )
		if name == interfaces.Constants.Constructor:
			name = "init"
		elif name == interfaces.Constants.Destructor:
			name = "cleanup"
		event       = element.getAnnotation("event")
		# Content
		self_ref    = []
		allocations = list(self._writeAllocations(element))
		params      = ", ".join(map(self.write, element.getParameters()))
		arguments   = self._writeClosureArguments(element)
		guards      = self.writeFunctionWhen(element)
		pre         = self.writeFunctionPre(element)
		if event:
			operations = ["return " + self._runtimeEventBind(event.getContent()) + ";"]
		else:
			operations = list(map(self._writeStatement, element.getOperations()))
		if parent and isinstance(parent, interfaces.IModule):
			self_ref = ['const {0} = {1};'.format(
				self._runtimeSelfReference(element),
				self.getResolvedName(element.parent))
			]
		else:
			self_ref = ["const {0} = this;".format(self._runtimeSelfReference(element))]
		# We build the whole thing
		res = [
			"{0}function({1}){{".format(prefix, params),
		] + self_ref + arguments + guards + pre + allocations + operations + ["}"]
		# FIXME: Rework
		# And append the annotations
		if element.getAnnotations(withName="post"):
			res[0] = "const __wrapped__ = " + res[0] + ";"
			if parent and isinstance(parent, interfaces.IModule):
				res.insert(0, 'const %s=%s;' % (self._runtimeSelfReference(element), self.getAbsoluteName(parent)))
			res.append("const result = __wrapped__.apply(%s, arguments);" % (self._runtimeSelfReference(element)))
			res.append(self.writeFunctionPost(element))
			res.append("return result;")
		res = self.writeDecorators(element, res)
		self.popVarContext()
		return res

	def onAccessor( self, element ):
		return self.onMethod(element)

	def onMutator( self, element ):
		return self.onMethod( element)

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
		implicits  = [_ for _ in self._writeAllocations(closure)]
		if bodyOnly:
			result = implicits + [self._format(self.write(_)) + ";" for _ in operations]
		else:
			result = [
				self._document(closure),
				(
					self.options["ENABLE_METADATA"] and "__def(function(%s) {" \
					or "function(%s) {"
				) % ( ", ".join(map(self.write, closure.getArguments()))),
				self._writeClosureArguments(closure),
				implicits,
				list(map(self._writeStatement, operations)),
				(
					(not self.options["ENABLE_METADATA"] and "}") or \
					"}, %s)" % ( self._writeFunctionMeta(closure))
				)
			]
		# We format the result as a string
		# FIXME: Should not do that
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
		return ('{', list(map(self._writeStatement, closure.getOperations())), '}')

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
				result.append("%s = %s__slice__(arguments,%d)" % (
					arg_name,
					self.runtimePrefix,
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
		return (self._writeStatement(_) for _ in block.getOperations())

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
		elif symbol_name == "Nothing":
			return self._runtimeNothing()
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
			return symbol_name
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
				if self.isIn(interfaces.IMethod) or self.isIn(interfaces.IConstructor) or self.isIn(interfaces.IDestructor):
					return self._runtimeWrapMethodByName(symbol_name, value, element)
				else:
					#return "%s.%s" % (self._runtimeSelfReference(value), symbol_name)
					return "%s.%s" % (self.getSafeName(scope), symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				# FIXME: Same as above
				if self.isIn(interfaces.IClassMethod):
					return "%s.%s" % (self._runtimeSelfReference(value), symbol_name)
				else:
					return self._runtimeGetCurrentClass(element) + "." + symbol_name
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
		if isinstance(o, interfaces.IImportModuleOperation):
			return self.getSafeName(self.getProgram().getModule(o.getImportedModuleName()))
		elif isinstance(o, interfaces.IImportModulesOperation):
			return self.getSafeName(self.getProgram().getModule(name))
		elif isinstance(o, interfaces.IImportSymbolOperation):
			module_name = o.getImportOrigin()
			symbol_name = o.getImportedElement()
			return self.getSafeName(self.getProgram().getModule(module_name)) + "." + symbol_name
		elif isinstance(o, interfaces.IImportSymbolsOperation):
			module_name = o.getImportOrigin()
			match       = None
			for _ in o.getImportedElements():
				if _.getImportedName() == name:
					match = _
			if match:
				# NOTE: We don't use the alias here but the actual symbol
				# because we're doing a fully prefixed resolution because we're
				# doing a fully prefixed resolution.
				return self.getSafeName(self.getProgram().getModule(module_name)) + "." + match.getImportedElement()
			else:
				raise Exception("Could not find imported symbol: {0} in parent operation {1}".format(name, op))
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
		if isinstance(key, interfaces.IString) or isinstance(key, interfaces.INumber):
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
			return self._runtimeMapFromItems(element.getItems())

	# =========================================================================
	# OPERATIONS
	# =========================================================================

	def onAllocation( self, allocation, prefix="" ):
		"""Writes an allocation operation."""
		s = allocation.getSlotToAllocate()
		v = allocation.getDefaultValue()
		# NOTE: We don't do any declaration here as the declaration happens
		# in the parent scope
		if v:
			return "%s%s = %s" % (prefix, self._rewriteSymbol(s.getName()), self._format(self.write(v)))
		else:
			return "%s%s" % (prefix, self._rewriteSymbol(s.getName()))

	def onAssignment( self, assignation ):
		"""Writes an assignation operation."""
		# TODO: If assignment target is an  access, we should rewrite it with
		# explicit length
		parent = self.context[-2]
		rvalue = assignation.getAssignedValue()
		if isinstance(rvalue, interfaces.IChain):
			return "{0}{1} = {2}".format("".join(self.write(rvalue)), self.write(assignation.getTarget()), rvalue.dataflow.getImplicitSlotFor(rvalue).getName())
		else:
			return "%s = %s" % (
				self.write(assignation.getTarget()),
				self.write(rvalue)
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
			r.append("{0}__sprintf__(_[{0}],{1})".format(self.runtimePrefix, v, json.dumps(f)) if f else "_[{0}]".format(v))
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
		res = "{0}__range__({1},{2})".format(self.runtimePrefix, start, end)
		step = operation.getStep()
		if step: res += " step " + self.write(step)
		return res

	def onDecomposition( self, element ):
		return self.onResolution(element)

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
			# If there is no context, we write the reference as-is
			return self.write(reference)
		elif context_name == "super":
			return self._runtimeSuperResolution(resolution)
		elif isinstance(resolution, interfaces.IDecomposition):
			return self._runtimeDecompose(context, reference)
		else:
			# NOTE: We don't need to rewrite symbols in decompositions
			return self.write(context) + "." + reference.getReferenceName()

	def onComputation( self, computation ):
		"""Writes a computation operation."""
		# FIXME: For now, we supposed operator is prefix or infix
		operands = [x for x in computation.getOperands() if x!=None]
		operator = computation.getOperator()
		name     = operator.getReferenceName()
		# FIXME: Add rules to remove unnecessary parens
		if len(operands) == 1:
			res = "%s%s" % (
				self.write(operator),
				self.write(operands[0])
			)
		else:
			if name == "has":
				res = '(!(%s.%s===undefined))' % (
					self.write(operands[0]),
					self.write(operands[1])
				)
			elif name == "in":
				res = self._runtimeIsIn(operands[0], operands[1])
			elif name == "not in":
				res = "!(" + self._runtimeIsIn(operands[0], operands[1]) + ")"
			elif name == "!+":
				res = self._runtimeEventBind(computation)
			elif name == "!!":
				res = self._runtimeEventBindOnce(computation)
			elif name == "!-":
				res = self._runtimeEventUnbind(computation)
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
		# FIXME: Special handling of assert
		target = invocation.getTarget()
		target_name = None
		if isinstance(target, interfaces.IResolution):
			target_name = self.write(target)
		elif isinstance(target, interfaces.IReference):
			s, e = self.resolve(target)
			target_name = self.getAbsoluteName(e) if e else target.getReferenceName()
		# FIXME: This should be defined as options
		if target_name in ("extend.assert", "__assert__", "ff.errors.assert"):
			return self._runtimeAssert(invocation)
		elif invocation.isByPositionOnly():
			if self._isSuperInvocation(invocation):
				return self._runtimeSuperInvocation(invocation)
			else:
				return self._runtimeInvocation(invocation)
		else:
			raise NotImplementedError

	def onEventTrigger( self, element ):
		return self._runtimeEventTrigger(element)

	def onEventBind( self, element ):
		return self._runtimeEventBind(element)

	def onEventBindOnce( self, element ):
		return self._runtimeEventBindOnce(element)

	def onEventUnbind( self, element ):
		return self._runtimeEventUnbind(element)

	def onArgument( self, element ):
		r = self.write(element.getValue())
		if element.getValue().hasAnnotation("ellipsis"):
			return "..." + r
		elif element.isAsMap():
			# FIXME: Like **kwargs
			raise NotImplementedError
		elif element.isAsList():
			# FIXME: Like *kwargs
			raise NotImplementedError
		elif element.isByName():
			# FIXME: Maybe rewrite name
			raise NotImplementedError
		else:
			return r

	def onInstanciation( self, element ):
		"""Writes an invocation operation."""
		i = element.getInstanciable()
		t = self.write(i)
		# Invocation targets can be expressions
		if not isinstance(i, interfaces.IReference): t = "(" + t + ")"
		args = []
		with_ellipsis = None
		for i,a in enumerate(element.getArguments() or ()):
			if a.getValue().hasAnnotation("ellipsis"):
				with_ellipsis = i
			args.append(a)
		if with_ellipsis is None:
			return "new %s(%s)" % (
				t,
				", ".join(self.write(_) for _ in element.getArguments())
			)
		else:
			# SEE: https://stackoverflow.com/questions/1606797/use-of-apply-with-new-operator-is-this-possible/8843181#8843181
			return "(function(c){{return new (Function.prototype.bind.apply(c,Array.prototype.slice.call(arguments,0,{2}+1).concat(arguments[{2}+1])));}})({0},{1})".format(
				t,
				", ".join(self.write(_.getValue()) for _ in element.getArguments()),
				i
			)


	def onChain( self, chain ):
		target = self.write(chain.getTarget())
		v      = self._getRandomVariable()
		groups = chain.getGroups()
		implicit_slot = chain.dataflow.getImplicitSlotFor(chain)
		prefix        = ""
		op            = self.write(chain.getOperator())
		if op == "...":
			prefix = implicit_slot.getName() + "="
		return [
			implicit_slot.getName() + "=" + self.write(chain.getTarget()) + ";",
		] + [
			# We filter out the implict reference
			prefix + self._format(self.write(g)) + ";" for g in groups if not isinstance(g, interfaces.IImplicitReference)
		]

	def onSelection( self, selection ):
		# If-expressions are not going to be with a process or block as parent.
		in_process = isinstance(self.context[-2], interfaces.IProcess) or isinstance(self.context[-2], interfaces.IBlock)
		if not in_process and selection.hasAnnotation("if-expression"):
			return self._format(self._writeSelectionInExpression(selection))
		rules     = selection.getRules()
		#implicits = [_ for _ in self._writeImplicitAllocations(selection)]
		implicits = []
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
			if is_expression:
				body = "\t" + self.write(process)
			else:
				body = self._writeStatement(process)
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
		return result

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
		return self._runtimeFilter(i,p)
		# FIXME: We used to have extra closure/predicate for the
		# filter, but Sugar2 outputs a different model.
		# if c and p and (c is not p):
		# 	return self._runtimeMap(
		# 		self._runtimeFilter(i, p),
		# 		c
		# 	)
		# elif c:
		# 	return self._runtimeMap(i,c)
		# else:
		# 	return self._runtimeFilter(i,p)


	def onReduceIteration( self, iteration ):
		op = iteration.getAnnotation("operator")
		return self._runtimeReduce(
			iteration.getIterator(),
			iteration.getClosure(),
			iteration.getInitialValue(),
			op.getContent() == "::<" if op else False
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
			"var {l}={iterator};".format(l=l, iterator=iterator),
			# NOTE: Was getOwnPropertyNames
			"var {k}={l} instanceof Array ? {l} : ({l} instanceof Object ? Object.keys({l}) : []);".format(k=k, l=l),
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
		is_lvalue = isinstance(operation.parent, interfaces.IAssignment) and operation.parent.getTarget() is operation
		if is_direct or is_lvalue:
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
		return self._runtimeTypeIdentify(element)

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
			if closure_index >= 0 and iteration_index >= 0:
				closure   = self.context[closure_index]
				iteration = self.context[iteration_index]
				if closure == iteration.getClosure():
					return self._runtimeReturnBreak()
				elif iteration_index >= 0 and iteration_index > closure_index and not self.context[iteration_index].isRangeIteration():
					return self._runtimeReturnBreak()
				else:
					return "break"
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
		res         = ["try {", list(map(self._writeStatement, try_block.getOperations())), "}"]
		if try_catch:
			res[-1] += " catch(%s) {" % ( self.write(try_catch.getArguments()[0]))
			res.extend([
				list(map(self._writeStatement, try_catch.getOperations())),
				"}"
			])
		if try_finally:
			res[-1] += " finally {"
			res.extend([list(map(self._writeStatement, try_finally.getOperations())), "}"])
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

	def onWhere( self, eleent ):
		yield "// @where not implemented"

	# =========================================================================
	# TYPES
	# =========================================================================

	def onType( self, element, anonymous=False ):
		assert element.isConcrete()
		parents = element.getParents()
		traits  = [_ for _ in parents if isinstance(_, interfaces.ITrait)]
		parents = [_ for _ in parents if _ not in traits]
		self.pushContext (element)
		safe_name = self.getSafeName(element)
		abs_name  = element.getAbsoluteName()
		name      = "" if anonymous else ((element.getName() or "") + " ")
		slots     = [_ for _ in element.constraints if isinstance(_, interfaces.ISlotConstraint)]
		yield self.declarePrefix + "Class({"
		if parents:
			yield "\tparent: {0},".format(self.getSafeName(parents[0]))
		if slots:
			# FIXME: Not sure this is right
			yield "\tproperties: (function(self){"
			for i,s in enumerate(slots):
				suffix = "," if i < len(slots) else ""
				yield "\t\t{1} : {0}NOTHING{2}".format(self.declarePrefix, s.getName(), suffix)
			yield "\t}),"
		if traits:
			yield "\ttraits: [{0}],".format(",".join(self.getSafeName(_) for _ in traits))
		yield "\tinitialize:function({0}){{".format(", ".join(_.getName() for _ in slots))
		if parents:
			yield "\t\tObject.getPrototypeOf(this).apply(this,[]);"
		# TODO: Init traits?
		for s in slots:
			yield "\t\tthis.{0} = {0};".format(s.getName())
		yield "\t},"
		yield "\tname:\"{0}\"".format(abs_name)
		yield "});"
		self.popContext ()

	def onEnumerationType( self, element ):
		symbols = [_.getName() for _ in element.getSymbols()]
		m = self._runtimeModuleName(element)
		yield "{};"
		for i,_ in enumerate(symbols):
			# NOTE: Symbol is not supported yet, but would be preferrable
			yield "{0}.{1} = {0}.{3}.{1} = {4}(new Number({2}), \"{1}\");".format(m, _, i, element.getName(), self.runtimePrefix + "__set_name__")
			# FIXME: This has unexpected side effects
			# yield "{0}.{1}.__name__ = \"{2}.{1}\";".format(m, _, element.getName())


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
		for _ in self._writeAllocations(element, True):
			yield _

	def _writeAllocations( self, element, implicitsOnly=False ):
		"""Looks for allocations made within the current element and
		declares them all at once."""
		# FIXME: assert(element.dataflow) fails sometimes
		if element and element.dataflow:
			# NOTE: Implicits can sometimes be declared twice
			declared = {}
			for s in self._walkDataFlowSlots(element.dataflow):
				if s.isArgument() or s.isImported() or s.isEnvironment(): continue
				if s.isImplicit() or (not implicitsOnly):
					declared[s.getName()] = True
			if declared:
				yield "var {0};".format(", ".join(declared.keys()))

	def _walkDataFlowSlots( self, dataflow ):
		"""Recursively walks the slots of the given dataflow, skipping
		closures."""
		for s in dataflow.slots:
			yield s
		for c in dataflow.children:
			# We don't analyze the closures, as they have their own
			# scope.
			if isinstance(c, interfaces.IClosure): continue
			for s in self._walkDataFlowSlots(c):
				yield s

	def _writeUnitTests( self, element ):
		"""Writes the unit tests for this element and all its descendants,
		depth-first."""
		if self._withUnits:
			if isinstance(element, interfaces.IContext):
				for s,v,a,m in element.getSlots( ):
					for _ in self._writeUnitTests(v):
						yield _
			for where in element.getAnnotations("where"):
				yield self.onWhereAnnotation(where)


	def onWhereAnnotation( self, element ):
		"""Formats a "where" annotation, which stands for a unit test."""
		if self._withUnits:
			yield self._runtimeUnitTestPreamble(element)
			for op in element.getContent().getOperations():
				if isinstance(op, interfaces.IComputation):
					yield self._writeUnitComputation(op)
				else:
					yield self._writeStatement(op)
			yield self._runtimeUnitTestPostamble(element)

	def _writeUnitComputation( self, element ):
		op = element.getOperator().getName()
		l  = element.getLeftOperand  ()
		r  = element.getRightOperand ()
		uop = self.UNIT_OPERATORS.get(op)
		t   = self.write(element)
		if element.isUnary():
			yield ("__test__.{0}({1}).setCode({2});".format("assert", t, json.dumps(t)))
		elif uop:
			yield ("__test__.{0}({1}, {2}).setCode({3});".format(uop, self.write(l), self.write(r), json.dumps(t)))
		else:
			yield ("__test__.{0}({1}, {2}).setCode({4});".format("assert", t, json.dumps(t)))

	def _writeStatement( self, element ):
		r = self.write(element)
		if isinstance( element, interfaces.IContext):
			return r
		elif isinstance(r, str) or isinstance(r, unicode):
			return r + ";"
		else:
			return r

	# =========================================================================
	# RUNTIME
	# =========================================================================
	# This contains all the javascript snippets that are susceptible of
	# changing across the runties.

	def _runtimeSuper( self, element ):
		c = self.getCurrentClass()
		if self.isIn(interfaces.IClassAttribute) or self.isIn(interfaces.IClassMethod):
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
			p = self.getClassParents(c)
			if p:
				return "({0}.prototype)".format(
					self.getSafeSuperName(p[0]),
					self._runtimeSelfReference(element),
				)
			else:
				return "(Object.getPrototypeOf({0}).prototype)".format(
					self.getSafeSuperName(self.getCurrentClass()),
					self._runtimeSelfReference(element),
				)

	# def _runtimeSuperResolution( self, relement, reference ):
	def _runtimeSuperResolution( self, resolution ):
		# We need to check wether we're in a closure or not. If we are,
		# then we can't user `super`
		s = self._runtimeSelfReference(resolution)
		invocation = self.findInContext(interfaces.IInvocation)
		if invocation and invocation.getTarget() == resolution:
			# This is awkward, but that's how you emulate a super invocation
			return "Object.getPrototypeOf(Object.getPrototypeOf({0})).{1}.bind({0})".format(s, name)
		else:
			return n + ".bind(" + s + ")"

	def _runtimeSuperInvocation( self, element ):
		target = element.getTarget()
		if isinstance(target, interfaces.IReference) and target.getReferenceName() == "super":
			# We have a direct super invocation, which means we're invoking the
			# super constructor
			current_class = self.getCurrentClass()
			if isinstance(current_class, interfaces.ISingleton):
				# For singletons the absolute name is actually the class name
				return "/*singleton:super()*/Object.getPrototypeOf(Object.getPrototypeOf(self).constructor).apply({2},[{1}])".format(
					self.getSafeSuperName(self.getCurrentClass()),
					", ".join(map(self.write, element.getArguments())),
					self._runtimeSelfReference(),
				)
			else:
				return "/*super()*/Object.getPrototypeOf({0}).apply({2},[{1}])".format(
					self.getSafeSuperName(self.getCurrentClass()),
					", ".join(map(self.write, element.getArguments())),
					self._runtimeSelfReference(),
				)
		else:
			# Otherwise we're invoking a method from the super, which
			# is a simple call forwarding
			return "({0}.apply({2},[{1}]))".format(
				self.write(element.getTarget()),
				", ".join(map(self.write, element.getArguments())),
				self._runtimeSelfReference(),
			)

	def _runtimeGetMethodByName(self, name, value=None, element=None):
		return self._runtimeSelfReference(value) + "." + name

	def _runtimeWrapMethodByName(self, name, value=None, element=None):
		s = self._runtimeSelfReference(element)
		if isinstance(value, interfaces.IClassMethod):
			if self.findInContext(interfaces.IClassMethod):
				# In ES, we need to re-bind static methods when we're calling
				# them back, otherwise the reference will be lost.
				return "{0}.{1}.bind({0})".format(s, name)
			else:
				return "Object.getPrototypeOf({0}).constructor.{1}.bind(Object.getPrototypeOf({0}).constructor)".format(s, name)
		else:
			return "{0}.{1}.bind({0})".format(s, name)

	def _runtimeGetCurrentClass(self, element=None ):
		if self.indexLikeInContext(interfaces.IClassAttribute) >= 0:
			return self.getSafeName(self.findInContext(interfaces.IClass))
		else:
			return "(Object.getPrototypeOf({0}).constructor)".format(self.jsSelf)

	def _runtimeReturnBreak( self ):
		return "return {0}__BREAK__;".format(self.runtimePrefix)

	def _runtimeReturnContinue( self ):
		return "return {0}__CONTINUE__;".format(self.runtimePrefix)

	def _runtimeReturnType( self ):
		return "{0}__RETURN__".format(self.runtimePrefix)

	def _runtimeNothing( self ):
		return "{0}__NOTHING__".format(self.runtimePrefix)

	def _runtimeOp( self, name, *args ):
		return "{0}{1}({2})".format(
			self.runtimePrefix,
			self.RUNTIME_OPS.get(name) or name,
			", ".join(self.write(_) for _ in args)
		)

	def _runtimeIsIn( self, element, collection ):
		return self._runtimeOp("isIn", collection, element)

	def _runtimeModuleName( self, element=None ):
		return "__module__"

	def _runtimeMap( self, lvalue, rvalue ):
		return self._runtimeOp("map", lvalue, rvalue)

	def _runtimeReduce( self, lvalue, rvalue, initial=None, reverse=False ):
		name = "reducer" if reverse else "reduce"
		if initial is None:
			return self._runtimeOp(name, lvalue, rvalue)
		else:
			return self._runtimeOp(name, lvalue, rvalue, initial)

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
		resolved  = self.resolve("assert")
		if resolved:
			assert_symbol = self.getSafeName(resolved[1])
		else:
			assert_symbol = "__assert__"
		# TODO: We should include the offsets
		return "!({1}) && {0}(false, {2}, {3}, {4})".format(
			assert_symbol,
			predicate,
			json.dumps(self.getScopeName() + ":"),
			json.dumps("(failed `" + predicate + "`)"),
			", ".join(self.write(_) for _ in rest) or '""',
		)

	def _runtimeRestArguments( self, i ):
		return "(Array.prototype.slice.call(arguments," + str(i) + "))"

	def _runtimeDefaultValue( self, name, value ):
		return name + " === undefined ? " + value + " : " + name

	def _runtimeReturnValue( self, value ):
		return "return new " + self._runtimeReturnType() + "(" + value + ");"

	def _runtimeSelfReference( self, element=None ):
		return self.jsSelf

	def _runtimeSelfBinding( self, element ):
		c = self.getCurrentContext()
		t = "this"
		if isinstance(c, interfaces.IModule):
			t = "__module__"
		elif isinstance(c, interfaces.ISingleton):
			return None
		elif isinstance(c, interfaces.IClassMethod):
			t = "this"
			#t = self.getSafeName(self.getCurrentClass())
		return "const {0} = {1};".format(self.jsSelf, t)

	def _runtimeInvocation( self, element ):
		args = []
		with_ellipsis = None
		for i,a in enumerate(element.getArguments() or ()):
			if a.getValue().hasAnnotation("ellipsis"):
				with_ellipsis = i
			args.append(a)
		if with_ellipsis is None:
			return "{0}({1})".format(
				self.write(element.getTarget()),
				", ".join(self.write(_) for _ in args)
			)
		else:
			a = args[:with_ellipsis]
			n = args[with_ellipsis:]
			# FIXME: There was an __apply__ primitive before, but I don't
			# think it's necessary.
			args  = None
			# If there is only one narg and no regular arg, we don't
			# need to create a new array.
			if not a and len(n) == 1:
				args = self.write(n[0].getValue())
			else:
				args = "[{0}]{1}".format(
					", ".join(self.write(_) for _ in a),
					"".join(".concat(" + (self.write(_.getValue())) + ")" for _ in n),
				)

			target = element.getTarget()
			# TODO: Should we handle absolute references as well?
			if isinstance(target, interfaces.IDecomposition) or isinstance(target, interfaces.IResolution):
				# Here we need to make sure that when we have a.b(‥) that
				# `a` is preserved as the this. We need to use the runtime
				# as otherwise we'd need to evaluate the context twice.
				return "({0}__apply__({1},\"{2}\",{3}))".format(
					self.runtimePrefix,
					self.write(target.getContext()),
					self.write(target.getReference().getReferenceName()),
					args,
				)
			else:
				return "(({1}).apply(self,{2}))".format(
					self.runtimePrefix,
					self.write(element.getTarget()),
					args,
				)

	def _runtimePreamble( self ):
		return []

	def _runtimeAccess( self, target, index ):
		return "{0}__access__({1},{2})".format(self.runtimePrefix, target, index)

	# NOTE: Deprcated 2017-11-09 and left for reference
	# def _runtimeAccess( self, target, index ):
	# 	# FIXME: This should be included in a default runtime
	# 	return (
	# 		"(function(t,i){{return typeof(i) != 'number' ? t[i] : i < 0 "
	# 		"&& (typeof(t) == 'string' || t instanceof Array || t && isNumber(t.length))"
	# 		"? t[t.length + i] : t[i]}}({0},{1}))"
	# 	).format(target, index)

	def _runtimeSlice( self, target, start, end ):
		return "{0}__slice__({1},{2},{3})".format(self.runtimePrefix, target, start, end)

	def _runtimeDecompose( self, context, element ):
		return "{0}__decompose__({1}, \"{2}\")".format(
			self.runtimePrefix,
			self.write(context),
			element.getReferenceName()
		)


	def _runtimeEventTrigger( self, element ):
		target = self.write(element.getTarget()) or "undefined"
		event  = self.write(element.getEvent()) or "undefined"
		args   = element.getArguments()
		if len(args) == 0:
			args = "null"
		elif len(args) == 1:
			args = self.write(args[0])
		else:
			args = "[" + ", ".join(self.write(_) for _ in args) + "]"
		return "{0}__send__({1}, {2}, {3}, {1})".format(self.runtimePrefix, target, event, args)

	def _runtimeEventBind( self, element ):
		if isinstance(element, interfaces.IElement):
			return "{0}__bind__({1}, {2}, {3})".format(
				self.runtimePrefix,
				self.write(element.getTarget()) or "undefined",
				self.write(element.getEvent()) or "undefined",
				self.write(element.getArguments()) or "undefined",
			)
		else:
			return "{0}__bind__(self, \"{1}\", arguments[0], arguments[1])".format(
				self.runtimePrefix,
				element
			)

	def _runtimeEventBindOnce( self, element ):
		return "{0}__once__({1}, {2}, {3})".format(
			self.runtimePrefix,
			self.write(element.getTarget()) or "undefined",
			self.write(element.getEvent()) or "undefined",
			self.write(element.getArguments()) or "undefined",
		)

	def _runtimeEventUnbind( self, element ):
		return "{0}__unbind__({1}, {2}, {3})".format(
			self.runtimePrefix,
			self.write(element.getTarget()) or "undefined",
			self.write(element.getEvent()) or "undefined",
			self.write(element.getArguments()) or "undefined",
		)

	def _runtimeMapFromItems( self, items ):
		return "[{0}].reduce(function(r,v,k){{r[v[0]]=v[1];return r;}},{{}})".format(
			",".join("[{0},{1}]".format(self.write(k),self.write(v)) for k,v in items)
		)

	def _runtimeUnitTestPreamble( self, element ):
		return "(function(){{const __test__=new ff.util.testing.Unit('{0}');".format(self.getAbsoluteName(element.parent))

	def _runtimeUnitTestPostamble( self, element ):
		return "__test__.end();}());"

	def _runtimeTypeIdentify( self, element ):
		lvalue = self.write(element.getTarget())
		t      = element.getType()
		# FIXME: We should probably resolve the name, or try at least..
		rvalue = t.getName()
		# TODO: We should resolve the type in the namespace
		if (not t.parameters) or len(t.parameters) == 0:
			if rvalue == "String":
				rvalue = "'string'"
			elif rvalue == "Boolean":
				rvalue = "'boolean'"
			elif rvalue == "Number":
				rvalue = "'number'"
			elif rvalue == "Object":
				rvalue = "'object'"
			elif rvalue == "Undefined":
				rvalue = "'undefined'"
			elif rvalue == "None":
				rvalue = "null"
			else:
				slot, value = self.resolve(t.getReferenceName())
				if value:
					rvalue = self.getSafeName(value)
		return "{0}__isa__({1}, {2})".format(self.runtimePrefix, lvalue, rvalue)

MAIN_CLASS = Writer

# EOF - vim: tw=80 ts=4 sw=4 noet
