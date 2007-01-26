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
# Last mod  : 06-Dec-2006
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
		self._annotations = []
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

	def setDocumentation( self, doc ):
		"""Sets the documentation for this element."""
		self.meta["doc"] = doc

	def hasDataFlow( self ):
		return hasattr(self, "_dataflow")

	def getDataFlow( self ):
		return self._dataflow

	def setDataFlow( self, df ):
		self._dataflow = df
	
	def annotate(self, annotation):
		self._annotations.append(annotation)
	
	def annotations(self, withName):
		return [a for a in self._annotations if a.getName() == withName]

class Annotation(IAnnotation):

	def __init__( self, name=None, content=None ):
		self._content = content
		self._name    = name

	def setContent( self, content ):
		self._content = content

	def getContent( self ):
		return self._content

	def getName(self):
		return self._name

class Comment(Annotation, IComment):

	def __init__( self, content ):
		Annotation.__init__(self, "comment", content)

class Documentation(Annotation, IDocumentation):

	def __init__( self, content ):
		Annotation.__init__(self, "doc", content)

# ------------------------------------------------------------------------------
#
# STRUCTURAL AND COMPILE/RUN TIME ELEMENTS
#
# ------------------------------------------------------------------------------

class Context(Element, IContext):

	def __init__( self, name=None ):
		Element.__init__(self, name=name)
		assertImplements(self, IContext)
		self._slots = []
		self._parent = None

	# FIXME: AssignParent is used when the value assigned to the
	# slot is "owned" by the slot (like methods in classes)
	def setSlot( self, name, evaluable, assignParent = True ):
		if not isinstance(evaluable, IAssignable):
			raise ModelBadArgument(self, IAssignable, evaluable)
		if assignParent and isinstance(evaluable, IContext):
			evaluable.setParent(self)
		self._slots.append([name, evaluable])

	def getSlot( self, name ):
		for sname, svalue in self._slots:
			if sname == name: return svalue
		raise Exception("Slot not found:" + name)

	def hasSlot( self, name ):
		return name in map(lambda x:x[0],self._slots)

	def getSlots( self ):
		return self._slots

	def setParent( self, context ):
		if self._parent != None:
			raise Exception("Context already assigned to a parent")
		self._parent = context

	def getParent( self ): 
		return self._parent

class Class(Context, IClass, IReferencable, IAssignable):

	def __init__( self, name=None, inherited=None ):
		Context.__init__(self, name=name)
		assertImplements(self, IClass)
		self.setSuperClasses(inherited)

	def getAttributes( self ):
		return [value for name,value in self.getSlots()
			if isinstance(value, IAttribute) and not isinstance(value, IClassAttribute)
		]

	def getClassAttributes( self ):
		return [value for name,value in self.getSlots()
			if isinstance(value, IClassAttribute)
		]

	def getOperations( self ):
		return [value for name, value in self.getSlots() if isinstance(value, IInvocable)]

	def getConstructors( self ):
		return [value for name, value in self.getSlots() if isinstance(value, IConstructor)]

	def getDestructors( self ):
		return [value for name, value in self.getSlots() if isinstance(value, IDestructor)]
		
	def getMethods( self ):
		return [value for name, value in self.getSlots() if isinstance(value, IMethod)]
	
	def getInstanceMethods( self ):
		return [value for name, value in self.getSlots() if isinstance(value, IInstanceMethod)]

	def getClassMethods( self ):
		return [value for name, value in self.getSlots() if isinstance(value, IClassMethod)]

	def getName( self ):
		return self._name
		
	def setSuperClasses( self, classes ) :
		self._inherited = []
		if not classes: return
		for cl in classes:
			assert isinstance(cl, IReference)
			self._inherited.append(cl)

	def getSuperClasses( self ):
		return self._inherited

class Module(Context, IModule, IAssignable, IReferencable):

	def __init__( self, name=None ):
		Context.__init__(self, name=name)
		assertImplements(self, IModule)

	def getClasses( self ):
		return [value for name, value in self.getSlots() if isinstance(value, IClass)]

	def getName( self ):
		return self._name

	def setName( self, name ):
		self._name = name
		
# ------------------------------------------------------------------------------
#
# PROCESSES
#
# ------------------------------------------------------------------------------

class Process( Context, IContext, IProcess ):

	def __init__(self, name=None ):
		Context.__init__(self, name)
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

class Block( Process, IBlock ):
	pass

