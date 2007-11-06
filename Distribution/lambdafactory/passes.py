#!/usr/bin/env python
import sys
__module__ = sys.modules[__name__]
import lambdafactory.reporter as reporter
import lambdafactory.interfaces as interfaces
__module_name__ = 'lambdafactory.passes'
class PassContext:
	"""The 'PassContext' represents the current state of one or more passes when
	walking the program. It offers access to the 'environment' (gives access
	to the program and various passes).
	
	A single context can be shared among various passes."""
	def __init__ (self, environment=None, programPass=None):
		self.environment = None
		self.context = []
		self.programPass = None
		if environment is None: environment = None
		if programPass is None: programPass = None
		self.environment = environment
		self.programPass = programPass
	
	def setEnvironment(self, environment):
		self.environment = environment
	
	def setPass(self, programPass):
		self.programPass = programPass
	
	def run(self):
		self.walk(self.environment.getProgram())
	
	def handle(self, element):
		"""Handles a sungle element, without recursing through its children"""
		handle=self.programPass.getHandle(element)
		if handle:
			return handle(element)
		elif True:
			return None
	
	def walk(self, element):
		"""Walks the given element, recursively walking the child elements when the
		handler does not return False"""
		self.context.append(element)
		continue_walking=True
		handle=self.programPass.getHandle(element)
		if handle:
			if (handle(element) != False):
				continue_walking = True
		if (continue_walking != False):
			if isinstance(element, interfaces.IProgram):
				for module in element.getModules():
					self.walk(module)
			if isinstance(element, interfaces.IContext):
				for name_and_value in element.getSlots():
					self.walk(name_and_value[1])
			if isinstance(element, interfaces.IProcess):
				for operation in element.getOperations():
					self.walk(operation)
			if isinstance(element, interfaces.IOperation):
				for op_arg in element.getOpArguments():
					if (type(op_arg) in [tuple, list]):
						for arg in op_arg:
							assert(isinstance(arg, interfaces.IElement))
							self.walk(arg)
					elif True:
						self.walk(op_arg)
		self.context.pop()
	
	def filterContext(self, interface):
		return filter(lambda x:isinstance(x,interface), self.context) 
		
	
	def filter(self, list, interface):
		return filter(lambda x:isinstance(x,interface), list) 
		
	
	def findInContext(self, interface):
		res=self.filterContext(interface)
		if res:
			return res[-1]
		elif True:
			return None
	
	def getParentElement(self):
		return self.context[-2]
	
	def hasParentElement(self):
		return (len(self.context) > 1)
	
	def getCurrentElement(self):
		return self.context[-1]
	
	def getProgram(self):
		return self.environment.getProgram()
	
	def getFactory(self):
		return self.environment.getFactory()
	
	def isIn(self, interface):
		return (self.findInContext(interface) != None)
	
	def getCurrentClosure(self):
		return self.findInContext(interfaces.IClosure)
	
	def getCurrentFunction(self):
		return self.findInContext(interfaces.IFunction)
	
	def getCurrentModule(self):
		return self.findInContext(interfaces.IModule)
	
	def getCurrentDataFlow(self):
		i=(len(self.context) - 1)
		while (i >= 0):
			dataflow=self.context[i].getDataFlow()
			if dataflow:
				return dataflow
			i = (i - 1)
		return None
	
	def getCurrentMethod(self):
		return self.findInContext(interfaces.IMethod)
	
	def getCurrentContext(self):
		return self.findInContext(interfaces.IContext)
	
	def getCurrentClass(self):
		return self.findInContext(interfaces.IClass)
	
	def getCurrentProcess(self):
		return self.findInContext(interfaces.IProcess)
	
	def getCurrentClassParents(self, theClass):
		parents=[]
		if (theClass == None):
			theClass = self.getCurrentClass()
		if (not theClass):
			return tuple([])
		current_class=theClass
		for parent_class_ref in current_class.getParentClasses():
			parent_class_name=parent_class_ref.getReferenceName()
			resolution=self.resolve(parent_class_name, current_class)
			slot=resolution[0]
			parent_class=resolution[1]
			if parent_class:
				parents.append(parent_class)
			elif True:
				self.environment.report.error("Unable to resolve parent class:", parent_class_name, "from", current_class.getName())
		return parents
	
	def getCurrentClassAncestors(self, theClass=None):
		if theClass is None: theClass = None
		ancestors=[]
		if (theClass == None):
			theClass = self.getCurrentClass()
		if (not theClass):
			return tuple([])
		parents=self.getCurrentClassParents(theClass)
		for parent in parents:
			if (not (parent in ancestors)):
				for ancestor in self.getCurrentClassAncestors(parent):
					if (not (ancestor in ancestors)):
						ancestors.append(ancestor)
		ancestors.extend(parents)
		return ancestors
	
	def resolve(self, referenceOrName, contextOrDataFlow=None):
		"""Resolves the given 'IReference' or String sing the given context
		('IContext') or dataflow ('IDataFlow'). This usually requires that
		you've applied a pass to create the dataflow (see the
		'lambdafactory.resolution.BasicDataFlow' pass)."""
		if contextOrDataFlow is None: contextOrDataFlow = None
		if (contextOrDataFlow == None):
			contextOrDataFlow = self.getCurrentDataFlow()
		elif isinstance(contextOrDataFlow, interfaces.IElement):
			contextOrDataFlow = contextOrDataFlow.getDataFlow()
		if isinstance(referenceOrName, interfaces.IReference):
			referenceOrName = referenceOrName.getReferenceName()
		return contextOrDataFlow.resolve(referenceOrName)
	
	def resolveAbsolute(self, referenceOrName):
		"""Resolves the given reference or string expressed in absolute style
		('.'-separated list of names), starting from the root dataflow (the program
		dataflow)."""
		program=self.getProgram()
		program_dataflow=program.getDataFlow()
		slot_and_value=None
		matching_module=None
		if (not program_dataflow):
			raise ERR_NO_DATAFLOW_AVAILABLE
		if isinstance(referenceOrName, interfaces.IReference):
			referenceOrName = referenceOrName.getReferenceName()
		for module in program.getModules():
			mname=module.getName()
			mname_len=len(mname)
			if (mname == referenceOrName):
				matching_module = module
				return tuple([None, module])
			match_index=mname.find(referenceOrName)
			if ((match_index == 0) and (referenceOrName[mname_len] == ".")):
				if (not matching_module):
					matching_module = module
				elif (len(module.getName()) > len(matching_module.getName())):
					matching_module = module
		if (not matching_module):
			return tuple([None, None])
		elif True:
			symbol_name=referenceOrName
			slot_and_value = current_dataflow.resolve(ref_name)
			if (not slot_and_value[1]):
				return slot_and_value
			elif True:
				current_dataflow = slot_and_value[0].getDataFlow()
		return slot_and_value
	
	def resolveAbsoluteOrLocal(self, referenceOrName, contextOrDataFlow=None):
		"""Tries an absolute resolution first, then will look in the local scope if
		it fails."""
		if contextOrDataFlow is None: contextOrDataFlow = None
		slot_and_value=self.resolveAbsolute(referenceOrName)
		if (not slot_and_value[0]):
			return self.resolve(referenceOrName, contextOrDataFlow)
		elif True:
			return slot_and_value
	
	def resolveLocalOrAbsolute(self, referenceOrName, contextOrDataFlow=None):
		"""Tries a local resolution first, then will look in the program scope if
		it fails."""
		if contextOrDataFlow is None: contextOrDataFlow = None
		slot_and_value=self.resolve(referenceOrName, contextOrDataFlow)
		if (not slot_and_value[0]):
			return self.resolveAbsolute(referenceOrName)
		elif True:
			return slot_and_value
	

