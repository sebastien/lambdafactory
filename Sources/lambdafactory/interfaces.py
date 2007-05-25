# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 02-Nov-2006
# Last mod  : 22-May-2007
# -----------------------------------------------------------------------------

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
	if res is True:
		return
	else:
		raise Exception("Operations not implemented: %s from %s in %s" % (res, interface, instance.__class__))

class Constants:

	MainFunction  = "__main__"
	CurrentModule = "__current__"
	Constructor   = "__init__"
	Destructor    = "__destroy__"
	ModuleInit    = "__moduleinit__"
	CurrentValue  = "__currentvalue__"
	PARENS_PRIORITY = 9999

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

	# FIXME: I guess evaluation should be left to an evaluator
	#@abstract
	#def evaluate( self, context ):
	#	"""This *evaluates* the element in the given context. This returns the
	#	type (internal or not) for the value of the evaluated element, which
	#	should be as narrow as possible."""

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

class IAbstractable:
	"""An abstractable element is an element that is allow to have
	no underlying implementation.  Abstract element are typically interfaces,
	methods, functions, operations, and sometimes modules and classes."""

	@abstract
	def isAbstract( self ):
		"""Tells wether the given abstractable is abstract or not."""

	@abstract
	def setAbstract( self, isAbstract=True ):
		"""Sets wether the given abstractable is abstract or not."""

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

	@abstract
	def getName( self ):
		"""Returns the name of this annotation."""
		
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

class ILiteral(IValue):
	"""A literal is a value that does not need a context to be evaluated. The
	evaluation is direct."""

class INumber(ILiteral):
	pass

class IString(ILiteral):
	pass

class IList(IValue):

	@abstract
	def addValue( self, value ):
		"""Adds a value to this list."""
		pass

	def getValues( self ):
		"""Returns the values within this list."""
		pass

class IDict(IValue):
	"""A dictionary is a binding of key to values. It may or may not be ordered,
	depending on the implementation/model semantics."""

	@abstract
	def setValue( self, key, value ):
		"""Sets the value to be associated to the given key (which must be an
		evaluable)."""
		pass

	@abstract
	def getItems( self ):
		"""Returns the items contained in this dict"""
		pass

class IReference(IValue, IReferencable):
	"""A reference is a name that can be converted into a value using a
	resolution operation (for instance)."""

	def getReferenceName( self ):
		"""Returns the name which this reference contains. The name is used by
		the resolution operation to actually resolve a value from the name."""

class IOperator(IReference):
	pass

	@abstract
	def setPriority( self, priority ):
		"""Sets the priority for this operator"""
	
	@abstract
	def getPriority( self ):
		"""Gets the priority for this operator"""

class ISlot(IReference, IAssignable):
	"""An argument is a reference with additional type information."""

	@abstract
	def getTypeInformation( self ):
		"""Returns type information (constraints) that are associated to this
		argument."""

class IArgument(ISlot):
	pass

class IAttribute(ISlot):
	
	@abstract
	def setDefaultValue(self):
		"""Sets the default value for this attribute"""

	@abstract
	def getDefaultValue(self):
		"""Gets the default value for this attribute"""

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

	@abstract
	def setParent( self, context ):
		"""Sets the parent context for this context."""

	@abstract
	def getParent( self ): 
		"""Returns the parent context for this context (if any)"""

class IClass(IContext, IReferencable):
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
	def getConstructors(self):
		"""Returns the constructors for this class"""
		pass
	
	@abstract
	def getDestructors(self):
		"""Returns the destructors for this class"""
		pass
	
	@abstract
	def getInstanceMethods( self ):
		"""Returns the instance methods defined within this class."""
		pass
	
	@abstract
	def getClassMethods( self ):
		"""Returns the class method defined within this class."""
		pass

	@abstract
	def getName( self ):
		"""Returns this class name. It can be `None` if the class is anonymous."""

	@abstract
	def getSuperClasses( self ):
		"""Returns the list of inherited classes references."""

class IAbstractClass(IClass, IAbstractable):
	"""An abstract class is a class that has at least one abstract element."""

class IInterface(IAbstractClass):
	"""An interface is an abstract class that only has abstract elements."""

class IModule(IContext):
	pass

	@abstract
	def getClasses( self ):
		pass

class IProgram(IContext):
	"""The program is the core context and entry point for almost every
	operation offered by LambdaFactory."""
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

class IClosure(IProcess, IContext):

	@abstract
	def getArguments( self ):
		pass

	@abstract
	def setArguments( self ):
		pass

