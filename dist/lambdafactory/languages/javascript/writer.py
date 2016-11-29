# -----------------------------------------------------------------------------
# Project   : LambdaFactory
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 2006-11-02
# Last mod  : 2016-09-11
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


class Writer(AbstractWriter):

	# The following generates short random variables. Note that it's not thread
	# safe.
	RNDVARLETTERS = string.ascii_letters + "01234567890"

	def __init__( self ):
		AbstractWriter.__init__(self)
		self.jsPrefix                = ""
		self.jsCore                  = "extend."
		self.jsSelf                  = "self"
		self.jsModule                = "__module__"
		self._moduleName             = None
		self._moduleType             = None
		self.supportedEmbedLanguages = ["ecmascript", "js", "javascript"]
		self.inInvocation            = False
		self.options                 = {} ; self.options.update(OPTIONS)
		self._generatedVars          = [0]

	def _getRandomVariable(self):
		"""Generates a new random variable."""
		s = "__"
		i = self._generatedVars[-1]
		c = self.RNDVARLETTERS
		l = len(c)
		while i >= l:
			s += c[i % l]
			i  = i / l
		s += c[i]
		self._generatedVars[-1] += 1
		return s

	def pushContext( self, value ):
		self._generatedVars.append(0)
		AbstractWriter.pushContext(self, value)

	def popContext( self ):
		AbstractWriter.popContext(self)
		self._generatedVars.pop()

	def _extendGetMethodByName(self, name):
		return self.jsSelf + ".getMethod('%s') " % (name)

	def _extendGetClass(self, variable=None):
		return "%s.getClass()" % (variable or self.jsSelf)

	def _isSymbolValid( self, string ):
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

	def getAbsoluteName( self, element, relativeModule=True ):
		"""Returns the absolute name for the given element. This is the '.'
		concatenation of the individual names of the parents."""
		names = [self._rewriteSymbol(element.getName())]
		while element.getParent():
			element = element.getParent()
			# FIXME: Some elements may not have a name
			if not isinstance(element, interfaces.IProgram):
				names.insert(0, self._rewriteSymbol(element.getName()))
		if relativeModule and len(names) > 1 and names[0] == self._moduleName:
			names = ["__module__"] + names[1:]
		return ".".join(names)

	def renameModuleSlot(self, name):
		if name == interfaces.Constants.ModuleInit: name = "init"
		if name == interfaces.Constants.MainFunction: name = "main"
		return name

	# =========================================================================
	# MODULES
	# =========================================================================

	def onModule( self, moduleElement ):
		"""Writes a Module element."""
		# Detects the module type
		if self.environment.options.get(MODULE_UMD):
			self._moduleType = MODULE_UMD
		elif self.environment.options.get(MODULE_GOOGLE):
			self._moduleType = MODULE_GOOGLE
		else:
			self._moduleType = MODULE_VANILLA
		self._withExtendIterate = self.environment.options.get(OPTION_EXTEND_ITERATE) and True or False
		module_name = self._rewriteSymbol(moduleElement.getName())
		self._moduleName = module_name
		code = [
			"// " + SNIP % ("%s.js" % (self.getAbsoluteName(moduleElement).replace(".", "/"))),
			self._document(moduleElement),
			self.options["ENABLE_METADATA"] and "function __def(v,m){var ms=v['__def__']||{};for(var k in m){ms[k]=m[k]};v['__def__']=ms;return v}" or "",
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
			code.append("__module__.__VERSION__='%s';" % (version.getContent()))
		# --- SLOTS -----------------------------------------------------------
		for name, value in moduleElement.getSlots():
			if isinstance(value, interfaces.IModuleAttribute):
				declaration = "{0}.{1}".format(module_name, self.write(value))
			else:
				# NOTE: Some slot values may be shadowed, in which case they
				# won't return any value
				value_code = self.write(value)
				if value_code:
					slot_name   = self.renameModuleSlot(name)
					declaration = "{0}.{1} = {2}".format(module_name, slot_name, value_code)
			code.append(declaration)
		# --- INIT ------------------------------------------------------------
		# FIXME: Init should be only invoked once
		code.append('if (typeof(%s.init)!="undefined") {%s.init();}' % (
			"__module__",
			"__module__"
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
		module_name = self._rewriteSymbol(moduleElement.getName())
		return [
			"var %s=(typeof(extend)!='undefined' && extend && extend.module && extend.module(\"%s\")) || %s || {};" % (module_name, self.getAbsoluteName(moduleElement) or module_name, module_name),
			"(function(%s){" % (module_name),
			"var {0}={2}, {1}={2}".format(self.jsSelf, self.jsModule, module_name),
		]

	def getModuleVanillaSuffix( self, moduleElement ):
		module_name = self._rewriteSymbol(moduleElement.getName())
		return ["})(%s);" % (module_name)]

	# === UMD MODULES =========================================================

	def getModuleUMDPrefix( self, moduleElement):
		# SEE: http://babeljs.io/docs/plugins/transform-es2015-modules-umd/
		module_name = self._rewriteSymbol(moduleElement.getName())
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
			"var __extend__ = typeof extend !== 'undefined' ? extend : window.extend || null;",
			"var __module__;"
			# NOTE: Here we don't prefix with var, so it creates a global
			"{0} = __module__ = exports = typeof exports === 'undefined' ? {{}} : exports;".format(module_name),
		]
		symbols = []
		for alias, module, slot in self.getImportedSymbols(moduleElement):
			if not slot:
				# Modules are already imported
				if alias:
					symbols.append("var {0} = {1};".format(alias or module, module))
			else:
				# Extend gets a special treatment
				if module != "extend" or alias:
					symbols.append("var {0} = {1}.{2};".format(alias or slot, module, slot))
		return [
			preamble.replace("MODULE", module_name).replace("IMPORT", imports),
		] + [
			"var {0} = require(\"{0}\");".format(_) for _ in imported
		] + symbols + module_declaration + ["// END:UMD_PREAMBLE"]

	def getModuleUMDSuffix( self, moduleElement ):
		module_name = self._rewriteSymbol(moduleElement.getName())
		return [
			"// START:UMD_POSTAMBLE",
			"if (__extend__) {{__extend__.module(\"{0}\", {0})}}".format(module_name),
			(
				"if (typeof window !== 'undefined') {{var n='{0}'.split('.');"
				"var c=window;for(var i=0;i<n.length;i++){{"
				"if(i<n.length-1){{c[n[i]]=c[n[i]]||{{}}}}"
				"else{{c[n[i]]={0}}}"
				"}}}}"
			).format(module_name),
			"return {0}".format(module_name),
			"});",
			"// END:UMD_POSTAMBLE"
		]

	# === GOOGLE MODULES ======================================================
	# https://github.com/google/closure-library/wiki/goog.module:-an-ES6-module-like-alternative-to-goog.provide

	def getModuleGooglePrefix( self, moduleElement):
		module_name = self._rewriteSymbol(moduleElement.getName())
		modules     = ["var {0} = goog.require('{0}');".format(_) for _ in self.getImportedModules(moduleElement)]
		symbols     = []
		for alias, module, slot in self.getImportedSymbols(moduleElement):
			if not slot:
				# Modules are already imported
				if alias:
					symbols.append("var {0} = {1};".format(alias or module, module))
			else:
				# Extend gets a special treatment
				if module != "extend" or alias:
					symbols.append("var {0} = {1}.{2};".format(alias or slot, module, slot))
		return [
			"// START:GOOGLE_PREAMBLE",
			"goog.loadModule(function(exports){",
			"goog.module('{0}');".format(module_name),
		] + modules + symbols + [
			"var __module__ = {0}; var {0} = exports;".format(module_name),
			"// END:GOOGLE_PREAMBLE"
		]

	def getModuleGoogleSuffix( self, moduleElement ):
		return [
			"// START:GOOGLE_POSTAMBLE",
			"return exports;",
			"});",
			"// END:GOOGLE_POSTAMBLE"
		]

	# =========================================================================
	# IMPORTS
	# =========================================================================

	def getImportedModules( self, moduleElement ):
		res = []
		for o in moduleElement.getImportOperations():
			if   isinstance(o, interfaces.IImportModuleOperation):
				res.append(o.getImportedModuleName())
			elif isinstance(o, interfaces.IImportSymbolOperation):
				res.append(o.getImportOrigin())
			elif isinstance(o, interfaces.IImportSymbolsOperation):
				res.append(o.getImportOrigin())
			elif isinstance(o, interfaces.IImportModulesOperation):
				res += o.getImportedModuleNames()
			else:
				raise NotImplementedError
		n = []
		for _ in res:
			if _ not in n:
				n.append(_)
		return n

	def getImportedSymbols( self, moduleElement ):
		res = []
		for o in moduleElement.getImportOperations():
			if   isinstance(o, interfaces.IImportModuleOperation):
				res.append([
					o.getAlias(),
					o.getImportedModuleName(),
					None
				])
			elif isinstance(o, interfaces.IImportSymbolOperation):
				res.append([
					o.getAlias(),
					o.getImportOrigin(),
					o.getImportedElement()
				])
			elif isinstance(o, interfaces.IImportSymbolsOperation):
				for s in o.getImportedElements():
					res.append([
						None,
						o.getImportOrigin(),
						s
					])
			elif isinstance(o, interfaces.IImportModulesOperation):
				for s in o.getImportedModuleNames():
					res.append([
						None,
						s,
						None
					])
			else:
				raise NotImplementedError
		return res

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
				parent = self.getAbsoluteName(parent_class)
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
		result = []
		result.append(self._document(classElement))
		result.append("name:'%s', parent:%s," % (self.getAbsoluteName(classElement, relativeModule=False), parent))
		# We collect class attributes
		attributes   = classElement.getAttributes()
		constructors = classElement.getConstructors()
		destructors  = classElement.getDestructors()
		methods      = classElement.getInstanceMethods()
		if classAttributes:
			written_attrs = ",\n".join(map(self.write, classAttributes))
			result.append("shared:{")
			result.append([written_attrs])
			result.append("},")
		if attributes:
			# In attributes, we only print the name, ans use Undefined as the
			# value, because properties will be instanciated at construction
			written_attrs = ",\n".join(["%s:undefined" % (self._rewriteSymbol(e.getName())) for e in attributes])
			result.append("properties:{")
			result.append([written_attrs])
			result.append("},")
		if constructors:
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
					"\tif (true) {var __super__=",
					"%s.getSuper(%s.getParent());" % (self.jsSelf, self.getAbsoluteName(classElement)),
					"__super__.initialize.apply(__super__,arguments);}"
				])
			for a in classElement.getAttributes():
				if not a.getDefaultValue(): continue
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
					self.options["ENABLE_METADATA"] and "initialize:__def(function(){" \
					or "initialize:function(){"
				),
				["var %s=this;" % (self.jsSelf)],
				constructor_attributes or None,
				invoke_parent_constructor,
				(
					(not self.options["ENABLE_METADATA"] and "},") or \
					"},{arguments:[]),"
				)
			)
			# in case no constructor is given, we create a default constructor
			result.append(default_constructor)
		if destructors:
			assert len(destructors) == 1, "Multiple destructors are not supported"
			result.append("%s," % (self.write(destructors[0])))
		if methods:
			written_meths = ",\n".join(map(self.write, methods))
			result.append("methods:{")
			result.append([written_meths])
			result.append("},")
		if classOperations:
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
			"%s:%s" % (self._rewriteSymbol(element.getName()), default_value)
		)

	def onClassAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			res = "%s:%s" % (self._rewriteSymbol(element.getName()), self.write(default_value))
		else:
			res = "%s:undefined" % (self._rewriteSymbol(element.getName()))
		return self._format(self._document(element), res)

	def onModuleAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			default_value = self.write(default_value)
			return self._format(
				self._document(element),
				"%s=%s" % (self._rewriteSymbol(element.getName()), default_value)
			)
		else:
			return self._format(
				self._document(element),
				"%s;" % (self._rewriteSymbol(element.getName()))
			)

	def onMethod( self, methodElement ):
		"""Writes a method element."""
		self.pushContext(methodElement)
		method_name = self._rewriteSymbol(methodElement.getName())
		if method_name == interfaces.Constants.Constructor: method_name = "init"
		if method_name == interfaces.Constants.Destructor:  method_name = "cleanup"
		res = self._format(
			self._document(methodElement),
			(
				self.options["ENABLE_METADATA"] and "%s:__def(function(%s){" \
				or "%s:function(%s){"
			) % (
				method_name,
				", ".join(map(self.write, methodElement.getParameters()))
			),
			["var %s=this;" % (self.jsSelf)],
			self._writeClosureArguments(methodElement),
			self.writeFunctionWhen(methodElement),
			self.writeFunctionPre(methodElement),
			list(map(self.write, methodElement.getOperations())),
			(
				(not self.options["ENABLE_METADATA"] and "}") or \
				"},%s)" % ( self._writeFunctionMeta(methodElement))
			)
		)
		self.popContext()
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
		self.pushContext(methodElement)
		method_name = self._rewriteSymbol(methodElement.getName())
		args        = methodElement.getParameters()
		res = self._format(
			self._document(methodElement),
			(
				self.options["ENABLE_METADATA"] and "%s:__def(function(%s){" \
				or "%s:function(%s){"
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
		self.popContext()
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
				or "%s:function(%s){"
			) % (method_name, ", ".join(map(self.write, method_args))),
			["return %s.%s.apply(%s, arguments);" % (
				self.getAbsoluteName(inheritedMethodElement.getParent()),
				method_name,
				self.getAbsoluteName(currentClass)
			)],
			(
				(not self.options["ENABLE_METADATA"] and "}") or \
				"},%s)" % ( self._writeFunctionMeta(inheritedMethodElement))
			)
		)

	def onConstructor( self, element ):
		"""Writes a constructor element"""
		self.pushContext(element)
		current_class = self.getCurrentClass()
		attributes    = []
		# FIXME: Same as onClass
		for a in current_class.getAttributes():
			if not a.getDefaultValue(): continue
			attributes.append("if (typeof(%s.%s)=='undefined') {%s.%s = %s;};" % (
				self.jsSelf, self._rewriteSymbol(a.getName()),
				self.jsSelf, self._rewriteSymbol(a.getName()),
				self.write(a.getDefaultValue()))
			)
		res = self._format(
			self._document(element),
			(
				self.options["ENABLE_METADATA"] and "initialize:__def(function(%s){" \
				or "initialize:function(%s){"
			)  % (
				", ".join(map(self.write, element.getParameters()))
			),
			["var %s=this;" % (self.jsSelf)],
			self._writeClosureArguments(element),
			attributes or None,
			list(map(self.write, element.getOperations())),
			(
				(not self.options["ENABLE_METADATA"] and "}") or \
				"},%s)" % ( self._writeFunctionMeta(element))
			)
		)
		self.popContext()
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
		self.pushContext(function)
		parent = function.getParent()
		name   = self._rewriteSymbol( function.getName() )
		if parent and isinstance(parent, interfaces.IModule):
			res = [
				(
					self.options["ENABLE_METADATA"] and "__def(function(%s){" \
					or "function(%s){"
				)  % (
					", ".join(map(self.write, function.getParameters()))
				),
				[self._document(function)],
				['var %s=%s;' % (self.jsSelf, self.getAbsoluteName(parent))],
				self._writeClosureArguments(function),
				self.writeFunctionWhen(function),
				list(map(self.write, function.getOperations())),
				(
					(not self.options["ENABLE_METADATA"] and "}") or \
					"},%s)" % ( self._writeFunctionMeta(function))
				)
			]
		else:
			res = [
				self._document(function),
				(
					self.options["ENABLE_METADATA"] and "__def(function(%s){" \
					or "function(%s){"
				)  % (
					", ".join(map(self.write, function.getParameters()))
				),
				self._writeClosureArguments(function),
				self.writeFunctionWhen(function),
				list(map(self.write, function.getOperations())),
				(
					(not self.options["ENABLE_METADATA"] and "}") or \
					"},%s)" % ( self._writeFunctionMeta(closure))
				)
			]
		if function.getAnnotations(withName="post"):
			res[0] = "var __wrapped__ = " + res[0] + ";"
			if parent and isinstance(parent, interfaces.IModule):
				res.insert(0, 'var %s=%s;' % (self.jsSelf, self.getAbsoluteName(parent)))
			res.append("var result = __wrapped__.apply(%s, arguments);" % (self.jsSelf))
			res.append(self.writeFunctionPost(function))
			res.append("return result;")
		self.popContext()
		return self._format(res)

	# =========================================================================
	# CLOSURES
	# =========================================================================

	def onClosure( self, closure, bodyOnly=False, transpose=None ):
		"""Writes a closure element. The `transpose` element is used
		to rename parameters when there is an `encloses` annotation in
		an iteration loop.
		"""
		self.pushContext(closure)
		operations = closure.getOperations ()
		if bodyOnly:
			result = [self.write(_) + ";" for _ in operations]
		else:
			result   = [
				self._document(closure),
				(
					self.options["ENABLE_METADATA"] and "__def(function(%s){" \
					or "function(%s){"
				) % ( ", ".join(map(self.write, closure.getArguments()))),
				self._writeClosureArguments(closure),
				list(map(self.write, operations)),
				(
					(not self.options["ENABLE_METADATA"] and "}") or \
					"},%s)" % ( self._writeFunctionMeta(closure))
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
		self.popContext()
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
		return self._format(
			"{",
			list(map(self.write, block.getOperations())),
			"}"
		)

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
				if p:
					return self.getAbsoluteName(p[0])
				else:
					return symbol_name
			else:
				assert self.resolve("self"), "Super must be used inside method"
				# FIXME: Should check that the element has a method in parent scope
				return "%s.getSuper(%s.getParent())" % (
					self.jsSelf,
					self.getAbsoluteName(self.getCurrentClass())
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
		elif isinstance(o, interfaces.IImportSymbolOperation):
			module_name = o.getImportOrigin()
			symbol_name = o.getImportedElement()
			return module_name + "." + symbol_name
		elif isinstance(o, interfaces.IImportSymbolsOperation):
			module_name = o.getImportOrigin()
			return module_name + "." + symbol_name
		else:
			raise Exception("Importation operation not implemeted yet")

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
			return "var %s=%s;" % (self._rewriteSymbol(s.getName()), self.write(v))
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
				process = self.write(rule.getProcess())
			else:
				assert isinstance(rule, interfaces.IMatchExpressionOperation)
				process = "{%s}" % (self.write(rule.getExpression()))
			# If the rule process is a block/closure, we simply expand the
			# closure. So we have
			# if (...) { code }
			# instead of
			# if (...) { (function(){code})() }
			if process and isinstance(process, interfaces.IClosure):
				process = self.writeClosureBody(process)
			elif process:
				process = "%s" % (self.write(process))
			else:
				process = '{}'
			predicate = rule.getPredicate()
			is_else   = isinstance(predicate, interfaces.IReference) and predicate.getName() == "True"
			if i==0:
				rule_code = (
					"if ( %s )" % (self.write(predicate)),
					process,
				)
			elif is_else or rule.hasAnnotation("else"):
				rule_code = (
					"else",
					process
				)
			else:
				rule_code = (
					"else if ( %s )" % (self.write(predicate)),
					process,
				)
			result.extend(rule_code)
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
		it_name     = self._unique("_iterator")
		iterator    = iteration.getIterator()
		# If the iteration iterates on an enumeration, we can use a for
		# loop instead. We have to make sure that there is no scope forcing
		# though
		if isinstance(iterator, interfaces.IEnumeration) \
		and isinstance(iterator.getStart(), interfaces.INumber) \
		and isinstance(iterator.getEnd(),   interfaces.INumber) \
		and (isinstance(iterator.getStep(), interfaces.INumber) or not iterator.getStep()):
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
		self.pushContext(iteration)
		closure = iteration.getClosure()
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
		self.popContext()
		return self._format(
			# OK, so it is a bit complicated here. We start by storing a reference
			# to the iterated expression
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
				closure,
			),
			"}"
		)

	def onRepetition( self, repetition ):
		return self._format(
			"while (%s) " % (self.write(repetition.getCondition())),
			self.write(repetition.getProcess())
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
		#return "throw extend.FLOW_BREAK;"
		return "break"

	def onContinue( self, breaking ):
		"""Writes a continue operation."""
		#return "throw extend.FLOW_CONTINUE"
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
	# HELEPR
	# =========================================================================

	def _document( self, element ):
		if element.getDocumentation():
			doc = element.getDocumentation()
			res = []
			for line in doc.getContent().split("\n"):
				res.append("// " + line)
			return "\n".join(res)
		else:
			return None

MAIN_CLASS = Writer

# EOF - vim: tw=80 ts=4 sw=4 noet
