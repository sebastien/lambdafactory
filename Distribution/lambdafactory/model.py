#!/usr/bin/env python
"""This module is the default implementation of the LambdaFactory interfaces.
It defines objects that allow you to build a complete OO program model on
which you can apply transformation passes, and from which you can generate
code using the different back-ends."""
import sys
__module__ = sys.modules[__name__]
from lambdafactory.interfaces import *
import pprint
import lambdafactory.modeltypes
__module_name__ = 'lambdafactory.model'
class DataFlowSlot(IDataFlowSlot):
	def __init__ (self, name, value, origin, slotType):
		self.name = None
		self.value = None
		self.origin = None
		self.abstractType = None
		self.slotType = None
		self.operations = []
		self.dataflow = None
		self.name = name
		self.value = value
		self.origin = origin
		self.slotType = slotType
	
	def setDataFlow(self, dataflow):
		self.dataflow = dataflow
	
	def getDataFlow(self):
		return self.dataflow
	
	def getName(self):
		return self.name
	
	def getValue(self):
		return self.value
	
	def getOrigin(self):
		return self.origin
	
	def getAbstractType(self):
		return self.abstractType
	
	def addOperation(self, operation):
		"""Adds an operation made to this dataflow slot."""
		self.operations.append(operation)
	
	def isImported(self):
		return (self.slotType == DataFlow.IMPORTED)
	
	def isLocal(self):
		return (self.slotType == DataFlow.LOCAL)
	
	def isArgument(self):
		return (self.slotType == DataFlow.ARGUMENT)
	
	def isEnvironment(self):
		return (self.slotType == DataFlow.ENVIRONMENT)
	
	def __repr__(self):
		return '<Slot("%s"=%s):%s@%s%s>' % (self.name, self.value, "TYPE", self.slotType, self.origin)
		
	

