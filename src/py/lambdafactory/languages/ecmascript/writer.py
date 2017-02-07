# encoding: utf8
# -----------------------------------------------------------------------------
# Project   : LambdaFactory
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                            <sebastien@ffctn.com>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 2017-01-16
# Last mod  : 2017-01-31
# -----------------------------------------------------------------------------

import lambdafactory.interfaces as interfaces
import lambdafactory.reporter   as reporter
from   lambdafactory.languages.javascript.writer import Writer as JavaScriptWriter

# FIXME: It's kind of odd to have to do push/pop context

__doc__ = """
A specialization of the JavaScript writer to output runtime-free ECMAScript
code.
"""

RUNTIME_OPS = {
	"map":"__map__",
	"filter":"__filter__",
	"reduce":"__reduce__",
}

#------------------------------------------------------------------------------
#
#  WRITER
#
#------------------------------------------------------------------------------

class Writer(JavaScriptWriter):

	def __init__( self ):
		JavaScriptWriter.__init__(self)
		self.jsInit = "__init__"

	# -------------------------------------------------------------------------
	#
	# OPERATION
	#
	# -------------------------------------------------------------------------

	def onEnumeration( self, operation ):
		"""Writes an enumeration operation."""
		start = self.write(operation.getStart())
		end   = self.write(operation.getEnd())
		step  = operation.getStep()
		step  = self.write(step) if step else 1
		# NOTE: This is a safe, runtime-free enumeration
		return "__range__({0},{1},{2})".format(start,end,step)

	# -------------------------------------------------------------------------
	#
	# CONSTRUCTS
	#
	# -------------------------------------------------------------------------

	def onClass( self, element, anonymous=False ):
		"""Writes a class element."""
		self.pushContext (element)
		name = "" if anonymous else ((element.getName() or "") + " ")
		parent = self._onClassParents(element, self.getClassParents(element))
		yield "class " + name + ("extends " + parent if parent else "") + " {"
		yield self._onClassBody(element)
		yield "}"
		self.popContext ()

	def onType( self, element, anonymous=False ):
		assert element.isConcrete()
		self.pushContext (element)
		name   = "" if anonymous else ((element.getName() or "") + " ")
		parent = self._onClassParents(element, element.getParents())
		slots  = [_ for _ in element.constraints if isinstance(_, interfaces.ISlotConstraint)]
		yield "class " + name + ("extends " + parent if parent else "") + " {"
		yield "\tconstructor({0}){{".format(", ".join(_.getName() for _ in slots))
		if parent:
			yield "\t\tsuper();"
		for s in slots:
			yield "\t\tif (typeof {0} != \"undefined\") {{this.{0} = {0};}}".format(s.getName())
		yield "\t}"
		yield "}"
		self.popContext ()

	def onTrait( self, element ):
		self.pushContext (element)
		yield "function(_) { return class extends " + self._onClassParents(element, self.getClassParents(element), base="_") + " {"
		yield self._onClassBody(element, withConstructors=False)
		yield "};}"
		self.popContext()

	def onSingleton( self, element ):
		self.pushContext (element)
		yield "function() {"
		yield "\tvar self = new " + self._onClassParents(element, self.getClassParents(element), base="Object") + "();"
		for e in element.getAttributes():
			yield "\tself." + e.getName() + " = " + self.write(e.getDefaultValue()) + ";"
		for e in element.getConstructors():
			self.pushContext(e)
			yield [self._onFunctionBody(e)]
			self.popContext()
		for e in element.getInstanceMethods():
			self.pushContext(e)
			l = [_ for _ in self.onFunction(e, modifier="function")]
			l[0]   = "self." + e.getName() + " = " + l[0]
			l[-1] += ";"
			yield [l]
			self.popContext()
		yield "\treturn self;"
		yield "}();"
		self.popContext()

	def _onClassParents( self, element, parents, base="" ):
		"""Returns the parents of a class, taking into account the
		pre-processing by traits."""
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
			parent = self.getAbsoluteName(t) + "(" + (parent or "Object") + ")"
		return parent

	def _onClassBody( self, element, withConstructors=True ):
		"""Iterates through the slots in a context, writing their name and value"""
		slots = element.getSlots()
		for e in element.getConstructors() or ([None] if withConstructors else ()):
			self.pushContext(e)
			yield self.onConstructor(e)
			self.popContext()
		for e in element.getInstanceMethods():
			self.pushContext(e)
			yield self.onMethod(e)
			self.popContext()

	# -------------------------------------------------------------------------
	#
	# CALLABLES
	#
	# -------------------------------------------------------------------------

	def onFunction( self, element, anonymous=False, modifier="function", name=None, body=None, bindSelf=True ):
		name   = name or element.getName() if element else None
		params = self._onParametersList(element) if element else ""
		yield (modifier + " " if modifier else "") + (name if name and not anonymous else "") + "(" + params + ") {"
		yield self._onFunctionBody(element, body, bindSelf=bindSelf)
		yield "}"

	def onMethod( self, element ):
		return self.onFunction( element, modifier="" )

	def onClassMethod( self, element ):
		return self.onFunction( element, modifier="static" )

	def onConstructor( self, element ):
		if not element: return None
		r = []
		has_constructor = False
		for op in element.operations:
			if self.isSuperInvocation(op):
				has_constructor = op
				break
		c = self.getCurrentClass()
		if c:
			for a in c.getAttributes():
				n = a.getName()
				v = a.getDefaultValue()
				if v:
					r.append(
						"if (typeof {0}.{1} === typeof undefined) {{{0}.{1} = {2};}}".format(
						"this", a.getName(), self.write(v))
					)
		if not has_constructor:
			r.insert(0,"super();")
		return self.onFunction( element, modifier="constructor", anonymous=True, body=r, bindSelf=False)

	def onInitializer( self, element ):
		return self.onFunction( element,  anonymous=True )

	# =========================================================================
	# CALLBABLE-SPECIFIC RULES
	# =========================================================================

	def _onFunctionBody( self, element, body=None, bindSelf=True ):
		"""Writes the body of a function."""
		# Adds the `var self = this`
		if bindSelf: yield self._runtimeSelfBinding(element)
		for _ in self._writeImplicitAllocations(element):
			yield _
		if element:
			for _ in self._onParametersInit(element): yield _
			for _ in self._onPreCondition(element): yield _
		for _ in body or []:
			yield _
		if element:
			for _ in element.getOperations():
				yield self.write(_)
			for _ in self._onPostCondition(element):
				yield _

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
	# USEFUL PREDICATES
	# =========================================================================

	def isSuperInvocation( self, element ):
		return element and isinstance(element, interfaces.IInvocation) and element.getTarget().getReferenceName() == "super"

	# =========================================================================
	# UTILITIES
	# =========================================================================

	def _runtimeOp( self, name, lvalue, rvalue ):
		return "{0}({1},{2})".format(
			RUNTIME_OPS.get(name) or name,
			self.write(lvalue), self.write(rvalue)
		)

	def _runtimeReturnBreak( self ):
		return "return __BREAK__;"

	def _runtimeReturnContinue( self ):
		return "return __CONTINUE__;"

	def _runtimeRestArguments( self, i ):
		return "Array.prototype.slice.call(arguments," + str(i) + ")"

	def _runtimeDefaultValue( self, name, value ):
		return name + " === undefined ? " + value + " : " + name

	def _runtimeSelfReference( self, element ):
		if self.isIn(interfaces.IConstructor):
			# We cannot pre-bind the `self` in constructors before  the
			# super() is called
			return "this"
		else:
			return "self"

	def _runtimeSelfBinding( self, element ):
		c = self.getCurrentContext()
		t = "this"
		if isinstance(c, interfaces.IModule):
			t = "__module__"
		elif isinstance(c, interfaces.ISingleton):
			return None
		return "let {0} = {1};".format(self.jsSelf, t)

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

	def _runtimePreamble( self ):
		return []

	def _runtimeAccess( self, target, index ):
		return "({0} instanceof Array || typeof {0} === \"string\" ?  {0}.slice({1}) : undefined)".format(target, index)

	def _runtimeSlice( self, target, start, end ):
		return "({0} instanceof Array || typeof {0} === \"string\" ?  {0}.slice({1},{2}) : undefined)".format(target, start, end)

MAIN_CLASS = Writer

# EOF - vim: tw=80 ts=4 sw=4 noet
