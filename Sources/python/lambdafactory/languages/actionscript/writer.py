#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : LambdaFactory - ActionScript back-end
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 01-Aug-2007
# Last mod  : 23-Apr-2009
# -----------------------------------------------------------------------------

# SEE: http://livedocs.adobe.com/specs/actionscript/3/
# TODO: When constructor is empty, should assign default attributes anyway

import os
from lambdafactory import interfaces
from lambdafactory import reporter
from lambdafactory.languages.javascript import writer as javascript
from lambdafactory.splitter import SNIP

#------------------------------------------------------------------------------
#
#  JavaScript Writer
#
#------------------------------------------------------------------------------

class Writer(javascript.Writer):

	def __init__(self ):
		javascript.Writer.__init__(self)
		self.jsCore   = "extend."
		self.supportedEmbedLanguages.extend(("as", "actionscript"))

	def _extendGetMethodByName(self, name,variable="__this__"):
		return self.jsCore+"getMethodOf(%s,'%s') " % (variable, name)

	def _extendGetClass(self, variable="__this__"):
		return self.jsCore+"getClassOf(%s) " % (variable)

	def getRuntimeSource(s):
		"""Returns the JavaScript code for the runtime that is necassary to run
		the program."""
		this_file = os.path.abspath(__file__)
		js_runtime = os.path.join(os.path.dirname(this_file), "runtime.as")
		f = file(js_runtime, 'r') ; text = f.read() ; f.close()
		return text

	def onProgram( self, programElement ):
		"""Writes a Program element."""
		return "\n".join(map(self.write, programElement.getModules()))

	def onModule( self, moduleElement):
		"""Writes a Module element."""
		files_code  = []
		module_path = self.getAbsoluteName(moduleElement).replace(".", "/")
		# Now we on every slot
		imports = []
		classes = []
		module_functions  = []
		module_attributes = []
		module_init_ops  = []
		for name, value in moduleElement.getSlots():
			if isinstance(value, interfaces.IClass):
				classes.append((name,value))
			elif isinstance(value, interfaces.IFunction) \
			and value.getName() == interfaces.Constants.ModuleInit:
				module_init_ops = value.getOperations()
			elif isinstance(value, interfaces.IFunction):
				module_functions.append((name,value))
			elif isinstance(value, interfaces.IModuleAttribute):
				module_attributes.append((name,value))
		for op in module_init_ops:
			if isinstance(op, interfaces.IAnnotation):
				pass
			else:
				raise Exception("ActionScript does not allow code in module: %s" % (op))
		imports.extend(moduleElement.getImportOperations())
		imports.reverse()
		# NOTE: ActionScript is a language designed by nazi-engineers, where you
		# MUST have one file per public element (Class or... variable.. or
		# function !). Very convenient when you have functions declared outside
		# of classes.
		for name, value in moduleElement.getSlots():
			f = None
			#if functions:
			#	f = map(lambda n,f: self.write(f), functions)
			#	functions = None
			value_code = self.write(value)
			if type(value_code) != list: value_code = [value_code]
			code = [
				"// " + SNIP % ("%s/%s.as" % (module_path, value.getName())),
				self._document(moduleElement),
				"package %s {" % (self.getAbsoluteName(moduleElement)),
				["import %s" % ( self.jsCore[:-1])],
				map(self.write, imports),
				f,
				value_code,
				"}"
			]
			files_code.extend(code)
		return self._format(
			*files_code
		)

	def onImportOperation( self, importElement):
		imported_name = self.write(importElement.getImportedElement())
		imported_elem = imported_name.split(".")[-1]
		if importElement.getAlias():
			return "import %s=%s" % (importElement.getAlias().getReferenceName(), imported_name)
		else:
			return "import %s" % (imported_name)

	def onClass( self, classElement ):
		"""Writes a class element."""
		parents    = classElement.getParentClasses()
		parent     = ""
		decoration = None
		# SWF Annotations are like 
		# [SWF(width="800", height="600", backgroundColor="#ffffff", frameRate="30")]
		# And allow wrapping a class into an SWF container
		swf_ann = classElement.getAnnotation("SWF")
		if swf_ann:
			decoration = "[SWF(%s)]" % (swf_ann.getContent())
		if len(parents) == 1:
			parent = "extends %s " % (self.write(parents[0]))
		elif len(parents) > 1:
			raise Exception("ActionScript back-end only supports single inheritance")
		# We create a map of class methods, including inherited class methods
		# so that we can copy the implementation of these
		classOperations = {}
		# Here, we've got to cheat a little bit. Each class method will 
		# generate an '_imp' suffixed method that will be invoked by the 
		for meth in classElement.getClassMethods():
			classOperations[meth.getName()] = meth
		classOperations = classOperations.values()
		classAttributes = {}
		for attribute in classElement.getClassAttributes():
			classAttributes[attribute.getName()] = self.write(attribute)
		classAttributes = classAttributes.values()
		class_code = []
		version = self.getCurrentModule().getAnnotation("version")
		if version:
			version = 'public static _VERSION_:String = "%s";' % (version.getContent())
		code       = [
			self._document(classElement),
			decoration,
			"public dynamic class %s %s{" % (classElement.getName(), parent),
			version,
			class_code,
			"}"
		]
		# We collect class attributes
		class_code.extend(map(self.write, classElement.getClassAttributes()))
		class_code.extend(map(self.write, classElement.getAttributes()))
		class_code.extend(map(self.write, classElement.getAttributeMethods()))
		class_code.extend(map(self.write, classElement.getConstructors()))
		# FIXME: What about destructors
		class_code.extend(map(self.write, classElement.getClassMethods()))
		class_code.extend(map(self.write, classElement.getInstanceMethods()))
		return self._format(code)


	def onAttribute( self, element ):
		"""Writes an argument element."""
		element_name     = element.getName()
		type_description = element.getTypeDescription()
		# FIXME: This is a hack which is needed because the AS3 backend needs a
		# :Class type for [Embed...] to work
		if type_description == "Class":
			element_name += ":" + type_description
		default_value    = element.getDefaultValue()
		if default_value:
			return self._format(
				self._document(element),
				"public var %s = %s; " % (element_name, self.write(default_value))
			)
		else:
			return self._format(
				self._document(element),
				"public var %s; " % (element_name)
			)

	def onClassAttribute( self, element ):
		"""Writes an argument element."""
		res = ""
		default_value = element.getDefaultValue()
		fleximage_ann = element.getAnnotation("fleximage")
		rest          = ""
		the_type      = "*"
		if default_value:
			rest = " = %s" % (self.write(default_value))
		if fleximage_ann:
			res +="[Embed(%s)]\n" % (fleximage_ann.getContent())
			the_type = "Class"
		res += "public static var %s:%s%s" % (element.getName(),the_type,rest)
		return self._format(self._document(element), res)
	
	def onConstructor( self, element ):
		"""Writes a constructor element."""
		current_class = self.getCurrentClass()
		attributes    = []
		return self._format(
			self._document(element),
			"public function %s(%s){" % (
				current_class.getName(),
				", ".join(map(self.write, element.getArguments()))
			),
			["var __this__=this"],
			self._writeClosureArguments(element),
			attributes or None,
			map(self.write, element.getOperations()),
			"}"
		)

	def _isTaggedAsOverride( self, element ):
		"""Tells if the given element has an "overrides" annotation."""
		# FIXME: We only handle the case where there is ONE or NO annotation, if
		# there is more (like "@as override, inline, utility", it will crash)
		annotation = element.getAnnotation("as")
		if annotation:
			content = annotation.getContent()
			if type(content) == list: content = content[0]
			return content.lower() == "overrides"
		else:
			return False

	def onMethod( self, methodElement ):
		"""Writes a method element."""
		method_name = methodElement.getName()
		# FIXME: The type description is put *as is*, while it should be
		# processed
		return_type = methodElement.getReturnTypeDescription()
		if return_type: return_type = ":" + return_type 
		else: return_type = ""
		class_name  = self.getCurrentClass().getName()
		if method_name == interfaces.Constants.Constructor: method_name = class_name
		if method_name == interfaces.Constants.Destructor:  method_name = "destroy"
		# FIXME: We should instead look if the method is already defined
		overrides = method_name in map(lambda x:x[0], methodElement.getParent().getInheritedSlots())
		overrides = (overrides or self._isTaggedAsOverride(methodElement)) and " override" or ""
		return self._format(
			self._document(methodElement),
			"public%s function %s(%s)%s {" % (
				overrides,
				method_name,
				", ".join(map(self.write, methodElement.getArguments())),
				return_type
			),
			["var __this__=this"],
			self._writeClosureArguments(methodElement),
			self.onFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def onAccessor( self, element ):
		method_name = element.getName()
		overrides   = self._isTaggedAsOverride(element) and " override" or ""
		return_type = element.getReturnTypeDescription()
		if return_type: return_type = ":" + return_type 
		return self._format(
			self._document(element),
			"public %s function get %s()%s {" % (
				overrides,
				method_name,
				return_type
			),
			["var __this__=this"],
			self._writeClosureArguments(element),
			self.onFunctionWhen(element),
			map(self.write, element.getOperations()),
			"}"
		)

	def onMutator( self, element ):
		method_name = element.getName()
		overrides   = self._isTaggedAsOverride(element) and " override" or ""
		return self._format(
			self._document(element),
			"public %s function set %s(%s):void {" % (
				overrides,
				method_name,
				", ".join(map(self.write, element.getArguments())),
			),
			["var __this__=this"],
			self._writeClosureArguments(element),
			self.onFunctionWhen(element),
			map(self.write, element.getOperations()),
			"}"
		)
	def onClassMethod( self, methodElement ):
		"""Writes a class method element."""
		class_name  = methodElement.getParent().getName()
		method_name = methodElement.getName()
		args        = methodElement.getArguments()
		return self._format(
			self._document(methodElement),
			"public static function %s(%s){" % (method_name, ", ".join(map(self.write, args))),
			["var __this__ = %s;" % (class_name)],
			self._writeClosureArguments(methodElement),
			self.onFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def onFunction( self, function ):
		"""Writes a function element."""
		parent = function.getParent()
		name   = function.getName() or ""
		prefix = isinstance(function.getParent(), interfaces.IModule) and "public " or ""
		res = [
			self._document(function),
			"%sfunction %s (%s){" % (
				prefix,
				name,
				", ".join(map(self.write, function.getArguments()))
			),
			self._writeClosureArguments(function),
			self.onFunctionWhen(function),
			map(self.write, function.getOperations()),
			"}"
		]
		if function.getAnnotations("post"):
			res[0] = "var __wrapped__ = " + res[0] + ";"
			if parent and isinstance(parent, interfaces.IModule):
				res.insert(0, 'var __this__=%s;' % (self.getAbsoluteName(parent)))
			res.append("var result = __wrapped__.apply(__this__, arguments);")
			res.append(self.onFunctionPost(function))
			res.append("return result;")
		return self._format(res)

	def onClosure( self, closure ):
		"""Writes a closure element."""
		arguments = ", ".join(map(self.write, closure.getArguments()))
		if arguments: arguments += ","
		arguments += " ... arguments"
		return self._format(
			self._document(closure),
			"function(%s){" % ( arguments ),
			self._writeClosureArguments(closure),
			map(self.write, closure.getOperations()),
			"}"
		)

	def onArgument( self, argument ):
		"""Writes an argument element."""
		prefix  = ""
		# ActionScript supports "..." for extra arguments
		if argument.isRest():
			prefix = "... "
		value   = argument.getDefaultValue()
		# NOTE: We can only write the argument as default when it is a litteral,
		# otherwise we have assign the value in the function body
		arg_type = argument.getTypeDescription()
		# FIXME: We need to do proper type translation here. The strategy for
		# now is simply to bypass type expressions '<...>' and include named
		# type references "as-is"
		if arg_type:
			if arg_type[0] == "<":
				arg_type = ""
			else:
				arg_type = ":" + arg_type
		else: arg_type = ""
		if value:
			return "%s%s%s=%s" % (
				prefix,
				argument.getName(),
				arg_type,
				isinstance(value, interfaces.ILiteral) and self.write(value) or "undefined"
			)
		else:
			return prefix + argument.getName() + arg_type

	def _writeClosureArguments(self, closure):
		i = 0
		l = len(closure.getArguments())
		result = []
		for argument in closure.getArguments():
			arg_name = argument.getName()
			arg_value = argument.getDefaultValue()
			# ActionScript supports varargs (variable parameters) using the
			# '... extra' syntax, so we don't have to slice the arguments like
			# we have to do in JS.
			if argument.isRest():
				pass
			# Here we only add the code for the attributes initialization if it
			# is not a litteral, in which case a default value was already
			# assigned
			if not (arg_value is None) and not isinstance(arg_value, interfaces.ILiteral):
				result.append("%s = %s === undefined ? %s : %s" % (
					arg_name,
					arg_name,
					self.write(arg_value),
					arg_name
				))
			i += 1
		return result

	def onModuleAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value: default_value = self.write(default_value)
		else: default_value = 'undefined'
		return self._format(
			self._document(element),
			"public var %s=%s" % (element.getName(), default_value)
		)
		
	def onReference( self, element ):
		"""Writes an argument element."""
		symbol_name  = element.getReferenceName()
		# FIXME: Does resolve really always return a dataflow slot ?
		slot, value = self.resolve(symbol_name)
		if slot:
			value = slot.getValue()
			scope = slot.getDataFlow().getElement()
		else:
			value = None
			scope = None
		if symbol_name == "super":
			assert self.resolve("self"), "Super must be used inside method"
			return "super"
		if scope and isinstance(scope, interfaces.IModule):
			if not isinstance(value, interfaces.IClass):
				names = [scope.getName(), symbol_name]
				while scope.getParent():
					scope = scope.getParent()
					if not isinstance(scope, interfaces.IProgram):
						names.insert(0, scope.getName())
						return ".".join(names)
		if self.getCurrentClass() == scope:
			# FIXME: This seems broken as resolve returns a dataflowslot
			if isinstance(value, interfaces.IInstanceMethod):
				# Here we need to wrap the method if they are given as values (
				# that means used outside of direct invocations), because when
				# giving a method as a callback, the 'this' pointer is not carried.
				if self.inInvocation:
					return "__this__.%s" % (symbol_name)
				else:
					return "__this__.getMethod('%s') " % (symbol_name)
			elif isinstance(value, interfaces.IClassMethod):
				if self.isIn(interfaces.IInstanceMethod):
					return "%s.%s" % (self.getCurrentClass().getName(), symbol_name)
				else:
					return "__this__.%s" % (symbol_name)
			elif isinstance(value, interfaces.IClassAttribute):
				if self.isIn(interfaces.IClassMethod):
					return "__this__.%s" % (symbol_name)
				else:
					return "%s.%s" % (self.getCurrentClass().getName(), symbol_name)
			else:
				# It's a probably a None value (it's not resolved :/)
				return symbol_name
		return javascript.Writer.onReference(self, element)

	def onImportSymbolOperation( self, element ):
		res = ["import"]
		res.append(element.getImportedElement())
		symbol_origin = element.getImportOrigin()
		symbol_alias = element.getAlias()
		if symbol_origin:
			vres = ["from", symbol_origin]
			vres.extend(res)
			res = vres
		if symbol_alias:
			res.extend(["as", symbol_alias])
		return " ".join(res)

	def onImportSymbolsOperation( self, element ):
		res           = []
		symbol_origin = element.getImportOrigin()
		imported      = element.getImportedElements()
		for i in imported:
			assert symbol_origin
			if i == "*":
				res.append("import %s.*" % (symbol_origin))
			else:
				res.append("import %s.%s" % (symbol_origin, i))
		return ";".join(res)

	def onImportModuleOperation( self, element ):
		res = ["import"]
		res.append(element.getImportedModuleName())
		symbol_alias = element.getAlias()
		if symbol_alias:
			res.extend(["as", symbol_alias])
		return " ".join(res)

	def onImportModulesOperation( self, element ):
		res = []
		for m in element.getImportedModuleNames():
			res.append("import %s" % (m))
		return ";".join(res)

	def _document( self, element ):
		if element.getDocumentation():
			doc = element.getDocumentation()
			annotations = []
			res = []
			for line in doc.getContent().split("\n"):
				l = line.strip()
				if l and l[0] == "[" and l[-1] == "]":
					annotations.append(l)
				else:
					res.append(line)
			annotations = "\n".join(annotations)
			res         = "\n".join(res)
			if annotations and not res:
				return annotations
			if res and not annotations:
				return "/** %s\n*/" % (res)
			else:
				return "/** %s\n*/\n%s" % (res, annotations)
		else:
			return None

MAIN_CLASS = Writer
# EOF