class Closure(Process, IAssignable, IClosure, IEvaluable):

	def __init__(self, arguments, name=None ):
		Process.__init__(self, name=name)
		self._arguments = arguments
		assertImplements(self, IInvocable)
		assertImplements(self, IClosure)
		assertImplements(self, IEvaluable)

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

	def getId( self ):
		return self._id

class Function( Closure, IFunction, IReferencable ):

	def __init__(self, name, arguments ):
		Closure.__init__(self, arguments, name)
		self._arguments = arguments
		assertImplements(self, IFunction)
		assertImplements(self, IReferencable)

	def getName( self ):
		return self._name

class Method(Function, IMethod):
	pass

class Constructor(Method, IConstructor):

	def __init__(self, arguments ):
		Method.__init__(self, None, arguments)
		assertImplements(self, IConstructor)

	def getName( self ):
		return Constants.Constructor
	
class Destructor(Method, IDestructor):

	def __init__(self  ):
		Method.__init__(self, None, ())
		assertImplements(self, IDestructor)

	def getName( self ):
		return Constants.Destructor

class ClassMethod(Method, IClassMethod):
	pass


class InstanceMethod(Method, IInstanceMethod):
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

	def setOpArgument( self, i, argument ):
		if not i < len(self.ARGS):
			raise ModelException("Too many arguments: %s expected %s, got %s" \
			% (self, len(self.ARGS), len(arguments)))
		if not self._isInstance(argument, self.ARGS[i]):
			raise ModelException("Incompatible argument:  %s expected arg %s as  %s, got %s" \
			% (self, offset, self.ARGS[i], argument))
		while len(self._oparguments) < i: self._oparguments.append(None)
		self._oparguments[i] = argument

	def addOpArgument( self, argument ):
		offset = len(self._oparguments)
		if offset > len(self.ARGS):
			raise ModelException("Too many arguments: %s expected args %s as %s, got %s" \
			% (self, offset, len(self.ARGS), offset + 1))
		if not self._isInstance(argument, self.ARGS[offset]):
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


class Assignation(Operation, IAssignation, IEvaluable):

	def getTarget( self ):
		return self.getOpArgument(0)

	def getAssignedValue( self ):
		return self.getOpArgument(1)

class Allocation(Operation, IAllocation, IEvaluable):

	def getSlotToAllocate( self ):
		return self.getOpArgument(0)

	def getDefaultValue( self ):
		return self.getOpArgument(1)
		
class Resolution(Operation, IResolution, IEvaluable, IReferencable):

	def getReference( self ):
		return self.getOpArgument(0)

	def getContext( self ):
		return self.getOpArgument(1)

class Computation(Operation, IComputation, IEvaluable):

	def getOperator( self ):
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
	pass

class Instanciation(Operation, IInstanciation, IEvaluable):
	pass

class Selection(Operation, ISelection):

	def addRule( self, evaluable ):
		res = self.getOpArguments()
		if not res:
			res = []
			self.addOpArgument(res)
		else:
			res = res[0]
		res.append(evaluable)

	def getRules( self ):
		return self.getOpArgument(0)

class Evaluation( Operation, IEvaluation ):
	pass

class SliceOperation(Operation, ISliceOperation):
	pass

class MatchOperation(Operation, IMatchOperation):
	pass

class Iteration( Operation, IIteration ):
	pass

class Enumeration(Operation, IEnumeration):
	pass

class Repetition(Operation, IRepetition):
	pass

class Termination(Operation, ITermination):

	def getReturnedEvaluable( self ):
		return self.getOpArgument(0)

# ------------------------------------------------------------------------------
#
# VALUES
#
# ------------------------------------------------------------------------------

class Value(Element, IValue, IEvaluable, IAssignable):
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

class List(Value, IList):
	def __init__(self):
		Value.__init__(self)
		assertImplements(self, IList)
		self._values = []

	def addValue( self, value ):
		assertImplements(value, IEvaluable)
		self._values.append(value)

	def getValues( self ):
		return self._values

class Dict(Value, IDict):

	def __init__(self):
		Value.__init__(self)
		assertImplements(self, IDict)
		self._values = []

	def setValue( self, key, value ):
		self._values.append([key,value])

	def getItems( self ):
		return self._values

class Reference(Value, IReference):

	def __init__( self, refname ):
		Value.__init__(self)
		assert type(refname) in (str, unicode), "Expected string: " +repr(refname)
		self._refname = refname
		assertImplements(self, IReference)

	def getName( self ):
		return self._refname

	def getReferenceName( self ):
		return self._refname