class DataFlow(IDataFlow):
	"""The DataFlow are ''dynamic contexts'' bound to the various program model
	elements. DataFlows are typically owned by elements which implement
	'IContext', and are linked together by rules defined in the 'Resolver'
	class.
	
	The dataflow bound to most expressions is the one of the enclosing closure
	(wether it is a function, or method. The dataflow of a method is bound to
	its parent class, which dataflow is also bound to the parent class dataflow.
	
	While 'DataFlow' and 'Context' may appear very similar, they are not the
	same: contexts are elements that keep track of declared slots, while the
	dataflow make use of the context to weave the elements togeher."""
	ARGUMENT = "Argument"
	ENVIRONMENT = "Environment"
	LOCAL = "Local"
	IMPORTED = "Imported"
	def __init__ (self, element, parent=None):
		self.program = None
		self.element = None
		self.parent = None
		self.sources = []
		self.destinations = []
		self.slots = []
		self.children = []
		if parent is None: parent = None
		self.element = element
		self.children = []
		if parent:
			self.setParent(parent)
		element.setDataFlow(self)
	
	def declareArgument(self, name, value):
		self._declare(name, value, None, self.__class__.ARGUMENT)
	
	def declareEnvironment(self, name, value):
		self._declare(name, value, None, self.__class__.ENVIRONMENT)
	
	def declareVariable(self, name, value, origin):
		self._declare(name, value, origin, self.__class__.LOCAL)
	
	def declareImported(self, name, value, origin):
		self._declare(name, value, origin, self.__class__.IMPORTED)
	
	def _declare(self, name, value, origin, slotType):
		"""Declares the given slot with the given name, value, origin
		and type. This is used internaly by the other 'declare' methods."""
		previous_slot=self.getSlot(name)
		if previous_slot:
			self.slots.remove(previous_slot)
		self.addSlot(DataFlowSlot(name, value, [origin], slotType))
	
	def addSource(self, dataflow):
		if (not (dataflow in self.sources)):
			self.sources.append(dataflow)
			dataflow.addDestination(self)
	
	def getSources(self):
		return self.sources
	
	def addDestination(self, dataflow):
		if (not (dataflow in self.destinations)):
			self.destinations.append(dataflow)
			dataflow.addSource(self)
	
	def getDestinations(self):
		return self.destinations
	
	def addSlot(self, slot):
		self.slots.append(slot)
		slot.setDataFlow(self)
	
	def getSlots(self):
		"""Returns the slots defiend for this dataflow."""
		return self.slots
	
	def _getAvailableSlots(self, slotList=None):
		if slotList is None: slotList = {}
		for slot in self.slots:
			if (not slotList.get(slot.getName())):
				slotList[slot.getName()] = slot
		if self.parent:
			self.parent._getAvailableSlots(slotList)
		return slotList
	
	def getAvailableSlots(self):
		return self._getAvailableSlots().values()
	
	def getSourcesSlots(self, slots=None):
		"""Returns the list of slots defined in the sources, using the sources axis."""
		if slots is None: slots = None
		if (slots == None):
			slots = {}
		elif True:
			for slot in self.getSlots():
				if (slots.get(slot.getName()) == None):
					slots[slot.getName()] = slot
		for source in self.getSources():
			source.getSourcesSlots(slots)
		return slots.values()
	
	def getAvailableSlotNames(self):
		return self._getAvailableSlots().keys()
	
	def hasSlot(self, name):
		for slot in self.slots:
			if (slot.getName() == name):
				return slot
		return False
	
	def getSlot(self, name):
		return self.hasSlot(name)
	
	def getElement(self):
		return self.element
	
	def getParent(self):
		return self.parent
	
	def getRoot(self):
		if self.parent:
			return self.parent.getRoot()
		elif True:
			return self
	
	def setParent(self, parent):
		assert(((self.parent == None) or (parent == self.parent)))
		if parent:
			self.parent = parent
			self.parent.addChild(self)
	
	def addChild(self, child):
		assert((not (child in self.children)))
		self.children.append(child)
	
	def getChildren(self):
		return self.children
	
	def resolveInSources(self, name):
		if self.sources:
			for source in self.getSources():
				slot_and_value=source.resolveLocally(name)
				if (slot_and_value[1] != None):
					return slot_and_value
				slot_and_value = source.resolveInSources(name)
				if (slot_and_value[1] != None):
					return slot_and_value
			return tuple([None, None])
		elif True:
			return tuple([None, None])
	
	def resolveLocally(self, name):
		slot=self.getSlot(name)
		if slot:
			return tuple([slot, slot.getValue()])
		elif True:
			return tuple([None, None])
	
	def resolve(self, name):
		"""Returns a couple '(DataFlow slot, IElement)' or '(None,None)'
		corresponding to the resolution of the given 'name' in this dataflow. The
		slot is the slot that holds the element, and the given element is the
		element value bound to the slot.
		
		The resolution scheme first looks into this datalfow, see if the slot
		is defined. It then looks in the sources, sequentially and if this fails,
		it will look into the parent.
		
		Alternative resolution schemes can be implemented depending on the target
		programming languages semantics, but this resolution operation should
		always be implemented in the same way. If you wish to have another
		way of doing resolution, you should provide a specific method in the
		DataFlow implementation, and also maybe provide more specific resolution
		operation in the 'PassContext' class."""
		slot=self.getSlot(name)
		if slot:
			return tuple([slot, slot.getValue()])
		if self.sources:
			slot_and_value=self.resolveInSources(name)
			if (slot_and_value[0] != None):
				return slot_and_value
		if self.parent:
			r=self.parent.resolve(name)
			if (r[0] != None):
				return r
		return tuple([None, None])
	
	def defines(self, name):
		slot=self.getSlot(name)
		if slot:
			return tuple([slot, self.element])
		elif True:
			for child in self.getChildren():
				res=child.defines(name)
				if res:
					return child
		return tuple([None, None])
	