class Pass(PassContext):
	HANDLES = []
	NAME = ""
	def __init__ (self):
		PassContext.__init__(self)
		self.setPass(self)
	
	def getHandle(self, element):
		"""Tells if the pass handles the given element. This basically iterates
		on the 'handles' property values (which are interfaces), when one
		interface matches the given 'element', then the corresponding 'onXXX'
		method is invoked, where 'XXX' is the interface
		name (without the leading 'I')."""
		for interface in self.__class__.HANDLES:
			if isinstance(element, interface):
				handler_name=("on" + interface.__name__[1:])
				if (not hasattr(self, handler_name)):
					self.environment.report.error("Handler does not define pass for:", handler_name)
					raise ERR_PASS_HANDLER_NOT_DEFINED(handler_name)
				return getattr(self, handler_name)
		return None
	
	def getName(self):
		"""Returns the name of this pass"""
		return self.__class__.NAME
	

class ImportationPass(Pass):
	"""The importation pass will look for importation operations ('IImportation'),
	will try to resolve the importations (according to the current environment)
	and will trigger the loading and parsing of each module into the current
	program."""
	HANDLES = [interfaces.IModule]
	NAME = "Importation"
	def __init__ (self):
		Pass.__init__(self)
	
	def onModule(self, module):
		imports=module.getImportOperations()
		for i in imports:
			if isinstance(i, interfaces.IImportModuleOperation):
				imported_module_name=i.getImportedModuleName()
				imported_module_origin=i.getAlias()
				imported_module=self.environment.importModule(imported_module_name)
			elif isinstance(i, interfaces.IImportSymbolOperation):
				imported_module_name=i.getImportOrigin()
				imported_module=self.environment.importModule(imported_module_name)
			elif isinstance(i, interfaces.IImportSymbolsOperation):
				imported_module_name=i.getImportOrigin()
				imported_module=self.environment.importModule(imported_module_name)
			elif True:
				self.environment.report.error(("ImportationPass: operation not implemented " + repr(i)))
		return False
	

class DocumentationPass(Pass):
	"""The documentation pass will run SDoc on all the modules declared in this
	program, creating an HTML file."""
	HANDLES = [interfaces.IModule]
	NAME = "Documentation"
	def __init__ (self, args=None):
		self.sdocArguments = None
		self.sdocDocumenter = None
		if args is None: args = []
		Pass.__init__(self)
		self.sdocArguments = args
		import sdoc.main
		self.sdocDocumenter = sdoc.main.LambdaFactoryDocumenter()
		
	
	def onModule(self, module):
		self.sdocDocumenter.documentModule(module)
	
	def asHTML(self, title=None):
		"""Returns the HTML document generated by this pass"""
		if title is None: title = None
		return self.sdocDocumenter.toHTML(title)
	

class TransformAsynchronousInvocations(Pass):
	HANDLES = [interfaces.IClosure]
	NAME = "AsynchronousInvocationsExpansion"

