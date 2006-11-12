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
	where common operations can be defined.
	
	Each element has a `meta` attribute that can be used to store some things
	like documentation."""
	COUNT = 0

	def __init__( self, name=None ):
		assert name is None or type(name) in (str, unicode)
		self._id     = self.COUNT
		self._name   = name
		self._source = None
		self.meta    = {}
		self.COUNT  += 1

	def getSource( self ):
		"""Returns the source for this element (it can be an URL, a file path,
		etc)."""
		return self._source

	def setSource( self, source ):
		"""Sets the source for this element."""
		self._source = source

	@classmethod
	def getModelType( self ):
		return mt.typeFromClass(self)

	def hasDocumentation( self ):
		"""Tells if this element has attached documentation."""
		return self.meta.get("doc") 

	def getDocumentation( self ):
		"""Gets the documentation attached to this element."""
		return self.meta.get("doc")

	def setDocumentation( self, text ):
		"""Sets the documentation for this element."""
		self.meta["doc"] = text

class Annotation(IAnnotation):

	def __init__( self, content = None ):
		assert content is None or type(content) in (str, unicode)
		self._content = None

	def setContent( self, content ):
		self._content = content

	def getContent( self ):
		return self._content

class Comment(Annotation, IComment):
	pass

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
		return name in self._slots.keys()

	def getSlots( self ):
		return self._slots.items()

class Class(Context, IClass, IAssignable):

	def __init__( self, name=None ):
		Context.__init__(self, name=name)
		assertImplements(self, IClass)

	def getOperations( self ):
		return [value for value in self._slots.values() if isinstance(value, IInvocable)]

	def getMethods( self ):
		return [value for value in self._slots.values() if isinstance(value, IMethod) and not isinstance(value, IClassMethod)]

	def getClassMethods( self ):
		return [value for value in self._slots.values() if isinstance(value, IClassMethod)]

	def getName( self ):
		return self._name

class Module(Context, IModule, IAssignable):

	def __init__( self, name=None ):
		Context.__init__(self, name=name)
		assertImplements(self, IModule)

	def getClasses( self ):
		return [value for value in self._slots.values() if isinstance(value, IClass)]

	def getName( self ):
		return self._name

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
		

class Function(Process, IReferencable, IAssignable, IFunction):

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

class Method(Function, IMethod):
	pass

class ClassMethod(Method, IClassMethod):
	pass


# ------------------------------------------------------------------------------
#
# OPERATIONS
#
# ------------------------------------------------------------------------------

class Operation(Element, IEvaluable, IOperation):

	def __init__( self, *arguments ):
		Element.__init__(self)
		assertImplements(self, IEvaluable)
		self._oparguments = []
		self.setOpArguments(arguments)

	def setOpArguments( self, arguments ):
		if not len(arguments) <= len(self.ARGS):
			raise ModelException("Too many arguments: %s expected %s, got %s" \
			% (self, len(self.ARGS), len(arguments)))
		self._oparguments = []
		map(self.addOpArgument, arguments)

	def addOpArgument( self, argument ):
		offset = len(self._oparguments)
		if offset > len(self.ARGS):
			raise ModelException("Too many arguments: %s expected args %s as %s, got %s" \
			% (self, offset, len(self.ARGS), offset + 1))
		if not self._isInstance(argument, self.ARGS[offset]):
			print argument, self.ARGS[offset]
			raise ModelException("Incompatible argument:  %s expected arg %s as  %s, got %s" \
			% (self, offset, self.ARGS[offset], argument))
		self._oparguments.append(argument)

	def getOpArguments( self ):
		"""Returns the arguments to this operation."""
		return self._oparguments
	
	def getOpArgument( self, i ):
		"""Returns the arguments with the given index."""
		return self._oparguments[i]

	def evaluate( self, context ):
		pass
		# TODO: Find how we process the operations to get a type

	@classmethod
	def getOperationName( self ):
		"""This is a simple shorthand to return the Operation class name."""
		return self.__name__

	@classmethod
	def getOpArgumentsInternalTypes( self ):
		"""Returns the *internal types* for this operations arguments. This is
		typically the list of interfaces or classes that the arguments must
		comply to."""

	@staticmethod
	def _isInstance( arg, argtype ):
		"""A more specific implementation of isinstance, that allows list of
		types to be used as types. For instance, `[ISlot]` stands for ''a
		list of arguments''."""
		if arg is None: return True
		if type(argtype) in (list, tuple):
			if not (type(arg) in (list, tuple)): return False
			for e in arg:
				if not isinstance(e, argtype[0]):
					return False
			return True
		else:
			return isinstance(arg, argtype)

class Instanciation(Operation, IInstanciation, IEvaluable):

	def getInstanciable( self ):
		"""Returns the instanciable used in this operation."""
		return self.getOpArgument(0)

class Assignation(Operation, IAssignation, IEvaluable):

	def getTargetReference( self ):
		"""Returns this assignation target."""
		return self.getOpArgument(0)

	def getAssignedValue( self ):
		"""Returns this assigned value."""
		return self.getOpArgument(1)

class Allocation(Operation, IAllocation, IEvaluable):

	def getSlotToAllocate( self ):
		"""Returns slot to be allocated by this operation."""
		return self.getOpArgument(0)

class Resolution(Operation, IResolution, IEvaluable):

	def getReference( self ):
		"""Returns the reference to be resolved."""
		return self.getOpArgument(0)

	def getContext( self ):
		"""Returns the reference to be resolved."""
		return self.getOpArgument(1)


class Computation(Operation, IComputation, IEvaluable):

	def getOperator( self ):
		"""Returns the reference to be resolved."""
		return self.getOpArgument(0)

	def getOperand( self ):
		return self.getLeftOperand()

	def getOperands( self ):
		return self.getLeftOperand(), self.getRightOperand()

	def getLeftOperand( self ):
		return self.getOpArgument(1)

	def getRightOperand( self ):
		return self.getOpArgument(2)

class Invocation(Operation, IInvocation, IEvaluable):

	def getTarget( self ):
		"""Returns the invocation target reference."""
		return self.getOpArgument(0)

	def getArguments( self ):
		"""Returns evaluable arguments."""
		return self.getOpArgument(1) or ()

# FIXME
class Termination(Operation, ITermination):

	def getReturnedEvaluable( self ):
		"""Returns the termination return evaluable."""
		return self.getOpArgument(0)

# ------------------------------------------------------------------------------
#
# VALUES
#
# ------------------------------------------------------------------------------

class Value(Element, IEvaluable):
	pass

class Litteral(Value, ILitteral):

	def __init__( self, actualValue ):
		Value.__init__(self)
		self._litteralValue = actualValue
		assertImplements(self, ILitteral)

	def getActualValue( self ):
		"""Returns the (python) value for this litteral."""
		return self._litteralValue

class Number(Litteral, INumber):
	pass

class String(Litteral, IString):
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

	def getTypeInformation( self ):
		return self._typeinfo

class Argument(Slot, IArgument):

	def __init__( self, refname, typeinfo ):
		Slot.__init__(self, refname, typeinfo)
		assertImplements(self, IArgument)

class Attribute(Slot, IAttribute):
	pass

class ClassAttribute(Slot, IClassAttribute):
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

	def createMethod( self, name, arguments=None ):
		return self._getImplementation("Method")(name, arguments)

	def createClassMethod( self, name, arguments=() ):
		return self._getImplementation("ClassMethod")(name, arguments)

	def createClass( self, name ):
		return self._getImplementation("Class")(name)

	def createModule( self, name ):
		return self._getImplementation("Module")(name)

	def allocate( self, slot ):
		return self._getImplementation("Allocation")(slot)

	def assign( self, name, evaluable ):
		return self._getImplementation("Assignation")(name, evaluable)

	def compute( self, operatorName, leftOperand, rightOperand=None ):
		return self._getImplementation("Computation")(operatorName, leftOperand, rightOperand)

	def invoke( self, evaluable, *arguments ):
		return self._getImplementation("Invocation")(evaluable, arguments)

	def resolve( self, reference, context=None ):
		return self._getImplementation("Resolution")(reference, context)

	def returns( self, evaluable ):
		return self._getImplementation("Termination")(evaluable)

	def comment( self, content ):
		return self._getImplementation("Comment")(content)

	def _ref( self, name ):
		return self._getImplementation("Reference")(name)

	def _slot( self, name, typeinfo=None ):
		return self._getImplementation("Slot")(name, typeinfo)

	def _arg( self, name, typeinfo=None ):
		return self._getImplementation("Argument")(name, typeinfo)

	def _attr( self, name, typeinfo=None):
		return self._getImplementation("Attribute")(name, typeinfo)

	def _clattr( self, name, typeinfo=None):
		return self._getImplementation("ClassAttribute")(name, typeinfo)

	def _op( self, symbol ):
		return self._getImplementation("Operator")(symbol)

	def _number( self, number ):
		return self._getImplementation("Number")(number)

	def _string( self, value ):
		return self._getImplementation("String")(value)

# EOF