class Element:
	"""The Element class is a generic class that implements many of the
	functionalities required to implement the full LambdaFactory program model.
	
	Property defined in this class may not be relevant to every subclass, but at
	least they provide a common infrastructure and limit the number of
	subclasses."""
	COUNT = 0
	def __init__ (self, name=None):
		self.id = None
		self.name = None
		self.source = None
		self.annotations = []
		self.abstractType = None
		self.resultAbtractType = None
		self.sourceLocation = [-1, -1, -1]
		self.dataflow = None
		self.parent = None
		if name is None: name = None
		self.name = name
		self.id = self.__class__.COUNT
		self.__class__.COUNT = (self.__class__.COUNT + 1)
	
	def setName(self, name):
		self.name = name
	
	def getName(self):
		assert((isinstance(self, IReferencable) or isinstance(self, IAnnotation)))
		return self.name
	
	def hasName(self):
		return (isinstance(self, IReferencable) or isinstance(self, IAnnotation))
	
	def getParent(self):
		return self.parent
	
	def hasParent(self):
		if self.parent:
			return self.parent
		elif True:
			return False
	
	def setParent(self, parent):
		assert(((self.parent == None) or (parent == self.parent)))
		self.parent = parent
	
	def detach(self):
		if self.parent:
			self.parent = None
		return self
	
	def setSource(self, source):
		self.source = source
	
	def getSource(self):
		return self.source
	
	def annotate(self, annotation):
		if (not annotation):
			return None
		if (type(annotation) in [tuple, list]):
			map(self.annotate , annotation)
		elif True:
			assert(isinstance(annotation, IAnnotation))
			self.annotations.append(annotation)
	
	def getAnnotations(self, withName):
		 return [a for a in self.annotations if a.getName() == withName]
		
	
	def getAnnotation(self, withName):
		annotations=self.getAnnotations(withName)
		if annotations:
			return annotations[0]
		elif True:
			return None
	
	def setDocumentation(self, documentation):
		self.annotate(documentation)
	
	def getDocumentation(self):
		return self.getAnnotation("documentation")
	
	def getDataFlow(self):
		return self.dataflow
	
	def setDataFlow(self, f):
		self.dataflow = f
	
	def hasDataFlow(self):
		return self.dataflow
	
	def ownsDataFlow(self):
		raise "Not implemented"
	
	def getAbstractType(self):
		if (self.abstractType == None):
			self.abstractType = modeltypes.typeForValue(self)
		return self.abstractType
	
	def setAbstractType(self, abstractType):
		self.abstractType = abstractType
	
	def getResultAbstractType(self):
		return self.resultAbtractType
	
	def setResultAbstractType(self, abstractType):
		self.resultAbtractType = abstractType
	
	def prettyList(self):
		return pprint.pprint(self.asList())
	
	def asList(self):
		return [self.__class__.__name__]
	
	def _copy(self, *arguments):
		copy=None
		copy = self.__class__(*arguments)
		
		copy.name = self.name
		copy.source = self.source
		for annotation in self.annotations:
			copy.annotate(annotation.copy().detach())
		copy.abstractType = self.abstractType
		copy.resultAbtractType = self.resultAbtractType
		copy.sourceLocation = self.sourceLocation
		if self.dataflow:
			copy.dataflow = self.dataflow.clone().attach(copy)
		return copy
	

class Annotation(Element, IAnnotation):
	def __init__ (self, name=None, content=None):
		self.content = None
		if name is None: name = None
		if content is None: content = None
		Element.__init__(self, name)
		self.name = name
		self.content = content
	
	def getContent(self):
		return self.content
	

class Comment(Annotation, IComment):
	def __init__ (self, content=None):
		if content is None: content = None
		Annotation.__init__(self, "comment", content)
	
	pass

class Documentation(Annotation, IDocumentation):
	def __init__ (self, content=None):
		if content is None: content = None
		Annotation.__init__(self, "documentation", content)
	
	pass

