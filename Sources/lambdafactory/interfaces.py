
def abstract(f):
	def decorator(self, *args, **kwargs):
		raise Exception("Operation not implemented: %s in %s" % (f, self.__class__))
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
#  Annotation Elements
#
#------------------------------------------------------------------------------

class IAnnotation:
	"""An annotation is some information that is not used for the actual
	program, but annotates/gives meta-information about is elements."""

	@abstract
	def getContent( self ):
		"""Returns the content of this annotation."""

class IComment(IAnnotation):
	"""A comment is an annotation that can occur anywhere in a source file."""

class IDocumentation(IAnnotation):
	"""Documentation is often attached to various language elements.
	Documentation can be found in coments (as in Java), or be directly embedded
	as values (as in Python)."""

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

class IString(IValue):
	pass

class IReference(IValue, IReferencable):
	"""A reference is a name that can be converted into a value using a
	resolution operation (for instance)."""

	def getReferenceName( self ):
		"""Returns the name which this reference contains. The name is used by
		the resolution operation to actually resolve a value from the name."""

class IOperator(IReference):
	pass

class ISlot(IReference, IAssignable):
	"""An argument is a reference with additional type information."""

	def getTypeInformation( self ):
		"""Returns type information (constraints) that are associated to this
		argument."""

class IArgument(ISlot):
	pass

class IAttribute(ISlot):
	pass

class IClassAttribute(IAttribute):
	pass

#------------------------------------------------------------------------------
#
#  Contexts and Processes
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
	def getAttributes( self ):
		"""Returns the attributes defined within this class."""
		pass

	@abstract
	def getClassAttributes( self ):
		"""Returns the class attributes defined within this class."""
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

	@abstract
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

class IBlock(IProcess):
	"""A block is a specific type of (sub) process."""

class IFunction(IProcess):

	@abstract
	def getName( self ):
		"""Returns this class name. It can be `None` if the class is anonymous."""

class IMethod(IFunction):
	pass

class IClassMethod(IMethod):
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

	@abstract
	def setOpArgument( self, i, value ):
		"""Sets the given argument of this operation, by argument index."""

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
	ARGS = [ IReferencable, IReferencable ]

	@abstract
	def getReference( self ):
		"""Returns the reference to be resolved."""

	@abstract
	def getContext( self ):
		"""Returns the (optional) context in which the resolution should occur."""

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

class IMatchOperation(IOperation):
	"""A match operation is the binding of an expression and a process."""
	ARGS = [ IEvaluable, IProcess ]

	def getPredicate( self ):
		"""Returns the evaluable that acts as a predicate for this operation."""
		return self.getOpArgument(0)

	def getProcess( self ):
		"""Returns the process that will be executed if the rule matches."""
		return self.getOpArgument(1)

class ISelection(IOperation):
	"""Selections are the abstract objects behind `if`, `select` or
	pattern-matching operations. Each selection has match operations as
	arguments, which bind a subprocess to a predicate expression."""
	ARGS = [ [IMatchOperation] ]

	@abstract
	def addRule( self, evaluable ):
		"""Adds a rule to this operation."""

	@abstract
	def getRules( self ):
		"""Returns the ordered set of rule for this selection."""

class IIteration( IOperation ):
	"""An iteration is the multiple application of a process given a set of
	values produced by an iterator."""
	ARGS = [ ISlot, IEvaluable, IProcess ]

	def getIteratedSlot( self ):
		"""Returns the slot that will contain the iterated value."""
		return self.getOpArgument(0)

	def getIterator( self ):
		"""Returns this iteration iterator."""
		return self.getOpArgument(1)

	def getProcess( self ):
		"""Returns the iterated process."""
		return self.getOpArgument(2)

class IEnumeration( IOperation ):
	"""An enumeration produces values between a start and an end value, with the
	given step."""
	ARGS = [ IEvaluable, IEvaluable, IEvaluable ]

	def getStart( self ):
		"""Returns this enumeration start."""
		return self.getOpArgument(0)

	def getEnd( self ):
		"""Returns this enumeration end."""
		return self.getOpArgument(1)

	def getStep( self ):
		"""Returns this enumeration step."""
		return self.getOpArgument(2)

	def setStep( self, value ):
		"""Sets this enumeration step"""
		return self.setOpArgument(2, value)

class IRepetition( IOperation ):
	"""A repetition is the repetitive execution of a process according to a
	predicate expression which can be modified by the process."""
	ARGS = [ IEvaluable, IProcess ]

	def getCondition( self ):
		"""Gets the expression that is the condition for this repetition."""
		return self.getOpArgument(0)

	def getProcess( self ):
		return self.getOpArgument(1)

class ITermination(IOperation):
	ARGS = [ IEvaluable ]

	@abstract
	def getReturnedEvaluable( self ):
		"""Returns the termination return evaluable."""

# EOF
