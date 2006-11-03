#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 02-Nov-2006
# Last mod  : 03-Nov-2006
# -----------------------------------------------------------------------------

# FIXME: Evaluable == Expression ?

from interfaces import *
import modeltypes as mt

class ModelException(Exception):
	pass

class ModelBadArgument(Exception):
	def __init__( self, someClass, expectedClass, argument ):
		Exception.__init__(self, "Bad argument: %s expected %s, got %s" \
		% (someClass, expectedClass, argument))

class Element:
	"""Element is the *base class* for every class within this module. This is
	where common operations can be defined."""
	COUNT = 0

	def __init__( self, name=None ):
		assert name is None or type(name) in (str, unicode)
		self._id    = self.COUNT
		self._name  = name
		self.COUNT += 1

	@classmethod
	def getModelType( self ):
		return mt.typeFromClass(self)

# ------------------------------------------------------------------------------
#
# STRUCTURAL AND COMPILE/RUN TIME ELEMENTS
#
# ------------------------------------------------------------------------------

class Context(Element, IContext):

	def __init__( self, name=None ):
		Element.__init__(self, name=name)
		assertImplements(self, IContext)
		self._slots = {}

	def setSlot( self, name, evaluable ):
		if not isinstance(evaluable, IAssignable):
			raise ModelBadArgument(self, IAssignable, evaluable)
		self._slots[name] = evaluable

	def getSlot( self, name ):
		return self._slots.get(name)

	def hasSlot( self, name ):
		return name in self._slots().keys()

class Class(Context):

	def getMethods( self ):
		return [value for value in self._slots.values() if isinstance(value, IInvocable)]

# ------------------------------------------------------------------------------
#
# PROCESSES
#
# ------------------------------------------------------------------------------

class Process( Element, IProcess ):

	def __init__(self, name=None ):
		Element.__init__(self, name)
		self._operations = []
		assertImplements(self, IEvaluable)

	def addOperation( self, operation ):
		if not isinstance(operation, IOperation):
			raise ModelException("%s expected %s, got %s" \
			% (self, IOperation, operation.__class__))
		self._operations.append(operation)

	def addOperations( self, *operations ):
		map( self.addOperation, operations )

	def getOperations( self ):
		return self._operations
	
	def evaluate( self, context ):
		pass
		# TODO: Find how we process the operations to get a type
		

class Function(Process, IReferencable, IInvocable, IAssignable):

	def __init__(self, name, arguments ):
		Process.__init__(self, name=name)
		self._arguments = arguments
		assertImplements(self, IReferencable)
		assertImplements(self, IInvocable)

	def setArguments( self, arguments ):
		"""Sets the arguments for this function."""
		self._arguments = []
		for argument in arguments:
			if not isinstance(argument, ISlot):
				raise ModelBadArgument(self, ISlot, argument)
			self._arguments.append(argument)

	def getArguments( self ):
		return self._arguments

	def getArgument( self, index ):
		if index > len(self._arguments): return None
		return self._arguments[index]

	def getName( self ):
		return self._name
	
	def getId( self ):
		return self._id

class Method(Function):
	pass

# ------------------------------------------------------------------------------
#
# OPERATIONS
#
# ------------------------------------------------------------------------------

class Operation(Element, IEvaluable, IOperation):

	ARGS = []

	def __init__( self, *arguments ):
		Element.__init__(self)
		assertImplements(self, IEvaluable)
		self._arguments = []
		self.setArguments(arguments)

	def setArguments( self, arguments ):
		if not len(arguments) <= len(self.ARGS):
			raise ModelException("Too many arguments: %s expected %s, got %s" \
			% (self, len(self.ARGS), len(arguments)))
		self._arguments = []
		map(self.addArgument, arguments)

	def addArgument( self, argument ):
		offset = len(self._arguments)
		if offset > len(self.ARGS):
			raise ModelException("Too many arguments: %s expected args %s as %s, got %s" \
			% (self, offset, len(self.ARGS), offset + 1))
		if not self._isInstance(argument, self.ARGS[offset]):
			raise ModelException("Incompatible argument:  %s expected arg %s as  %s, got %s" \
			% (self, offset, self.ARGS[offset], argument.__class__.__name__))
		self._arguments.append(argument)

	def getArguments( self ):
		"""Returns the arguments to this operation."""
		return self._arguments

	def evaluate( self, context ):
		pass
		# TODO: Find how we process the operations to get a type

	@classmethod
	def getOperationName( self ):
		"""This is a simple shorthand to return the Operation class name."""
		return self.__name__

	@classmethod
	def getArgumentsInternalTypes( self ):
		"""Returns the *internal types* for this operations arguments. This is
		typically the list of interfaces or classes that the arguments must
		comply to."""

	@staticmethod
	def _isInstance( arg, argtype ):
		"""A more specific implementation of isinstance, that allows list of
		types to be used as types. For instance, `[ISlot]` stands for ''a
		list of arguments''."""
		if type(argtype) in (list, tuple):
			if not (type(arg) in (list, tuple)): return False
			for e in arg:
				if not isinstance(e, argtype[0]):
					return False
			return True
		else:
			return isinstance(arg, argtype)