class Context(Element):
	def __init__ (self, name=None):
		self.slots = []
		self.parent = None
		self.abstract = False
		if name is None: name = None
		Element.__init__(self, name)
	
	def setAbstract(self, isAbstract):
		self.abstract = isAbstract
	
	def isAbstract(self):
		return self.abstract
	
	def setSlot(self, name, evaluable, assignParent=None):
		if assignParent is None: assignParent = True
		if (not isinstance(evaluable, IAssignable)):
			raise ERR_SLOT_VALUE_NOT_ASSIGNABLE
		if ((assignParent and isinstance(evaluable, IContext)) or hasattr(evaluable, "setParent")):
			evaluable.setParent(self)
		self.slots.append([name, evaluable])
	
	def hasSlot(self, name):
		for slot in self.slots:
			if (slot[0] == name):
				return True
		return False
	
	def getSlot(self, name):
		for slot in self.slots:
			if (slot[0] == name):
				return slot[1]
		raise ERR_SLOT_NOT_FOUND
	
	def getSlots(self):
		return self.slots
	
	def setParent(self, context):
		self.parent = context
	
	def getParent(self):
		return self.parent
	

class Class(Context, IClass, IReferencable, IAssignable):
	def __init__ (self, name=None, parentClasses=None):
		self.parentClasses = []
		if name is None: name = None
		if parentClasses is None: parentClasses = None
		Context.__init__(self, name)
		if (parentClasses != None):
			self.setParentClasses(parentClasses)
	
	def slotValuesImplementing(self, interface, without=None):
		if without is None: without = None
		res=[]
		for slot in self.getSlots():
			value=slot[1]
			if ((without == None) or (not isinstance(value, without))):
				if isinstance(value, interface):
					res.append(value)
		return res
	
	def getAttributes(self):
		return self.slotValuesImplementing(IAttribute, IClassAttribute)
	
	def getClassAttributes(self):
		return self.slotValuesImplementing(IClassAttribute)
	
	def getOperations(self):
		return self.slotValuesImplementing(IInvocable)
	
	def getConstructors(self):
		return self.slotValuesImplementing(IConstructor)
	
	def getDestructors(self):
		return self.slotValuesImplementing(IDestructor)
	
	def getMethods(self):
		return self.slotValuesImplementing(IMethod)
	
	def getInstanceMethods(self):
		return self.slotValuesImplementing(IInstanceMethod)
	
	def getClassMethods(self):
		return self.slotValuesImplementing(IClassMethod)
	
	def getParentClasses(self):
		return self.parentClasses
	
	def setParentClasses(self, classes):
		self.parentClasses = []
		for the_class in classes:
			if (not (isinstance(the_class, IReference) or isinstance(the_class, IResolution))):
				raise ERR_PARENT_CLASS_REFERENCE_EXPECTED
			self.parentClasses.append(the_class)
	
	def getInheritedLike(self, protocol):
		res = {}
		for slot in self.getDataFlow().getSourcesSlots():
			if isinstance(slot.getValue(), protocol):
				res[slot.getName()] = slot.getValue()
		return res
	
	def getInheritedClassMethods(self):
		"""Returns the inherited class methods as a dict of slots"""
		return self.getInheritedLike(IClassMethod)
	
	def getInheritedClassAttributes(self):
		return self.getInheritedLike(IClassAttribute)
	

class Interface(Class, IInterface):
	pass

class Module(Context, IModule, IAssignable, IReferencable):
	def __init__ (self, name=None):
		self.importOperations = []
		self.imported = False
		if name is None: name = None
		Context.__init__(self, name)
	
	def getParentName(self):
		"""Returns 'grandparentname.parentname'"""
		return (".".join(self.name.split(".")[0:-1]) or None)
	
	def getAbsoluteName(self):
		"""A module name is already absolute, so 'getAbsoluteName' is the same as
		'getName'"""
		return self.name
	
	def isImported(self):
		return self.imported
	
	def setImported(self, value=None):
		if value is None: value = True
		self.imported = value
	
	def addImportOperation(self, operation):
		self.importOperations.append(operation)
		operation.setParent(self)
	
	def getImportOperations(self):
		return self.importOperations
	
	def getClasses(self):
		 return [value for name, value in self.getSlots() if isinstance(value, IClass)]
		
	

