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

# TODO: When constructor is empty, should assign default attributes anyway

import javascript
import interfaces

class Resolver(javascript.Resolver):
	pass

#------------------------------------------------------------------------------
#
#  JavaScript Writer
#
#------------------------------------------------------------------------------

class Writer(javascript.Writer):

	def writeModule( self, moduleElement):
		"""Writes a Module element."""
		files_code  = []
		module_path = self.getAbsoluteName(moduleElement).replace(".", "/")
		# Module version
		version = moduleElement.getAnnotation("version")
		if version:
			module_code.append('public static _VERSION_:String = "%s";' % (version.getContent()))
		# Now we write every slot
		for name, value in moduleElement.getSlots():
			if isinstance(value, interfaces.IClass):
				code = [
					"// " + self.SNIP % ("%s/%s.as" % (module_path, value.getName())),
					self._document(moduleElement),
					"package %s {" % (self.getAbsoluteName(moduleElement)),
					[self.write(value)],
					"}"
				]
				files_code.extend(code)
			else:
				pass
				#print "***", name, value
				#raise Exception("ActionScript does not support module function or attributes")
		return self._format(
			*files_code
		)

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
		code       = [
			self._document(classElement),
			"public class %s %s{" % (classElement.getName(), parent),
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

# EOF