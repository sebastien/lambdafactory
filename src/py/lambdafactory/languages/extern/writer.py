# -----------------------------------------------------------------------------
# Project   : LambdaFactory
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                            <sebastien@ffctn.com>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 2016-12-02
# Last mod  : 2016-12-02
# -----------------------------------------------------------------------------

from   lambdafactory.modelwriter import AbstractWriter, flatten
import lambdafactory.interfaces as interfaces
import lambdafactory.reporter   as reporter

__doc__ = """
A backend that writes closure-compiler compatible extern files.
"""


# More info about externs: https://developers.google.com/closure/compiler/docs/api-tutorial3
# ES* externs: https://github.com/google/closure-compiler/tree/master/externs
# 3rd party externs: https://github.com/google/closure-compiler/tree/master/contrib/externs
# # Types:
# https://github.com/google/closure-compiler/wiki/Types-in-the-Closure-Type-System
#
# Annotating:
# https://github.com/google/closure-compiler/wiki/Annotating-JavaScript-for-the-Closure-Compiler
#
# General wiki:
# https://github.com/google/closure-compiler/wiki

LINE = ('',)

class Writer(AbstractWriter):

	def __init__( self ):
		AbstractWriter.__init__(self)

	def onProgram( self, element ):
		res = [self._docstring(
			"@fileoverview Externs for {0}".format(element),
			"@externs"
		)]
		for _ in element.getModules():
			res += LINE
			res += list(self.write(_))
		return self._format(res)

	def onModule( self, element ):
		"""Writes a Module element."""
		name = element.getName()
		yield "/* Module {0} */".format(name)
		yield self._docstring("@const")
		yield "var {0} = {{}};".format(name)
		for name,value in element.getSlots():
			yield LINE
			for _ in self.write(value):
				yield _

	def onModuleAttribute( self, element ):
		return [
			self._docstring("@typedef Object"),
			"{0};".format(self.getAbsoluteName(element))
		]

	def onClass( self, element ):
		name         = self.getAbsoluteName(element)
		yield self._section("Class " + name)
		for _ in element.getConstructors():
			yield self._docfunction(_, "@constructor")
		for _ in element.getClassAttributes():
			yield self._docvalue(_, inInstance=False)
		for _ in element.getClassMethods():
			yield self._docvalue(_, inInstance=False)
		for _ in element.getAttributes():
			yield self._docvalue(_, inInstance=True)
		for _ in element.getInstanceMethods():
			yield self._docfunction(_, inInstance=True)


	def onFunction( self, element ):
		name   = self.getAbsoluteName(element)
		params = self._extractParameters(element)
		header = self._docstring(
			["@param {type} {name}".format(**_) for _ in params] + ["@return {Object}"]
		)
		return [
			header,
			"{0} = function({1});".format(name, ", ".join(_["name"] for _ in params))
		]

	# =========================================================================
	# HELPER
	# =========================================================================

	def _docvalue( self, element, prefix=None, inInstance=False ):
		name   = self.getAbsoluteName(element)
		header = [prefix] if prefix else []
		header.append("@type {Object}")
		header = self._docstring(*header)
		if inInstance:
			name = name.split(".")
			name.insert(-1, "prototype")
			name = ".".join(name)
		return "\n" + header + "\n{0};".format(name)

	def _docfunction( self, element, prefix=None, inInstance=False ):
		name   = self.getAbsoluteName(element)
		params = self._extractParameters(element)
		header = [prefix] if prefix else []
		for p in params:
			header.append("@param {{{0}}} {1}".format(p["type"], p["name"]))
		header = self._docstring(*header)
		if inInstance:
			name = name.split(".")
			name.insert(-1, "prototype")
			name = ".".join(name)
		return "\n" + header + "\n{0} = function({1});".format(name, ", ".join(_["name"] for _ in params))

	def _extractParameters( self, element ):
		params = []
		for param in element.getParameters():
			params.append(dict(
				name = param.getName(),
				type = "Object"
			))
		return params

	def _docstring( self, *lines ):
		if len(lines) == 1 and (isinstance(lines[0],tuple) or isinstance(lines[0],list)):
			return self._docstring(*lines[0])
		else:
			return "\n".join(["/**"] + [" * " + _ for _ in lines] + ["*/"])

	def _section( self, text ):
		return "\n".join((
			"// " + "-" * 76,
			"// ",
			"// " + text,
			"//",
			"// " + "-" * 76,
		))

	def getAbsoluteName( self, element ):
		"""Returns the absolute name for the given element. This is the '.'
		concatenation of the individual names of the parents."""
		names = [] if isinstance(element, interfaces.IConstructor) else [element.getName()]
		while element.getParent():
			element = element.getParent()
			# FIXME: Some elements may not have a name
			if not isinstance(element, interfaces.IProgram):
				names.insert(0, element.getName())
		return ".".join(names)

MAIN_CLASS = Writer

# EOF - vim: tw=80 ts=4 sw=4 noet