class Program(Context, IProgram):
	def __init__ (self, name=None):
		self.factory = None
		self.modules = []
		if name is None: name = None
		Context.__init__(self, name)
	
	def addModule(self, module):
		if (module in self.modules):
			raise ERR_MODULE_ADDED_TWICE(module)
		self.modules.append(module)
		module.setParent(self)
	
	def getModule(self, moduleAbsoluteName):
		for module in self.modules:
			if (module.getName() == moduleAbsoluteName):
				return module
	
	def getModules(self):
		return self.modules
	
	def getModuleNames(self):
		res=[]
		for m in self.modules:
			res.append(m.getName())
		return res
	
	def setFactory(self, factory):
		"""Sets the factory that was used to create this program"""
		self.factory = factory
	
	def getFactory(self):
		"""Gets the factory that was used to create this program. It can be
		used to create more elements in the program."""
		return self.factory
	

class Process(Context, IContext, IProcess, IAbstractable):
	def __init__ (self, name=None):
		self.operations = []
		if name is None: name = None
		Context.__init__(self, name)
	
	def addOperation(self, operation):
		if self.isAbstract():
			raise ERR_ABSTRACT_PROCESS_NO_OPERATIONS
		operation.setParent(self)
		self.operations.append(operation)
	
	def getOperations(self):
		return self.operations
	
	def asList(self):
		res=[]
		for o in self.operations:
			res.append(o.asList())
		return tuple([self.__class__.__name__, tuple(self.operations)])
	

class Group(Process, IGroup):
	pass

class Block(Group, IBlock):
	pass

class Closure(Process, IAssignable, IClosure, IEvaluable):
	def __init__ (self, arguments, name=None):
		self.arguments = None
		if name is None: name = None
		Process.__init__(self, name)
		self.setArguments(arguments)
	
	def setArguments(self, arguments):
		self.arguments = []
		for argument in arguments:
			if (not isinstance(argument, ISlot)):
				raise ERR_CLOSURE_ARGUMENT_NOT_SLOT
			self.arguments.append(argument)
	
	def getArguments(self):
		return self.arguments
	
	def getArgument(self, index):
		return self.arguments[index]
	

class Function(Closure, IFunction, IReferencable):
	def __init__ (self, name, arguments):
		Closure.__init__(self, arguments, name)
	
	def getAbsoluteName(self):
		if self.getParent():
			return ((self.getParent().getAbsoluteName() + ".") + self.name)
		elif True:
			return self.name
	

class Method(Function, IMethod):
	pass

class Constructor(Method, IConstructor):
	def __init__ (self, arguments):
		Method.__init__(self, Constants.Constructor, arguments)
	
	pass

class Destructor(Method, IDestructor):
	def __init__ (self):
		Method.__init__(self, Constants.Destructor, [])
	
	pass

class ClassMethod(Method, IClassMethod):
	pass

class InstanceMethod(Method, IInstanceMethod):
	pass

class Operation(Element, IEvaluable, IOperation):
	ARGS = None
	def __init__ (self, *arguments):
		self.opArguments = []
		Element.__init__(self)
		self.setOpArguments(arguments)
	
	def copy(self):
		op_copy=None
		op_arguments=[]
		op_copy = Element._copy(self)
		for a in self.opArguments:
			op_copy.addOpArgument(a.copy().detach())
		return op_copy
	
	def setOpArguments(self, arguments):
		self.opArguments = []
		for a in arguments:
			self.addOpArgument(a)
	
	def setOpArgument(self, i, argument):
		while (len(self.opArguments) < i):
			self.opArguments.append(None)
		self.opArguments[i] = argument
	
	def addOpArgument(self, argument):
		self.opArguments.append(argument)
		self._setOpArgumentParent(argument)
	
	def _setOpArgumentParent(self, value):
		"""Sets the value parent to this"""
		if (type(value) in [tuple, list]):
			map(self._setOpArgumentParent , value)
		elif True:
			if isinstance(value, Element):
				value.setParent(self)
	
	def getOpArguments(self):
		return self.opArguments
	
	def getOpArgument(self, i):
		return self.opArguments[i]
	
	def asList(self):
		args=[]
		for a in self.opArguments:
			if (not (type(a) in [tuple, list])):
				if a:
					args.append(a.asList())
				elif True:
					args.append(a)
			elif True:
				args.append(a)
		return tuple([self.__class__.__name__, tuple(args)])
	

