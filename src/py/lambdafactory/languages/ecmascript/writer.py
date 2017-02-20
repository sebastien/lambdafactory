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
import types

# FIXME: It's kind of odd to have to do push/pop context

__doc__ = """
A specialization of the JavaScript writer to output runtime-free ECMAScript
code.
"""

RUNTIME_OPS = {
	"isIn":"__in__",
	"map":"__map__",
	"filter":"__filter__",
	"reduce":"__reduce__",
	"iterate":"__iterate__"
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
		self.jsSelf = "self"

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
		safe_name = self.getSafeName(element)
		abs_name  = element.getAbsoluteName()
		name = "" if anonymous else ((element.getName() or "") + " ")
		parent = self._onClassParents(element, self.getClassParents(element))
		yield "class " + name + ("extends " + parent if parent else "") + " {"
		yield self._onClassBody(element)
		yield "}"
		yield "Object.defineProperty({0}, \"__name__\", {{value:\"{1}\",writable:false}});".format(safe_name, abs_name)
		for _ in element.getClassAttributes():
			yield "Object.defineProperty({0}, \"{1}\", {{value:{2},writable:true}});".format(
				safe_name,
				_.getName(),
				self.write(_.getDefaultValue()) or "undefined")
		self.popContext ()

	def onType( self, element, anonymous=False ):
		assert element.isConcrete()
		self.pushContext (element)
		safe_name = self.getSafeName(element)
		abs_name  = element.getAbsoluteName()
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
		yield "Object.defineProperty({0}, \"__name__\", {{value:\"{1}\",writable:false}});".format(safe_name, abs_name)
		self.popContext ()

	def onTrait( self, element ):
		self.pushContext (element)
		yield "function(_) {"
		yield "\tvar res = class extends " + self._onClassParents(element, self.getClassParents(element), base="_") + " {"
		yield [self._onClassBody(element, withConstructors=False)]
		yield "\t}"
		yield "\tObject.defineProperty({0}, \"__name__\", {{value:\"{1}\",writable:false}});".format("res", element.getAbsoluteName())
		yield "\treturn res;"
		yield "}"
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
		# TODO: Support getters & setters?
		for e in element.getInstanceMethods():
			self.pushContext(e)
			l = [_ for _ in self.onFunction(e, modifier="function")]
			l[0]   = "self." + e.getName() + " = " + l[0]
			l[-1] += ";"
			yield [l]
			self.popContext()
		yield "\tself.__name__ = \"{0}\"".format(self.getAbsoluteName(element))
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
			self.pushContext(e or interfaces.IConstructor)
			yield self.onConstructor(e)
			self.popContext()
		for e in element.getClassMethods():
			self.pushContext(e)
			yield self.onClassMethod(e)
			self.popContext()
		for e in element.getAccessors():
			self.pushContext(e)
			yield self.onAccesor(e)
			self.popContext()
		for e in element.getMutators():
			self.pushContext(e)
			yield self.onMutator(e)
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

	def onFunction( self, element, anonymous=False, modifier="function", name=None, body=None, bindSelf=True, operations=None ):
		name   = name or element.getName() if element else None
		params = self._onParametersList(element) if element else ""
		yield (modifier + " " if modifier else "") + (name if name and not anonymous else "") + "(" + params + ") {"
		yield self._onFunctionBody(element, body, bindSelf=bindSelf, operations=operations)
		yield "}"

	def onAccesor( self, element ):
		return self.onFunction( element, modifier="get" )

	def onMutator( self, element ):
		return self.onFunction( element, modifier="set" )

	def onMethod( self, element ):
		return self.onFunction( element, modifier="" )

	def onClassMethod( self, element ):
		return self.onFunction( element, modifier="static" )

	def onConstructor( self, element ):
		call_super = None
		init       = ["let self=this;"]
		ops        = []
		if element:
			for op in element.operations:
				if self.isSuperInvocation(op):
					call_super = op
				else:
					ops.append(op)
		c = self.getCurrentClass()
		if c:
			traits = [_ for _ in self.getClassParents(c) if isinstance(_, interfaces.ITrait)]
			attrs  = []
			# We merge in attributes from the current class and then the traits
			# if they do not override
			for p in [c] + traits:
				for a in p.getAttributes():
					n = a.getName()
					if n not in attrs:
						attrs.append(n)
						v = a.getDefaultValue()
						if v:
							init.append(
								"if (typeof {0}.{1} === typeof undefined) {{{0}.{1} = {2};}}".format(
								"self", a.getName(), self.write(v))
							)
		# We only use super if the clas has parents and ther is no explicit
		# constructor
		if not call_super:
			if self.getClassParents(c):
				# We need to pass teh argumetns as-is
				init.insert(0,"super(...arguments);")
		else:
			self.jsSelf = "this"
			init.insert(0, self.write(call_super))
			self.jsSelf = "self"

		return self.onFunction( element, modifier="constructor", anonymous=True, body=init, bindSelf=False, operations=ops)

	def onInitializer( self, element ):
		return self.onFunction( element,  anonymous=True )

	# =========================================================================
	# CALLBABLE-SPECIFIC RULES
	# =========================================================================

	def _onFunctionBody( self, element, body=None, bindSelf=True, operations=None ):
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
			for _ in operations or element.getOperations():
				if isinstance(_, types.LambdaType):
					_()
				elif isinstance(_, interfaces.IElement):
					yield self.write(_)
				else:
					yield _
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
		if element and isinstance(element, interfaces.IInvocation):
			target = element.getTarget()
			return isinstance(target, interfaces.IReference) and target.getReferenceName() == "super"
		else:
			return False

	# =========================================================================
	# UTILITIES
	# =========================================================================

	def _runtimeOp( self, name, *args ):
		return "{0}({1})".format(
			RUNTIME_OPS.get(name) or name,
			", ".join(self.write(_) for _ in args)
		)

	def _runtimeReturnBreak( self ):
		return "return __BREAK__;"

	def _runtimeReturnContinue( self ):
		return "return __CONTINUE__;"

	def _runtimeReturnType( self ):
		return "__RETURN__"

	def _runtimeRestArguments( self, i ):
		return "Array.prototype.slice.call(arguments," + str(i) + ")"

	def _runtimeDefaultValue( self, name, value ):
		return name + " === undefined ? " + value + " : " + name

	def _runtimeIsIn( self, element, collection ):
		# NOTE: The is in is reversed in the ES runtime
		return self._runtimeOp("isIn", collection, element)

	def _runtimeSelfReference( self, element ):
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

	def _runtimeSuperResolution( self, resolution ):
		# We need to check wether we're in a closure or not. If we are,
		# then we can't user `super`
		closure = self.lastIndexInContext(interfaces.IClosure)
		method  = self.lastIndexInContext(interfaces.IMethod)
		name    = self._rewriteSymbol(resolution.getReference().getReferenceName())
		if method >= closure:
			return "super.{0}".format(name)
		else:
			s = self._runtimeSelfReference(resolution)
			invocation = self.findInContext(interfaces.IInvocation)
			if invocation and invocation.getTarget() == resolution:
				# This is awkward, but that's how you emulate a super invocation
				return "Object.getPrototypeOf(Object.getPrototypeOf({0})).{1}.bind({0})".format(s, name)
			else:
				m = s + ".__super_method__" + name
				n = "self.prototype." + name
				# NOTE: The commented line is a relatively bad way to do the
				# binding
				#return "(typeof {0} === typeof undefined ? {0} = function(){{return {1}.apply(self,arguments);}} : {0})".format(m, n)
				return n + ".bind(" + s + ")"

	def _runtimeGetCurrentClass(self, variable=None):
		return "Object.getPrototypeOf(" + (variable or self.jsSelf) + ").constructor"

	def _runtimeGetMethodByName(self, name, value=None, element=None):
		return self._runtimeSelfReference(element) + "." + name

	def _runtimeWrapMethodByName(self, name, value=None, element=None):
		s = self._runtimeSelfReference(element)
		if isinstance(value, interfaces.IClassMethod):
			return "Object.getPrototypeOf({0}).constructor.{1}.bind(Object.getPrototypeOf({0}).constructor)".format(s, name)
		else:
			return "{0}.{1}.bind({0})".format(s, name)

	def _runtimePreamble( self ):
		return []

	def _runtimeAccess( self, target, index ):
		return "__access__({0},{1})".format(target, index)

	def _runtimeSlice( self, target, start, end ):
		return "__slice__({0},{1},{2})".format(target, start, end)

	def _runtimeMapFromItems( self, items ):
		return "[{0}].reduce(function(r,v,k){{r[v[0]]=v[1];return r;}},{{}})".format(
			",".join("[{0},{1}]".format(self.write(k),self.write(v)) for k,v in items)
		)

MAIN_CLASS = Writer

# EOF - vim: tw=80 ts=4 sw=4 noet