class IFunction(IClosure, IReferencable, IAbstractable):

	@abstract
	def getName( self ):
		"""Returns this class name. It can be `None` if the class is anonymous."""

class IMethod(IFunction):
	pass

class IConstructor(IMethod):
	pass

class IDestructor(IMethod):
	pass

class IInstanceMethod(IMethod):
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

class IImportOperation(IOperation):
	ARGS = [ IEvaluable, IEvaluable ]
	
	def getTarget( self ):
		if self.getAlias():
			return self.getAlias()
		return self.getName()

	def getName( self ):
		return self.getOpArgument(0)

	def getAlias( self ):
		return self.getOpArgument(1)

class IEvaluation(IOperation):
	ARGS = [ IEvaluable, IEvaluable ]

	def getEvaluable( self ):
		return self.getOpArgument(0)

class IAssignation(IOperation):
	ARGS = [ IEvaluable, IEvaluable ]

	@abstract
	def getTarget( self ):
		"""Returns this assignation target reference, which can be an evaluable
		(in case you assign to self.something, or a reference)"""

	@abstract
	def getAssignedValue( self ):
		"""Returns this assigned evaluable."""

class IAllocation(IOperation):
	ARGS = [ ISlot, IEvaluable ]

	@abstract
	def getSlotToAllocate( self ):
		"""Returns slot to be allocated by this operation."""

	@abstract
	def getDefaultValue( self ):
		"""Returns the expression that assigns the default value."""
		
class IResolution(IOperation):
	"""A resolution resolves a reference into a value."""
	ARGS = [ IReferencable, IEvaluable ]

	@abstract
	def getReference( self ):
		"""Returns the reference to be resolved."""

	@abstract
	def getContext( self ):
		"""Returns the (optional) context in which the resolution should occur."""

class IComputation(IOperation):
	ARGS = [ IOperator, IEvaluable, IEvaluable ]

	def getOperator( self ):
		"""Gets the operator for this computation"""
		return self.getOpArgument(0)

	def setOperator( self, operator ):
		"""Sets the operator for this computation"""
		return self.getOpArgument(0, operator)
	
	def getOperand( self ):
		"""Returns the left operand of this computation."""
		return self.getLeftOperand()
	
	def getOperands( self ):
		"""Returns the left (and right, if any) operands of this computation."""
		return self.getLeftOperand(), self.getRightOperand()
	
	def getLeftOperand( self ):
		"""Returns the left operand of this computation."""
		return self.getOpArgument(1)

	def getRightOperand( self ):
		"""Returns the right operand of this computation (if any)"""
		return self.getOpArgument(2)
	
	def setLeftOperand( self, operand ):
		"""Sets the left operand of this computation."""
		return self.setOpArgument(1, operand)

	def setRightOperand( self, operand ):
		"""Sets the right operand of this computation"""
		return self.setOpArgument(2, operand)

class IInvocation(IOperation):
	ARGS = [ IEvaluable, [IEvaluable] ]

	def getTarget( self ):
		"""Returns the invocation target reference."""
		return self.getOpArgument(0)

	def getArguments( self ):
		"""Returns evaluable arguments."""
		return self.getOpArgument(1) or ()

class IInstanciation(IOperation):
	ARGS = [ IEvaluable, [IEvaluable] ]

	def getInstanciable( self ):
		"""Returns the instanciable used in this operation."""
		return self.getOpArgument(0)

	def getArguments( self ):
		"""Returns evaluable arguments."""
		return self.getOpArgument(1) or ()

class ISliceOperation(IOperation):
	ARGS = [ IEvaluable, IEvaluable ]

	def getTarget( self ):
		"""Returns the operation target."""
		return self.getOpArgument(0)

	def getSlice( self ):
		"""Returns evaluable that will return the slice."""
		return self.getOpArgument(1)

class IMatchOperation(IOperation):
	"""A match operation is the binding of an expression and a process."""
	ARGS = [ IEvaluable, IProcess ]

	def getPredicate( self ):
		"""Returns the evaluable that acts as a predicate for this operation."""
		return self.getOpArgument(0)

	def setPredicate( self, v ):
		return self.setOpArgument(0, v)

	def getProcess( self ):
		"""Returns the process that will be executed if the rule matches."""
		return self.getOpArgument(1)

	def setProcess( self, v ):
		return self.setOpArgument(1, v)


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
	ARGS = [IEvaluable, IEvaluable ]

	def getIterator( self ):
		"""Returns this iteration iterator."""
		return self.getOpArgument(0)

	def getClosure( self ):
		"""Returns the closure that will be applied to the iterator."""
		return self.getOpArgument(1)

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
