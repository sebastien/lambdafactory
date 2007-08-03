#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 01-Aug-2007
# Last mod  : 01-Aug-2007
# -----------------------------------------------------------------------------

# SEE: http://livedocs.adobe.com/specs/actionscript/3/
# TODO: When constructor is empty, should assign default attributes anyway

import javascript
import interfaces
import reporter

class Resolver(javascript.Resolver):
	pass

#------------------------------------------------------------------------------
#
#  JavaScript Writer
#
#------------------------------------------------------------------------------

class Writer(javascript.Writer):

	def __init__(self, reporter=reporter.DefaultReporter ):
		javascript.Writer.__init__(self,reporter=reporter)
		self.jsCore   = "Extend.__module__."

	def writeModule( self, moduleElement):
		"""Writes a Module element."""
		files_code  = []
		module_path = self.getAbsoluteName(moduleElement).replace(".", "/")
		# Now we write every slot
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
			elif isinstance(op, interfaces.IImportOperation):
				imports.append(op)
			else:
				raise Exception("ActionScript does not allow code in module: %s" % (op))
		for name, value in classes:
			f = None
			#if functions:
			#	f = map(lambda n,f: self.write(f), functions)
			#	functions = None
			code = [
				"// " + self.SNIP % ("%s/%s.as" % (module_path, value.getName())),
				self._document(moduleElement),
				"package %s {" % (self.getAbsoluteName(moduleElement)),
				"import %s" % ( self.jsCore[:-1]),
				map(self.write, imports),
				f,
				self.write(value),
				"}"
			]
			files_code.extend(code)
		# If we have functions or attribute
		# This is a trick that will create a class name "__module__" in which
		# there will be module-level attributes and functions
		if module_functions or module_attributes:
			f = [] ; a = []
			if module_functions:
				for n, v in module_functions:
					f.append(self.write(v))
			if module_attributes:
				for n, v in module_attributes:
					a.append(self.write(v))
			module_code = ["public class __module__ {"]
			module_code.extend(map(self.write, imports))
			module_code.extend(a)
			module_code.extend(f)
			module_code.append("}")
			code = [
				"// " + self.SNIP % ("%s/__module__.as" % (module_path)),
				self._document(moduleElement),
				"package %s {" % (self.getAbsoluteName(moduleElement)),
				module_code,
				"}"
			]
			files_code.extend(code)
		return self._format(
			*files_code
		)

	def writeImportOperation( self, importElement):
		imported_name = self.write(importElement.getImportedElement())
		imported_elem = imported_name.split(".")[-1]
		if importElement.getAlias():
			return "import %s=%s" % (importElement.getAlias().getReferenceName(), imported_name)
		else:
			return "import %s" % (imported_name)

	def writeClass( self, classElement ):
		"""Writes a class element."""
		parents = classElement.getSuperClasses()
		parent  = ""
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
			"public class %s %s{" % (classElement.getName(), parent),
			version,
			class_code,
			"}"
		]
		# We collect class attributes
		class_code.extend(map(self.write, classElement.getAttributes()))
		class_code.extend(map(self.write, classElement.getConstructors()))
		# FIXME: What about destructors
		class_code.extend(map(self.write, classElement.getClassMethods()))
		class_code.extend(map(self.write, classElement.getInstanceMethods()))
		return self._format(code)

	def writeAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			return self._format(
				self._document(element),
				"public var %s = %s" % (element.getReferenceName(), self.write(default_value))
			)
		else:
			return self._format(
				self._document(element),
				"public var %s" % (element.getReferenceName())
			)

	def writeClassAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value:
			res = "public static var %s = %s" % (element.getReferenceName(), self.write(default_value))
		else:
			res = "public static var %s" % (element.getReferenceName())
		return self._format(self._document(element), res)
	
	def writeConstructor( self, element ):
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

	def writeMethod( self, methodElement ):
		"""Writes a method element."""
		method_name = methodElement.getName()
		class_name  = self.getCurrentClass().getName()
		if method_name == interfaces.Constants.Constructor: method_name = class_name
		if method_name == interfaces.Constants.Destructor:  method_name = "destroy"
		return self._format(
			self._document(methodElement),
			"public function %s(%s){" % (
				method_name,
				", ".join(map(self.write, methodElement.getArguments()))
			),
			["var __this__=this"],
			self._writeClosureArguments(methodElement),
			self.writeFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def writeClassMethod( self, methodElement ):
		"""Writes a class method element."""
		method_name = methodElement.getName()
		args        = methodElement.getArguments()
		return self._format(
			self._document(methodElement),
			"public static function %s(%s){" % (method_name, ", ".join(map(self.write, args))),
			["var __this__ = this;"],
			self._writeClosureArguments(methodElement),
			self.writeFunctionWhen(methodElement),
			map(self.write, methodElement.getOperations()),
			"}"
		)

	def writeFunction( self, function ):
		"""Writes a function element."""
		parent = function.getParent()
		name   = function.getName() or ""
		prefix = isinstance(function.getParent(), interfaces.IModule) and "public static " or ""
		res = [
			self._document(function),
			"%sfunction %s (%s){" % (
				prefix,
				name,
				", ".join(map(self.write, function.getArguments()))
			),
			self._writeClosureArguments(function),
			self.writeFunctionWhen(function),
			map(self.write, function.getOperations()),
			"}"
		]
		if function.annotations(withName="post"):
			res[0] = "var __wrapped__ = " + res[0] + ";"
			if parent and isinstance(parent, interfaces.IModule):
				res.insert(0, 'var __this__=%s;' % (self.getAbsoluteName(parent)))
			res.append("var result = __wrapped__.apply(__this__, arguments);")
			res.append(self.writeFunctionPost(function))
			res.append("return result;")
		return self._format(res)

	def writeArgument( self, argElement ):
		"""Writes an argument element."""
		return "%s=undefined" % (
			argElement.getReferenceName(),
		)


	def writeModuleAttribute( self, element ):
		"""Writes an argument element."""
		default_value = element.getDefaultValue()
		if default_value: default_value = self.write(default_value)
		else: default_value = 'undefined'
		return self._format(
			self._document(element),
			"public static %s=%s" % (element.getReferenceName(), default_value)
		)
		
	def writeReference( self, element ):
		"""Writes an argument element."""
		symbol_name  = element.getReferenceName()
		value, scope = self.resolve(symbol_name)
		if scope and isinstance(scope, interfaces.IModule):
			if not isinstance(value, interfaces.IClass):
				names = [scope.getName(), "__module__", symbol_name]
				while scope.getParent():
					scope = scope.getParent()
					if not isinstance(scope, interfaces.IProgram):
						names.insert(0, scope.getName())
						return ".".join(names)
		return javascript.Writer.writeReference(self, element)

# EOF