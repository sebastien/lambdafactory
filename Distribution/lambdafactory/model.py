#!/usr/bin/env python
"""This module is the default implementation of the LambdaFactory interfaces.
It defines objects that allow you to build a complete OO program model on
which you can apply transformation passes, and from which you can generate
code using the different back-ends."""
import sys
__module__ = sys.modules[__name__]
from interfaces import *
import pprint
import modeltypes
__module_name__ = 'lambdafactory.model'
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
	
	def setSource(self, source):
		self.source = source
	
	def getSource(self):
		return self.source
	
	def annotate(self, annotation):
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
	def detach(self):
	    return self

	def copy(self):
	    return self
	


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
	
	def getInheritedClassMethods(self, resolver):
		"""Returns the inherited class methods as a dict of lists. This operation
		needs a resolver to resolve the classes from their references."""
		res={}
		for class_ref in self.getParentClasses():
			parent_name=class_ref.getReferenceName()
			slot_and_scope = self.getDataFlow().resolveAbsoluteOrLocal(parent_name)
			slot=slot_and_scope[0]
			scope=slot_and_scope[1]
			the_class=slot.getValue()
			for method in the_class.getClassMethods():
				self.name = method.getName()
				methods = res.setdefault(self.name, [])
				methods.append(method)
			for name_and_method in the_class.getInheritedClassMethods(resolver).items():
				meths = res.setdefault(name_and_method[0], [])
				meths.extend(name_and_method[1])
		return res
	
	def getInheritedClassAttributes(self, resolver):
		"""Returns the inherited class attributes as a dict of lists. This operation
		needs a resolver to resolve the classes from their references."""
		res={}
		for class_ref in self.getParentClasses():
			parent_name=class_ref.getReferenceName()
			slot_and_scope = self.getDataFlow().resolveAbsoluteOrLocal(parent_name)
			slot=slot_and_scope[0]
			scope=slot_and_scope[1]
			the_class=slot.getValue()
			for attr in the_class.getClassAttributes():
				self.name = attr.getName()
				attrs = res.setdefault(self.name, [])
				attrs.append(attr)
			for name_and_attrs in the_class.getInheritedClassAttributes(resolver).items():
				attrs = res.setdefault(name_and_attrs[0], [])
				attrs.extend(name_and_attrs[1])
		return res
	

class Interface(Class, IInterface):
	pass

class Module(Context, IModule, IAssignable, IReferencable):
	def __init__ (self, name=None):
		self.importOperations = []
		self.imported = False
		if name is None: name = None
		Context.__init__(self, name)
	
	def getParentName(self):
		return (".".join(self.name.split(".")[0:-1]) or None)
	
	def isImported(self):
		return self.imported
	
	def setImported(self, value=None):
		if value is None: value = True
		self.imported = value
	
	def addImportOperation(self, operation):
		self.importOperations.append(operation)
	
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
	
	def getModule(self, moduleAbsoluteName):
		for module in self.modules:
			if (module.getName() == moduleAbsoluteName):
				return module
	
	def getModules(self):
		return self.modules
	
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
	
	pass

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
	pass

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
	
	def getValues(self):
		return self.values
	
	def getValue(self, i):
		return self.values[i]
	

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
		self.optional = False
		self.keywords = False
		Slot.__init__(self, name, typeDescription)
	
	def isOptional(self):
		return self.optional
	
	def setOptional(self, value):
		self.optional = (value and value)
	
	def isRest(self):
		return self.rest
	
	def setRest(self, value):
		self.rest = (value and value)
	
	def isKeywords(self):
		return self.keywords
	
	def setKeywords(self, value):
		self.keywords = (value and value)
	

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