class Assignation(Operation, IAssignation, IEvaluable):
	def getTarget(self):
		return self.getOpArgument(0)
	
	def getAssignedValue(self):
		return self.getOpArgument(1)
	

class Allocation(Operation, IAllocation, IEvaluable):
	def getSlotToAllocate(self):
		return self.getOpArgument(0)
	
	def getDefaultValue(self):
		return self.getOpArgument(1)
	

class Resolution(Operation, IResolution, IEvaluable, IReferencable):
	def getReference(self):
		return self.getOpArgument(0)
	
	def getContext(self):
		return self.getOpArgument(1)
	

class Computation(Operation, IComputation, IEvaluable):
	def __init__ (self, *arguments):
		Operation.__init__(self, *arguments)
		
	
	pass

class Invocation(Operation, IInvocation, IEvaluable):
	def isByPositionOnly(self):
		for arg in self.getOpArgument(1):
			if (arg.isByName() or arg.isAsMap()):
				return False
		return True
	

class Instanciation(Operation, IInstanciation, IEvaluable):
	pass

class Selection(Operation, ISelection):
	def addRule(self, evaluable):
		res = self.getOpArguments()
		if (not res):
			res = []
			self.addOpArgument(res)
		elif True:
			res = res[0]
		res.append(evaluable)
		self._setOpArgumentParent(evaluable)
	
	def getRules(self):
		if self.opArguments:
			return self.getOpArgument(0)
		elif True:
			return []
	

class Evaluation(Operation, IEvaluation):
	pass

class AccessOperation(Operation, IAccessOperation):
	pass

class SliceOperation(Operation, ISliceOperation):
	pass

class MatchProcessOperation(Operation, IMatchProcessOperation):
	pass

class MatchExpressionOperation(Operation, IMatchExpressionOperation):
	pass

class Iteration(Operation, IIteration):
	pass

class Enumeration(Operation, IEnumeration):
	pass

class Repetition(Operation, IRepetition):
	pass

class Termination(Operation, ITermination):
	def getReturnedEvaluable(self):
		return self.getOpArgument(0)
	

class Breaking(Operation, IBreaking):
	pass

class Except(Operation, IExcept):
	pass

class Interception(Operation, IInterception):
	def __init__ (self, tryProcess, catchProcess=None, finallyProcess=None):
		if catchProcess is None: catchProcess = None
		if finallyProcess is None: finallyProcess = None
		Operation.__init__(self, tryProcess, catchProcess, finallyProcess)
	
	pass

class ImportOperation(Operation, IImportOperation):
	def __init__ (self, *arguments):
		Operation.__init__(self, *arguments)
		
	
	pass

class ImportSymbolOperation(Operation, IImportSymbolOperation):
	def __init__ (self, *arguments):
		Operation.__init__(self, *arguments)
		
	
	pass

class ImportSymbolsOperation(Operation, IImportSymbolsOperation):
	def __init__ (self, *arguments):
		Operation.__init__(self, *arguments)
		
	
	pass

class ImportModuleOperation(Operation, IImportModuleOperation):
	def __init__ (self, *arguments):
		Operation.__init__(self, *arguments)
		
	
	pass

class ImportModulesOperation(Operation, IImportModulesOperation):
	def __init__ (self, *arguments):
		Operation.__init__(self, *arguments)
		
	
	pass

class Embed(Operation, IEmbed):
	def __init__ (self, lang=None, code=None):
		self.language = None
		self.code = None
		if lang is None: lang = None
		if code is None: code = None
		Operation.__init__(self)
		self.language = lang
		self.code = code
	
	def getLanguage(self):
		return self.language
	
	def setLanguage(self, language):
		self.language = language
	
	def getCode(self):
		return self.code
	
	def setCode(self, code):
		self.code = code
	

class EmbedTemplate(Embed, IEmbedTemplate):
	pass

class Value(Element, IValue, IEvaluable, IAssignable):
	pass

