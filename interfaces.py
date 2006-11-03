
def abstract(f):
	def decorator(*args, **kwargs):
		raise Exception("Not implemented")
	decorator.isAbstract = True
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

class IInvocable(IProcess):
	"""An invocable can be used in an invocation operation."""

	@abstract
	def getArguments( self ):
		"""Returns a list of arguments (which are names associated with optional
		type information."""

class IOperation:

	@abstract
	def addArgument( self, argument ):
		"""Adds an argument to this operation. This should do checking of
		arguments (by expected internal type and number)."""

	@abstract
	def getArguments( self ):
		"""Returns the arguments to this operation."""

	@classmethod
	def getArgumentsInternalTypes( self ):
		"""Returns the *internal types* for this operations arguments. This is
		typically the list of interfaces or classes that the arguments must
		comply to."""

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

class IReference(IValue):
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

# EOF
