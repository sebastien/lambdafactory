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
import types, json

# FIXME: It's kind of odd to have to do push/pop context

__doc__ = """
A specialization of the JavaScript writer to output runtime-free ECMAScript
code.

There are a few specific workarounds the limitations of ECMAScript's objec
model:


1) Constructors do not directly initialize attributes/properties, but
   instead defer the initialization to the `__init_properties__` method
   defined in classes. This ensures that proerties initialization can
   be overriden by subclasses.
"""



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
		return "{0}__range__({1},{2},{3})".format(self.runtimePrefix, start,end,step)

	# -------------------------------------------------------------------------
	#
	# CONSTRUCTS
	#
	# -------------------------------------------------------------------------

	def onClass( self, element, anonymous=False, slotName=None ):
		"""Writes a class element."""
		self.pushContext (element)
		safe_name = slotName or self.getSafeName(element)
		abs_name  = element.getAbsoluteName()
		name = "" if anonymous else ((element.getName() or "") + " ")
		parents = self.getClassParents(element)
		parent = self._onClassParents(element, parents)
		yield "class " + name + ("extends " + parent if parent else "") + " {"
		yield self._onClassBody(element)
		yield "}"
		yield "Object.defineProperty({0}, \"__parents__\", {{writable:false,value:[{1}]}});".format(safe_name, ",".join(self.getSafeName(_) for _ in parents))
		yield "Object.defineProperty({0}, \"__name__\", {{value:\"{1}\",writable:false}});".format(safe_name, abs_name)
		# NOTE: Disabled for now, but might be useful for class method self reference
		# yield "const self={0};".format(safe_name)
		for _ in element.getClassAttributes():
			self.pushContext(_)
			yield "Object.defineProperty({0}, \"{1}\", {{value:{2},writable:true}});".format(
				safe_name,
				_.getName(),
				self.write(_.getDefaultValue()) or "undefined")
			self.popContext()
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
			yield "\t\tif (this.{0} === undefined) {{this.{0} = {0};}}".format(s.getName())

		yield "\t}"
		yield "}"
		yield "Object.defineProperty({0}, \"__name__\", {{value:\"{1}\",writable:false}});".format(safe_name, abs_name)
		self.popContext ()

	def onTrait( self, element ):
		self.pushContext (element)
		yield "function(_) {"
		yield "\tvar res = class extends " + self._onClassParents(element, self.getClassParents(element), base="_") + " {"
		# We need to pass arguments as-is
		yield ["\t\tconstructor(){super(...arguments);}"]
		yield [self._onClassBody(element, withConstructors=False, withAccessors=False, withProperties=False)]
		yield "\t}"
		# Now we take care of accessors. Somehow they don't seem to work
		# when declared in get/set and then mixed in.
		acc = {}
		for a in element.getAccessors():
			n = a.getName()
			if n not in acc: acc[n] = dict(get=None, set=None)
			acc[n]["get"] = self.onFunction(a, anonymous=True)
		for a in element.getMutators():
			n = a.getName()
			if n not in acc: acc[n] = dict(get=None, set=None)
			acc[n]["set"] = self.onFunction(a, anonymous=True)
		for k in acc:
			g = acc[k]["get"]
			s = acc[k]["set"]
			yield "\tObject.defineProperty(res.prototype, \"{0}\", {{".format(k,)
			if g:
				yield "\t\tget:"
				yield [[g]]
			if s:
				if g: yield "\t,"
				yield "\t\tset:"
				yield [[s]]
			yield "\t});"

		yield "\treturn res;"
		yield "};"
		yield "Object.defineProperty({0}, \"__name__\", {{value:\"{1}\",writable:false}});".format(self.getSafeName(element), element.getAbsoluteName())
		# Constructor
		yield "Object.defineProperty({0}, \"__init__\", {{writable:false,value:".format(self.getSafeName(element))
		# NOTE: Here we're moving the constructors to a static initialize
		# function, as there's some issues having a constructor super in traits when the
		# trait has no parent (ie. this is undefined).
		yield "\tfunction(self){"
		parents = self.getClassParents(element)
		for _ in self.getClassParents(element):
			if isinstance(_, interfaces.ITrait):
				yield "\t\t{0}.__init__(self);".format(self.getSafeName(_))
		for c in element.getConstructors():
			yield [[self._onFunctionBody(c, bindSelf=False)]]
		yield "\t}"

		yield "});"
		# Properties init
		safe_name = self.getSafeName(element)
		yield "Object.defineProperty({0}, \"__parents__\", {{writable:false,value:[{1}]}});".format(safe_name, ",".join(self.getSafeName(_) for _ in parents))
		yield "Object.defineProperty({0}, \"__init_properties__\", {{writable:false,value:".format(safe_name)
		yield "\tfunction(self) {"
		traits = [_ for _ in self.getClassParents(element) if isinstance(_, interfaces.ITrait)]
		yield [[self._onAttributes(element)]]
		for t in traits:
			yield "\t\t{0}.__init_properties__(self);".format(self.getSafeName(t))
		yield "\t}"
		yield "});"
		# Class attributes
		for _ in element.getClassAttributes():
			self.pushContext(_)
			yield "Object.defineProperty({0}, \"{1}\", {{value:{2},writable:true}});".format(
				safe_name,
				_.getName(),
				self.write(_.getDefaultValue()) or "undefined")
			self.popContext()
		# Class methods
		for _ in element.getClassMethods():
			self.pushContext(_)
			yield "Object.defineProperty({0}, \"{1}\", {{value:".format(safe_name, _.getName())
			for line in self.onFunction(_, anonymous=True):
				yield [line]
			yield ",writable:true});"
			self.popContext()
		self.popContext()

	def onSingleton( self, element ):
		self.pushContext (element)
		yield "function() {"
		body = self.onClass(element, anonymous=True, slotName=element.getName())
		for i,line in enumerate(self.lines(body)):
			if i == 0:
				yield "\tvar {0} = {1}".format(element.getName(), line[1:])
			else:
				yield "\t" + line
		yield "\tconst self=new {0}();".format(element.getName())
		yield "\tObject.defineProperty(self, '__name__', {{value:\"{0}\",writable:false}});".format(self.getAbsoluteName(element))
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
			parent = self.getSafeName(parents[0])
		else:
			parent = self.getSafeName(parents[0])
			self.environment.report.error(
				"Class has multiple class parents, ignoring the rest: {0}"
				.format(self.getAbsoluteName(element)))
		for t in traits:
			parent = self.getSafeName(t) + "(" + (parent or "Object") + ")"
		return parent

	def _onClassBody( self, element, withConstructors=True, withAccessors=True, withProperties=True):
		"""Iterates through the slots in a context, writing their name and value"""
		slots = element.getSlots()
		if withConstructors:
			for e in element.getConstructors() or [None]:
				self.pushContext(e or interfaces.IConstructor)
				yield self.onConstructor(e)
				self.popContext()
		# Init method
		if withProperties:
			yield "\t__init_properties__() {"
			yield "\t\tconst self=this;"
			parents = self.getClassParents(element)
			traits  = [_ for _ in parents if isinstance(_, interfaces.ITrait)]
			classes = [_ for _ in parents if _ not in traits]
			yield [self._onAttributes(element)]
			if len(classes) > 0:
				yield "\t\tif(super.__init_properties__) {super.__init_properties__();}"
			for t in traits:
				yield "\t\t{0}.__init_properties__(self);".format(self.getSafeName(t))
			yield "\t}"
		# NOTE: Not sure why events were defined as `get` -- there's no point in
		# that, they're immutable.
		# for e in element.getEvents():
		# 	yield "\tget {0} () {{return {1}; }}".format(e.getName(), self.write(e.getDefaultValue()))
		for e in element.getClassMethods():
			self.pushContext(e)
			yield self.onClassMethod(e)
			self.popContext()
		if withAccessors:
			for e in element.getAccessors():
				self.pushContext(e)
				yield self.onAccessor(e)
				self.popContext()
			for e in element.getMutators():
				self.pushContext(e)
				yield self.onMutator(e)
				self.popContext()
		for e in element.getInstanceMethods():
			self.pushContext(e)
			yield self.onMethod(e)
			self.popContext()

	def _onAttributes( self, element ):
		# Initializes the attributes
		c = element
		if c:
			attrs = []
			# We merge in attributes from the current class and then the traits
			# if they do not override
			for p in [c]:
				for a in p.getAttributes():
					n = a.getName()
					if n not in attrs:
						attrs.append(n)
						v = a.getDefaultValue()
						if v:
							yield (
								"if ({0}.{1} === undefined) {{{0}.{1} = {2};}}".format(
								"self", a.getName(), self.write(v))
							)

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

	def onAccessor( self, element ):
		return self.onFunction( element, modifier="get" )

	def onMutator( self, element ):
		return self.onFunction( element, modifier="set" )

	def onMethod( self, element ):
		return self.onFunction( element, modifier="" )

	def onClassMethod( self, element ):
		if isinstance(element.parent, interfaces.ITrait):
			return ["static {1}() {{return {0}.{1}.apply(this, arguments);}}".format(
				self.getSafeName(element.parent),
				element.getName()
			)]
		else:
			return self.onFunction( element, modifier="static" )

	def onConstructor( self, element ):
		call_super   = None
		init         = []
		traits_super = ["const self=this;"]
		ops          = []
		# Constructor can be none in some cases
		c          = element.parent if element else self.getCurrentClass()
		parents    = self.getClassParents(c) if c else []
		traits     = [_ for _ in parents if isinstance(_, interfaces.ITrait)]
		classes    = [_ for _ in parents if _ not in traits]
		if element:
			for op in element.operations:
				if self.isSuperInvocation(op):
					call_super = op
				else:
					ops.append(op)
		# If the element has traits, we need to invoke their explicit constructors in
		# order -- there are issues with the `this` reference in traits that
		# pushed us to move to explicit constructors.
		for t in traits:
			traits_super.append("{0}.__init__(self);".format(self.getSafeName(t)))
		# We only use super if the clas has parents and ther is no explicit
		# constructor
		if c and not call_super:
			if len(classes) > 0:
				# We need to pass the arguments as-is
				init = ["super(...arguments);"] + traits_super + init
			elif traits:
				# In this case the default parent is Object
				init = ["super();this.__init_properties__();"] + traits_super + init
			else:
				# No parent or trait
				init = [";this.__init_properties__();"] + traits_super + init
		else:
			self.jsSelf = "this"
			init = [self.write(call_super)] + traits_super + init
			self.jsSelf = "self"
		return self.onFunction( element, modifier="constructor", anonymous=True, body=init, bindSelf=False, operations=ops)

	def onInitializer( self, element ):
		return self.onFunction( element,  anonymous=True )

	def onInvocation( self, element ):
		res = JavaScriptWriter.onInvocation(self, element)
		# In the edge case where super is invoked in class without parent class
		# but traits, we need to explicitely init the properties.
		# NOTE: This does not fix extending a foreign class.
		if isinstance(element.getTarget(), interfaces.IReference) and element.getTarget().getReferenceName() == "super":
			current = self.getCurrentClass()
			parents = [_ for _ in self.getClassParents(current) if not isinstance(_, interfaces.ITrait)]
			if not parents:
				res += ";this.__init_properties__(this);"
		return res

	def onInstanciation( self, element ):
		"""Writes an invocation operation."""
		i = element.getInstanciable()
		t = self.write(i)
		# Invocation targets can be expressions
		if not isinstance(i, interfaces.IReference): t = "(" + t + ")"
		return "new %s(%s)" % (
			t,
			", ".join(self.write(_) for _ in element.getArguments())
		)


	# =========================================================================
	# CALLBABLE-SPECIFIC RULES
	# =========================================================================

	def _onFunctionBody( self, element, body=None, bindSelf=True, operations=None ):
		"""Writes the body of a function."""
		# Adds the `const self = this`
		if bindSelf: yield self._runtimeSelfBinding(element)
		for _ in self._writeImplicitAllocations(element):
			yield _
		if element:
			for _ in self._onParametersInit(element): yield _
			for _ in self._onPreCondition(element): yield _
		for _ in body or []:
			yield _
		if element:
			event = element.getAnnotation("event")
			if event:
				yield "return " + self._runtimeEventBind(event.getContent()) + ";"
			for _ in element.getOperations() if operations is None else operations:
				if isinstance(_, types.LambdaType):
					_()
				elif isinstance(_, interfaces.IEvaluable):
					yield self.write(_) + ";"
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
	# OPERATIONS
	# =========================================================================

	def onAllocation( self, element ):
		return JavaScriptWriter.onAllocation(self, element, "var ")

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
			return super(Writer, self)._runtimeSuperResolution( resolution )

	def _runtimeSuperInvocation( self, element ):
		target = element.getTarget()
		if isinstance(target, interfaces.IReference) and target.getReferenceName() == "super":
			# We have a direct super invocation, which means we're invoking the
			# super constructor
			return "super({0})".format(
				", ".join(map(self.write, element.getArguments())),
			)
		else:
			# Otherwise we're invoking a method from the super, which
			# is a simple call forwarding
			return "{0}({1})".format(
				self.write(element.getTarget()),
				", ".join(map(self.write, element.getArguments())),
			)

	def _runtimeInvocation( self, element ):
		args = element.getArguments()
		return "{0}({1})".format(
			self.write(element.getTarget()),
			", ".join(self.write(_) for _ in args)
		)

MAIN_CLASS = Writer

# EOF - vim: tw=80 ts=4 sw=4 noet