class Literal(Value, ILiteral):
	def __init__ (self, actualValue):
		self.actualValue = None
		Value.__init__(self)
		self.actualValue = actualValue
	
	def getActualValue(self):
		return self.actualValue
	
	def copy(self):
		value_copy=Value._copy(self)
		value_copy.actualValue = self.actualValue
		return value_copy
	

class Number(Literal, INumber):
	pass

class String(Literal, IString):
	pass

class List(Value, IList):
	def __init__ (self):
		self.values = []
		Value.__init__(self)
	
	def addValue(self, value):
		self.values.append(value)
		value.setParent(self)
	
	def getValues(self):
		return self.values
	
	def getValue(self, i):
		return self.values[i]
	
	def copy(self):
		values_copy=[]
		list_copy=Value._copy(self)
		for v in self.values:
			list_copy.addValue(v.copy().detach())
		return list_copy
	

class Dict(Value, IDict):
	def __init__ (self):
		self.items = []
		Value.__init__(self)
	
	def setValue(self, key, value):
		self.items.append([key, value])
	
	def getItems(self):
		return self.items
	

class Reference(Value, IReference):
	def __init__ (self, name):
		self.referenceName = None
		Value.__init__(self)
		self.referenceName = name
	
	def getReferenceName(self):
		return self.referenceName
	
	def asList(self):
		return tuple([self.__class__.__name__, self.referenceName])
	
	def copy(self):
		ref_copy=Value._copy(self, self.name)
		ref_copy.referenceName = self.referenceName
		return ref_copy
	

class AbsoluteReference(Reference, IAbsoluteReference):
	def __init__ (self, name):
		self.referenceName = None
		Reference.__init__(self, name)
	
	pass

class Operator(Reference, IOperator):
	def __init__ (self, operator, priority):
		self.priority = 0
		Reference.__init__(self, operator)
		self.setPriority(priority)
	
	def getPriority(self):
		return self.priority
	
	def setPriority(self, priority):
		self.priority = priority
	

class Slot(Element, ISlot):
	def __init__ (self, name, typeDescription):
		self.defaultValue = None
		self.typeDescription = None
		Element.__init__(self, name)
		self.typeDescription = typeDescription
	
	def getTypeDescription(self):
		return self.typeDescription
	
	def setDefaultValue(self, value):
		self.defaultValue = value
	
	def getDefaultValue(self):
		return self.defaultValue
	

class Argument(Slot, IArgument):
	def __init__ (self, name, typeDescription):
		self.rest = False
		self.keywordRest = False
		self.optional = False
		Slot.__init__(self, name, typeDescription)
	
	def isOptional(self):
		return self.optional
	
	def setOptional(self, value):
		self.optional = (value and value)
	
	def isRest(self):
		return self.rest
	
	def setRest(self, value):
		self.rest = (value and value)
	
	def isKeywordsRest(self):
		return self.rest
	
	def setKeywordsRest(self, value):
		self.rest = (value and value)
	

class Parameter(Element, IParameter):
	def __init__ (self, name=None, value=None):
		self.name = None
		self.value = None
		self._asList = False
		self._asMap = False
		if name is None: name = None
		if value is None: value = None
		Element.__init__(self, name)
		self.name = name
		self.value = value
	
	def isByName(self):
		return (self.name != None)
	
	def getName(self):
		return self.name
	
	def setByName(self, n):
		self.name = n
	
	def getValue(self):
		return self.value
	
	def setValue(self, v):
		self.value = v
	
	def isAsList(self):
		return self._asList
	
	def isAsMap(self):
		return self._asMap
	
	def setAsList(self, v=None):
		if v is None: v = True
		self._asMap = False
		self._asList = True
	
	def setAsMap(self, v=None):
		if v is None: v = True
		self._asMap = True
		self._asList = False
	

class Attribute(Slot, IAttribute):
	def __init__ (self, name, typeDescription, value=None):
		if value is None: value = None
		Slot.__init__(self, name, typeDescription)
		self.setDefaultValue(value)
	
	pass

class ClassAttribute(Attribute, IClassAttribute):
	pass

class ModuleAttribute(Attribute, IModuleAttribute):
	pass

