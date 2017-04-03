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

There are a few specific workarounds the limitations of ECMAScript's objec
model:


1) Constructors do not directly initialize attributes/properties, but
   instead defer the initialization to the `__init_properties__` method
   defined in classes. This ensures that proerties initialization can
   be overriden by subclasses.
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
			yield "\t\tif (typeof {0} != \"undefined\") {{this.{0} = {0};}}".format(s.getName())
		yield "\t}"
		yield "}"
		yield "Object.defineProperty({0}, \"__name__\", {{value:\"{1}\",writable:false}});".format(safe_name, abs_name)
		self.popContext ()

	def onTrait( self, element ):
		self.pushContext (element)
		yield "function(_) {"
		yield "\tvar res = class extends " + self._onClassParents(element, self.getClassParents(element), base="_") + " {"
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
		self.popContext()

	def onSingleton( self, element ):
		self.pushContext (element)
		yield "function() {"
		for i,line in enumerate(self.lines(self.onClass(element, anonymous=True, slotName=element.getName()))):
			if i == 0:
				yield "\tvar {0} = {1}".format(element.getName(), line[1:])
			else:
				yield line
		yield "\tvar self=new {0}();".format(element.getName())
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
			yield "\t\tlet self=this;"
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
								"if (typeof {0}.{1} === typeof undefined) {{{0}.{1} = {2};}}".format(
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

	def onAccesor( self, element ):
		return self.onFunction( element, modifier="get" )

	def onMutator( self, element ):
		return self.onFunction( element, modifier="set" )

	def onMethod( self, element ):
		return self.onFunction( element, modifier="" )

	def onClassMethod( self, element ):
		return self.onFunction( element, modifier="static" )

	def onConstructor( self, element ):
		call_super   = None
		init         = []
		traits_super = ["let self=this;"]
		ops          = []
		# Constructor can be none in some cases
		c          = element.parent if element else self.getCurrentClass()
		if element:
			for op in element.operations:
				if self.isSuperInvocation(op):
					call_super = op
				else:
					ops.append(op)
		# We only use super if the clas has parents and ther is no explicit
		# constructor
		if c and not call_super:
			parents = self.getClassParents(c)
			traits  = [_ for _ in parents if isinstance(_, interfaces.ITrait)]
			classes = [_ for _ in parents if _ not in traits]
			for t in traits:
				traits_super.append("{0}.__init__(self);".format(self.getSafeName(t)))
			if len(classes) > 0:
				# We need to pass the arguments as-is
				init = ["super(...arguments);"] + traits_super + init
			elif traits:
				# In this case the default parent is Object
				init = ["super();this.__init_properties__();"] + traits_super + init
			else:
				# No parent or trait
				init = ["this.__init_properties__();"] + traits_super + init
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
				res += "this.__init_properties__(this);"
		return res


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
			event = element.getAnnotation("event")
			if event:
				yield self._runtimeBindEvent(event.getContent())
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


	def _runtimeGetMethodByName(self, name, value=None, element=None):
		return self._runtimeSelfReference(element) + "." + name

	def _runtimeWrapMethodByName(self, name, value=None, element=None):
		s = self._runtimeSelfReference(element)
		if isinstance(value, interfaces.IClassMethod):
			if self.findInContext(interfaces.IClassMethod):
				# In ES, we need to re-bind static methods when we're calling
				# them back, otherwise the reference will be lost.
				return "{0}.{1}.bind({0})".format(s, name)
			else:
				return "Object.getPrototypeOf({0}).constructor.{1}.bind(Object.getPrototypeOf({0}).constructor)".format(s, name)
		else:
			return "{0}.{1}.bind({0})".format(s, name)

	def _runtimeBindEvent( self, event ):
		return "return __bind__( self, \"{0}\", arguments[0], arguments[1] );".format(event)

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
