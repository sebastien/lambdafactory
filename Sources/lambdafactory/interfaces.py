
def abstract(f):
	def decorator(*args, **kwargs):
		raise Exception("Not implemented")
	decorator.isAbstract = True
	decorator.__doc__ = getattr(f, "__doc__")
	return decorator

def implements( instance, interface ):
	"""This is a simple method that allows to check if the given instance
	implements the given interface."""
	res = []
	for key in interface.__dict__.keys():
		if not hasattr(instance, key):
			res.append(key)
		else:
			func = getattr(instance, key)
			if hasattr(func, "isAbstract"):
				res.append(key)
	if not res:
		return True
	else:
		return res

def assertImplements( instance, interface ):
	res = implements(instance, interface)
	if res is True: return
	else: raise Exception("Operations not implemented: " + str(res))

#------------------------------------------------------------------------------
#
#  Element Interfaces
#
#------------------------------------------------------------------------------

class IReferencable:
	"""A referencable is an element that can be referenced either by id (it is
	unique and stable), or by a name (which is also not supposed to change).

	Types are good examples of referencables: they have an *absolute name* (like
	`Data.List`), but can also be bound to slots within contexts which give them
	"local names" (like `List := Data.List`)
	"""

	@abstract
	def getId( self ):
		"""Returns the identifier of this referencable. The identifier must be
		unique among all elements."""

	@abstract
	def getName( self ):
		"""Returns the *absolute name* for this referencable element."""

class IEvaluable:
	"""An evaluable is an element that can produce a value. Evaluable elements
	then have associated type information."""

	@abstract
	def evaluate( self, context ):
		"""This *evaluates* the element in the given context. This returns the
		type (internal or not) for the value of the evaluated element, which
		should be as narrow as possible."""

class IAssignable:
	"""An assignable value can be *bound to a slot* within a context. Each
	assignable then has a a name for a particular context."""

	@abstract
	def bound( self, context ):
		"""Returns the name of this element in the given context."""

	@abstract
	def bind( self, context, name ):
		"""Binds the given element to the given context, using the given
		name."""

	@abstract
	def bounds( self ):
		"""Returns the list of bounds (context, name) between this element and
		all the contexts to which it is bound."""

	@abstract
	def unbind( self, context, name ):
		"""Unbinds this element from the given context."""

class IInstanciable:
	"""Instanciable is a property of some elements that allows them to be
	instanciated. Conceptually, an instanciation could be considered as a
	specific kind of invocation."""


class IInvocable:
	"""An invocable can be used in an invocation operation."""

	@abstract
	def getArguments( self ):
		"""Returns a list of arguments (which are names associated with optional
		type information."""

#------------------------------------------------------------------------------
#
#  Operational Elements
#
#------------------------------------------------------------------------------

class IValue(IEvaluable):
	"""A value represents an atomic element of the language, like a number, a
	string, or a name (that can resolved by the language, acts as key for data
	structures, etc.)."""

class ILitteral(IValue):
	"""A litteral is a value that does not need a context to be evaluated. The
	evaluation is direct."""

class INumber(IValue):
	pass

class IReference(IValue, IReferencable):
	"""A reference is a name that can be converted into a value using a
	resolution operation (for instance)."""

	def getReferenceName( self ):
		"""Returns the name which this reference contains. The name is used by
		the resolution operation to actually resolve a value from the name."""

class IOperator(IReference):
	pass

class ISlot(IReference):
	"""An argument is a reference with additional type information."""

	def getTypeInformation( self ):
		"""Returns type information (constraints) that are associated to this
		argument."""

class IArgument(ISlot):
	pass

#------------------------------------------------------------------------------
#
#  Operations
#
#------------------------------------------------------------------------------

class IOperation:

	@abstract
	def addOpArgument( self, argument ):
		"""Adds an argument to this operation. This should do checking of
		arguments (by expected internal type and number)."""

	@abstract
	def getOpArguments( self ):
		"""Returns the arguments to this operation."""

	@classmethod
	def getOpArgumentsInternalTypes( self ):
		"""Returns the *internal types* for this operations arguments. This is
		typically the list of interfaces or classes that the arguments must
		comply to."""

class IAssignation(IOperation):
	ARGS = [ IReference, IEvaluable ]

	@abstract
	def getTargetReference( self ):
		"""Returns this assignation target reference."""

	@abstract
	def getAssignedValue( self ):
		"""Returns this assigned evaluable."""

class IInstanciation(IOperation):
	ARGS = [ IInstanciable ]

	@abstract
	def getInstanciable( self ):
		"""Returns the instanciable used in this operation."""

class IAllocation(IOperation):
	ARGS = [ ISlot ]

	@abstract
	def getSlotToAllocate( self ):
		"""Returns slot to be allocated by this operation."""

class IResolution(IOperation):
	"""A resolution resolves a reference into a value."""
	ARGS = [ IReferencable ]

	@abstract
	def getReference( self ):
		"""Returns the reference to be resolved."""

class IComputation(IOperation):
	ARGS = [ IOperator, IEvaluable, IEvaluable ]

	@abstract
	def getOperator( self ):
		"""Returns the reference to be resolved."""

	@abstract
	def getOperand( self ):
		"""Returns the left operand of this computation."""

	@abstract
	def getOperands( self ):
		"""Returns the left (and right, if any) operands of this computation."""

	@abstract
	def getLeftOperand( self ):
		"""Returns the left operand of this computation."""

	@abstract
	def getRightOperand( self ):
		"""Returns the right operand of this computation (if any)"""

class IInvocation(IOperation):
	ARGS = [ IEvaluable, [IEvaluable] ]

	@abstract
	def getTarget( self ):
		"""Returns the invocation target reference."""

	@abstract
	def getArguments( self ):
		"""Returns evaluable arguments."""

# FIXME
class ITermination(IOperation):
	ARGS = [ IEvaluable ]

	@abstract
	def getReturnedEvaluable( self ):
		"""Returns the termination return evaluable."""

#------------------------------------------------------------------------------
#
#  Generic Element Interfaces
#
#------------------------------------------------------------------------------

class IContext:
	"""A context is an element that has slots, which bind evaluable elements
	(aka values) to names."""

	@abstract
	def setSlot( self, name, evaluable ):
		"""Binds the given evaluable to the named slot."""

	@abstract
	def getSlot( self, name ):
		"""Returns the given evaluable bound to named slot."""

	@abstract
	def hasSlot( self, name ):
		"""Tells if the context has a slot with the given name."""

	@abstract
	def getSlots( self ):
		"""Returns (key, evaluable) pairs representing the slots within this
		context."""

class IClass(IContext):
	pass

	@abstract
	def getOperations( self ):
		"""Returns the operations (methods and class methods) defined within this class."""
		pass

	@abstract
	def getMethods( self ):
		"""Returns the methods defined within this class."""
		pass
	
	@abstract
	def getClassMethods( self ):
		"""Returns the class method defined within this class."""
		pass

	def getName( self ):
		"""Returns this class name. It can be `None` if the class is anonymous."""

class IModule(IContext):
	pass

	@abstract
	def getClasses( self ):
		pass

class IProcess:
	"""A process is a sequence of operations."""

	@abstract
	def addOperation( self, operation ):
		"""Adds the given operation as a child of this process."""

	@abstract
	def addOperations( self, *operations ):
		"""Adds the given operations as children of this process."""

	@abstract
	def getOperations( self ):
		"""Returns the list of operations in this process."""

class IFunction(IProcess):
	pass

class IMethod(IFunction):
	pass

class IClassMethod(IMethod):
	pass

# EOF