class Operator(Reference, IOperator):
	pass

class Slot(Reference, ISlot ):

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

	def __init__( self, refname, typeinfo, value=None ):
		Slot.__init__(self, refname, typeinfo)
		assertImplements(self, IAttribute)
		self._defaultValue = value
		
	def setDefaultValue(self, value ):
		self._defaultValue = value

	def getDefaultValue(self):
		return self._defaultValue

class ClassAttribute(Attribute, IClassAttribute):
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

	MainFunction  = Constants.MainFunction
	CurrentModule = Constants.CurrentModule
	Constructor   = Constants.Constructor
	Destructor    = Constants.Destructor
	ModuleInit    = Constants.ModuleInit
	CurrentValue  = Constants.CurrentValue
	
	def __init__( self, module ):
		self._module = module

	def _getImplementation( self, name ):
		if not hasattr(self._module, name ):
			raise ModelException("Module %s does not implement: %s" % \
			(self._module, name))
		else:
			return getattr(self._module, name)

	def createBlock( self ):
		return self._getImplementation("Block")()

	def createClosure( self, arguments ):
		return self._getImplementation("Closure")(arguments)

	def createFunction( self, name, arguments ):
		return self._getImplementation("Function")(name, arguments)

	def createMethod( self, name, arguments=None ):
		return self._getImplementation("InstanceMethod")(name, arguments)

	def createConstructor( self, arguments=None ):
		return self._getImplementation("Constructor")(arguments)

	def createDestructor( self ):
		return self._getImplementation("Destructor")()

	def createClassMethod( self, name, arguments=() ):
		return self._getImplementation("ClassMethod")(name, arguments)

	def createClass( self, name, inherited=() ):
		return self._getImplementation("Class")(name, inherited)

	def createModule( self, name ):
		return self._getImplementation("Module")(name)

	def evaluate( self, evaluable ):
		return self._getImplementation("Evaluation")(evaluable)

	def allocate( self, slot, value=None ):
		return self._getImplementation("Allocation")(slot, value)

	def assign( self, name, evaluable ):
		return self._getImplementation("Assignation")(name, evaluable)

	def compute( self, operatorName, leftOperand, rightOperand=None ):
		return self._getImplementation("Computation")(operatorName, leftOperand, rightOperand)

	def invoke( self, evaluable, *arguments ):
		return self._getImplementation("Invocation")(evaluable, arguments)

	def instanciate( self, evaluable, *arguments ):
		return self._getImplementation("Instanciation")(evaluable, arguments)

	def resolve( self, reference, context=None ):
		return self._getImplementation("Resolution")(reference, context)

	def select( self ):
		return self._getImplementation("Selection")()

	def match( self, evaluable, process ):
		return self._getImplementation("MatchOperation")(evaluable, process)

	def iterate( self, evaluable, process ):
		return self._getImplementation("Iteration")(evaluable, process)

	def repeat( self, condition, process ):
		return self._getImplementation("Repetition")(condition, process)

	def slice( self, target, _slice ):
		return self._getImplementation("SliceOperation")(target, _slice)

	def enumerate( self, start, end, step=None ):
		return self._getImplementation("Enumeration")(start, end, step)

	def returns( self, evaluable ):
		return self._getImplementation("Termination")(evaluable)

	def comment( self, content ):
		return self._getImplementation("Comment")(content)
	
	def doc( self, content ):
		return self._getImplementation("Documentation")(content)
	
	def annotation( self, name, content ):
		return self._getImplementation("Annotation")(name, content)
	
	def _ref( self, name ):
		return self._getImplementation("Reference")(name)

	def _slot( self, name, typeinfo=None ):
		return self._getImplementation("Slot")(name, typeinfo)

	def _arg( self, name, typeinfo=None ):
		return self._getImplementation("Argument")(name, typeinfo)

	def _attr( self, name, typeinfo=None, value=None):
		return self._getImplementation("Attribute")(name, typeinfo, value)

	def _classattr( self, name, typeinfo=None, value=None):
		return self._getImplementation("ClassAttribute")(name, typeinfo, value)

	def _op( self, symbol ):
		return self._getImplementation("Operator")(symbol)

	def _number( self, number ):
		return self._getImplementation("Number")(number)

	def _string( self, value ):
		return self._getImplementation("String")(value)

	def _list( self, *args ):
		r = self._getImplementation("List")()
		map(lambda a:r.addValue(a), args)
		return r

	def _dict( self ):
		return self._getImplementation("Dict")()

# EOF
