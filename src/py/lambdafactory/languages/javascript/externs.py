# -----------------------------------------------------------------------------
# Project   : LambdaFactory
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                            <sebastien@ffctn.com>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 2016-12-02
# Last mod  : 2016-12-02
# -----------------------------------------------------------------------------

import lambdafactory.interfaces as interfaces

# __doc__ = """
# A backend that writes closure-compiler compatible extern files.
# """
#
KEYWORDS = ['abstract', 'break', 'case', 'class', 'let', 'continue', 'const', 'debugger',
'default', 'enum', 'export', 'extends', 'final', 'finally', 'for', 'function',
'goto', 'if', 'implements', 'import', 'in', 'interface', 'native', 'new',
'package', 'private', 'protected', 'public', 'return', 'short', 'static',
'super', 'switch', 'synchronized', 'throw', 'throws', 'transient', 'try',
'var', 'void', 'volatile', 'while', 'with']
#
# # More info about externs: <https://developers.google.com/closure/compiler/docs/api-tutorial3>
# # ES* externs: https://github.com/google/closure-compiler/tree/master/externs
# # 3rd party externs: https://github.com/google/closure-compiler/tree/master/contrib/externs
# # # Types:
# # https://github.com/google/closure-compiler/wiki/Types-in-the-Closure-Type-System
# #
# # Annotating:
# # https://github.com/google/closure-compiler/wiki/Annotating-JavaScript-for-the-Closure-Compiler
# #
# # General wiki:
# # https://github.com/google/closure-compiler/wiki
#
# LINE = ('',)
#
TYPE_ANY = "Object|Array|Function|string|boolean|number|null|undefined"

class ExternsWriter(object):

	def onProgram( self, element ):
		res = [self._docstring(
			"@fileoverview Externs for {0}".format(element),
			"@externs"
		)]
		for _ in element.getModules():
			if _.isImported(): continue
			res += LINE
			res += list(self.write(_))
		return self._format(res)

	def onModule( self, element ):
		"""Writes a Module element."""
		name = self.getName(element)
		yield "/* Module {0} */".format(name)
		yield self._docstring("@const")
		yield "goog.module('{0}');".format(name),
		for _ in self.getImportedModules(element):
			if _ != name:
				yield "var {0} = goog.require('{0}');".format(_)
		for alias, module, slot in self.getImportedSymbols(element):
			if module == name:
				continue
			elif not slot:
				# Modules are already imported
				if alias:
					yield ("var {0} = {1};".format(alias or module, module))
			else:
				# Extend gets a special treatment
				if module != "extend" or alias:
					yield ("var {0} = {1}.{2};".format(alias or slot, module, slot))
		# yield "var {0} = {{}};".format(name)
		for name,value in element.getSlots():
			yield LINE
			for _ in self.write(value):
				yield _

	def onModuleAttribute( self, element ):
		return [
			self._docstring("@type {0}".format(TYPE_ANY)),
			"{0};".format(self.getAbsoluteName(element))
		]

	def onClass( self, element ):
		name         = self.getAbsoluteName(element)
		yield self._section("Class " + name)
		constructors = element.getConstructors()
		# TODO: Should resolve the constructor in the parent if not found
		if constructors:
			for _ in constructors:
				yield self._docfunction(_, "@constructor")
		else:
			yield LINE
			yield self._docstring("@constructor")
			yield "{0} = function(){{}};".format(name)
		for _ in element.getClassAttributes():
			yield self._docvalue(_, inInstance=False)
		for _ in element.getClassMethods():
			yield self._docvalue(_, inInstance=False)
		for _ in element.getAttributes():
			yield self._docvalue(_, inInstance=True)
		for _ in element.getInstanceMethods():
			yield self._docfunction(_, inInstance=True)

	def onFunction( self, element ):
		yield self._docfunction(element, inInstance=False)

	# =========================================================================
	# HELPER
	# =========================================================================

	def _docvalue( self, element, prefix=None, inInstance=False ):
		name   = self.getAbsoluteName(element)
		header = [prefix] if prefix else [] + self.getDocumentation(element)
		header.append("@type {{{0}}}".format(TYPE_ANY))
		header = self._docstring(*header)
		if inInstance:
			name = name.split(".")
			name.insert(-1, "prototype")
			name = ".".join(name)
		return "\n" + header + "\n{0};".format(name)

	def _docfunction( self, element, prefix=None, inInstance=False, declaration=True ):
		name   = self.getAbsoluteName(element)
		params = self._extractParameters(element)
		header = [prefix] if prefix else [] + self.getDocumentation(element)
		for p in params:
			header.append("@param {{{0}{2}}} {1}".format(p["type"], p["name"], "=" if p["optional"] else ""))
		header = self._docstring(*header)
		if inInstance:
			name = name.split(".")
			name.insert(-1, "prototype")
			name = ".".join(name)
		if not declaration:
			return header + "\n"
		else:
			return "\n" + header + "\n{0} = function({1}){{}};".format(name, ", ".join(_["name"] for _ in params))

	def _extractParameters( self, element ):
		params = []
		for param in element.getParameters():
			params.append(dict(
				name     = self.getName(param),
				type     = TYPE_ANY,
				optional = param.getDefaultValue()
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

	def getDocumentation( self, element ):
		"""Returns a list of strings corresonding to each line of documentation
		in the original element."""
		doc = element.getDocumentation()
		if doc:
			return doc.getContent().split("\n") + [""]
		else:
			return ["Missing documentation for element `{0}`".format(self.getName(element)), ""]

	def getName( self, element ):
		name = element.getName()
		return "_" + name if name in KEYWORDS else name

	def getAbsoluteName( self, element ):
		"""Returns the absolute name for the given element. This is the '.'
		concatenation of the individual names of the parents."""
		names = [] if isinstance(element, interfaces.IConstructor) else [self.getName(element)]
		while element.getParent():
			element = element.getParent()
			# FIXME: Some elements may not have a name
			if not isinstance(element, interfaces.IProgram):
				names.insert(0, self.getName(element))
		return ".".join(names)
#
# MAIN_CLASS = Writer
#
#