class Instanciation(Operation):
	ARGS = [ IInstanciable ]

	def getInstanciable( self ):
		"""Returns the instanciable used in this operation."""
		return self.getArgument(0)

class Assignation(Operation):
	ARGS = [ IReference, IEvaluable ]

	def getTarget( self ):
		"""Returns this assignation target."""
		return self.getArgument(0)

	def getAssignedValue( self ):
		"""Returns this assigned value."""
		return self.getArgument(1)

class Allocation(Operation):
	ARGS = [ ISlot ]

	def geSlotToAllocate( self ):
		"""Returns slot to be allocated by this operation."""
		return self.getArgument(0)

class Resolution(Operation):
	ARGS = [ IReference ]

	def getReference( self ):
		"""Returns the reference to be resolved."""
		return self.getArgument(0)

class Computation(Operation):
	ARGS = [ IOperator, IEvaluable, IEvaluable ]

	def getOperator( self ):
		"""Returns the reference to be resolved."""
		return self.getArgument(0)

	def getOperand( self ):
		return self.getLeftOperand()

	def getOperands( self ):
		return self.getLeftOperand(), self.getRightOperand()

	def getLeftOperand( self ):
		return self.getArgument(1)

	def getRightOperand( self ):
		return self.getArgument(2)

class Invocation(Operation):

	ARGS = [ IEvaluable, [IEvaluable] ]

	def getTarget( self ):
		"""Returns the invocation target reference."""
		return self.getArgument(0)

	def getArguments( self ):
		"""Returns evaluable arguments."""

class Termination(Operation):

	ARGS = [ IEvaluable ]

	def getReturnedEvaluable( self ):
		"""Returns the termination return evaluable."""
		return self.getArgument(0)

	def getArguments( self ):
		"""Returns evaluable arguments."""

# ------------------------------------------------------------------------------
#
# VALUES
#
# ------------------------------------------------------------------------------

class Value(Element, IEvaluable):
	pass

class Litteral(Value):
	pass

class Reference(Value, IReference):

	def __init__( self, refname ):
		Value.__init__(self)
		assert type(refname) in (str, unicode), "Expected string: " +repr(refname)
		self._refname = refname
		assertImplements(self, IReference)

	def getReferenceName( self ):
		return self._refname

class Operator(Reference, IOperator):
	pass

class Slot(Reference, ISlot):

	def __init__( self, refname, typeinfo ):
		Reference.__init__(self, refname)
		self._typeinfo = typeinfo
		assertImplements(self, ISlot)

	def getReferenceName( self ):
		return self._refname

class Argument(Slot, IArgument):
	pass

# ------------------------------------------------------------------------------
#
# FACTORY
#
# ------------------------------------------------------------------------------

class Factory:
	"""This class takes a module and look for classes with the same name as the
	`createXXX` methods and instanciates them.

	For instance, if you define a module with classes like `Value`, `Litteral`,
	`Invocation`, `Function`, etc. you just have to give this module to the
	factory constructor and it will be used to generate the given element."""

	def __init__( self, module ):
		self._module = module

	def _getImplementation( self, name ):
		if not hasattr(self._module, name ):
			raise ModelException("Module %s does not implement: %s" % \
			(self._module, name))
		else:
			return getattr(self._module, name)

	def createFunction( self, name, arguments ):
		return self._getImplementation("Function")(name, arguments)

	def createMethod( self, name, arguments ):
		return self._getImplementation("Method")(name, arguments)

	def createClass( self, name ):
		return self._getImplementation("Class")(name)

	def allocate( self, slot ):
		return self._getImplementation("Allocation")(slot)

	def assign( self, name, evaluable ):
		return self._getImplementation("Assignation")(name, evaluable)

	def compute( self, operatorName, leftOperand, rightOperand=None ):
		return self._getImplementation("Computation")(operatorName, leftOperand, rightOperand)

	def invoke( self, evaluable, *arguments ):
		return self._getImplementation("Invocation")(evaluable, arguments)

	def resolve( self, reference ):
		return self._getImplementation("Resolution")(reference)

	def returns( self, evaluable ):
		return self._getImplementation("Termination")(evaluable)

	def _ref( self, name ):
		return self._getImplementation("Reference")(name)

	def _slot( self, name, typeinfo="None" ):
		return self._getImplementation("Slot")(name, typeinfo)

	def _arg( self, name, typeinfo=None ):
		return self._getImplementation("Argument")(name, typeinfo)
	
	def _op( self, symbol ):
		return self._getImplementation("Operator")(symbol)

# EOF
