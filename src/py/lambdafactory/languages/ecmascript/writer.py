# encoding: utf8
# -----------------------------------------------------------------------------
# Project   : LambdaFactory
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ffctn.com>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 2017-01-16
# Last mod  : 2017-11-16
# -----------------------------------------------------------------------------

import lambdafactory.interfaces as interfaces
import lambdafactory.reporter   as reporter
from   lambdafactory.languages.javascript.writer import Writer as JavaScriptWriter

# FIXME: It's kind of odd to have to do push/pop context

#------------------------------------------------------------------------------
#
#  WRITER
#
#------------------------------------------------------------------------------

class Writer(JavaScriptWriter):

	# -------------------------------------------------------------------------
	#
	# CONSTRUCTS
	#
	# -------------------------------------------------------------------------

	def onSingleton( self, element ):
		self.pushContext (element)
		yield "function() {"
		yield "\tvar self = new " + self._onClassParents(element) + "();"
		for e in element.getAttributes():
			yield "\tself." + e.getName() + " = " + self.write(e.getDefaultValue()) + ";"
		for e in element.getConstructors():
			yield [self._onFunctionBody(e)]
		for e in element.getInstanceMethods():
			l = [_ for _ in self.onFunction(e, modifier="function")]
			l[0]   = "self." + e.getName() + " = " + l[0]
			l[-1] += ";"
			yield [l]
		yield "\treturn self;"
		yield "}();"
		self.popContext()

	def onTrait( self, element ):
		self.pushContext (element)
		yield "function(Base) { return class extends " + self._onClassParents(element, "Base") + " {"
		yield [self._onClassBody(element)]
		yield "}}"
		self.popContext()

	def onClass( self, element ):
		"""Writes a class element."""
		self.pushContext (element)
		yield "class extends " + self._onClassParents(element) + " {"
		yield self._onClassBody(element)
		yield "}"
		self.popContext ()

	def _onClassParents( self, element, base="Object" ):
		parents = self.getClassParents(element)
		traits  = [_ for _ in parents if isinstance(_, interfaces.ITrait)]
		parents = [_ for _ in parents if _ not in traits]
		parent  = ""
		if len(parents) == 0:
			parent = base
		elif len(parents) == 1:
			parent = self.getAbsoluteName(parents[0])
		else:
			parent = self.getAbsoluteName(parents[0])
			reporter.warning(
				"Class has multiple class parents, ignoring the rest: {0}"
				.format(self.getAbsoluteName(element)))
		for t in traits:
			parent = self.getAbsoluteName(t) + "(" + parent + ")"
		return parent

	def _onClassBody( self, element ):
		"""Iterates through the slots in a context, writing their name and value"""
		slots = element.getSlots()
		for e in element.getConstructors() or [None]:
			yield self.onConstructor(e)
		for e in element.getInstanceMethods():
			yield self.onMethod(e)

	# -------------------------------------------------------------------------
	#
	# CALLABLES
	#
	# -------------------------------------------------------------------------

	def onFunction( self, element, anonymous=False, modifier="function", name=None, body=None ):
		name   = name or element.getName() if element else None
		params = self._onParametersList(element) if element else ""
		yield modifier + (" " + name if name and not anonymous else "") + "(" + params + ") {"
		yield self._onFunctionBody(element, body)
		yield "}"

	def onMethod( self, element ):
		return self.onFunction( element, modifier="" )

	def onClassMethod( self, element ):
		return self.onFunction( element, modifier="static" )

	def onConstructor( self, element ):
		r = []
		if not element:
			r.append("super();")
		c = self.getCurrentClass()
		if c:
			for a in c.getAttributes():
				n = a.getName()
				r.append(
					"if (typeof {0}.{1} === typeof undefined) {{{0}.{1} = {2};}}".format(
					self.jsSelf, a.getName(), self.write(a.getDefaultValue()))
				)
		return self.onFunction( element, modifier="constructor", anonymous=True, body=r)

	def onInitializer( self, element ):
		return self.onFunction( element,  anonymous=True )

	# =========================================================================
	# CALLBABLE-SPECIFIC RULES
	# =========================================================================

	def _onFunctionBody( self, element, body=None ):
		"""WRites the body of a function."""
		yield self._runtimeSelf(element)
		if element:
			for _ in self._onParametersInit(element): yield _
			for _ in self._onPreCondition(element): yield _
		for _ in body or []:
			yield _
		for _ in element.getOperations():
			yield self.write(_)
		if element:
			for _ in self._onPostCondition(element): yield _

	def _onParametersList( self, element ):
		params = element.getParameters()
		return ", ".join(self.write(_) for _ in params)

	def _onParametersInit( self, element ):
		params = element.getParameters()
		l      = len(params)
		for i,p in enumerate(params):
			n = self.write(p)
			v = p.getDefaultValue()
			if p.isRest():
				assert i >= l - 2
				yield n + " = " + self._runtimeRestArguments(i) + ";"
			if v is not None:
				yield n + " = " + self._runtimeDefaultValue(n, self.write(v)) + ";"

	def _onPreCondition( self, element ):
		"""Writes pre-conditions"""
		for a in element.getAnnotations(withName="when"):
			yield "if (!(%s)) {return undefined;}" % (self.write(a.getContent()))

	# NOTE: This is not really supported in the syntax anymore
	def _onPostCondition( self, element ):
		"""Writes post-conditions"""
		scope = self.getAbsoluteName(element)
		for a in element.getAnnotations(withName="post"):
			predicate = self.write(a.getContent())
			yield ("if (!({0})) {{throw new Exception('{1}: Post condition failed"
			"{0}';}}".format(predicate, scope))

	# =========================================================================
	# UTILITIES
	# =========================================================================

	def _runtimeRestArguments( self, i ):
		return "Array.prototype.slice.call(arguments," + str(i) + ")"

	def _runtimeDefaultValue( self, name, value ):
		return name + " === undefined ? " + value + " : " + name

	def _runtimeSelf( self, element ):
		c = self.getCurrentContext()
		t = "this"
		if isinstance(c, interfaces.IModule):
			t = "__module__"
		elif isinstance(c, interfaces.ISingleton):
			return None
		return "var {0} = {1};".format(self.jsSelf, t)

	def _runtimeSuper( self, element ):
		if self.isIn(interfaces.IClassAttribute) or self.isIn(interfaces.IClassMethod):
			c = self.getCurrentClass()
			p = self.getClassParents(c)
			if p:
				return self.getAbsoluteName(p[0])
			else:
				return self.getAbsoluteName(self.getCurrentContext())
		else:
			return "super"

	def _runtimeGetClass(self, variable=None):
		return (variable or self.jsSelf) + ".prototype"

	def _runtimeGetMethodByName(self, name):
		m = self.jsSelf + ".__method__" + name
		n = self.jsSelf + "." + name
		return "(typeof {0} === typeof undefined ? {0} = function(){{return {1}.apply(self,arguments);}} : {0})".format(m, n)

MAIN_CLASS = Writer

# EOF - vim: tw=80 ts=4 sw=4 noet