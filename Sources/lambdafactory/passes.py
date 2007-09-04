#8< ---[passes.py]---
import sys
__module__ = sys.modules[__name__]
import reporter
import interfaces
__module_name__ = 'passes'
class PassContext:
	"""The 'PassContext' represents the current state of one or more passes when
	walking the program. It offers access to the 'environment' (gives access
	to the program and various passes).
	
	A single context can be shared among various passes."""
	def __init__ (self, environment):
		self.environment = None
		self.context = []
		self.environment = environment
	
	def run(self):
		self.walk(self.environment.getProgram())
	
	def walk(self, element):
		self_1188932123_583=self.context
		self_1188932123_583.append(element)
		continue_walking=True
		for program_pass in self.environment.getPasses():
			handle=program_pass.getHandle(element)
			if handle:
				if (handle(self, element) != False):
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
		self_1188932123_5144=self.context
		self_1188932123_5144.pop()
	
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
	
	def isIn(self, interface):
		return (self.findInContext(interface) != None)
	
	def getCurrentClosure(self):
		return self.findInContext(interfaces.IClosure)
	
	def getCurrentFunction(self):
		return self.findInContext(interfaces.IFunction)
	
	def getCurrentMethod(self):
		return self.findInContext(interfaces.IMethod)
	
	def getCurrentClass(self):
		return self.findInContext(interfaces.IClass)
	
	def getCurrentProcess(self):
		return self.findInContext(interfaces.IProcess)
	
	def getCurrentClassParents(self, theClass):
		parents=[]
		if (theClass == None):
			theClass = self.getCurrentClass()
		current_class=theClass
		for parent_class_ref in current_class.getParentClasses():
			parent_class_name=parent_class_ref.getReferenceName()
			resolution=self.resolve(parent_class_name, current_class)
			target=resolution[0]
			context=resolution[1]
			parent_class = self.value
			self_1188932123_5212=parents
			self_1188932123_5212.append(parent_class)
	
	def resolve(self, referenceOrName, contextOrDataFlow=None):
		if contextOrDataFlow is None: contextOrDataFlow = None
		if (contextOrDataFlow == None):
			contextOrDataFlow = getCurrentContext().getDataFlow()
		elif isinstance(contextOrDataFlow, interfaces.IElement):
			contextOrDataFlow = contextOrDataFlow.getDataFlow()
		if isinstance(referenceOrName, interfaces.IReference):
			referenceOrName = referenceOrName.getReferenceName()
		return contextOrDataFlow.resolve(referenceOrName)
	

class Pass:
	HANDLES = []
	NAME = ""
	def __init__ (self):
		pass
	
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
					raise ERR_PASS_HANDLER_NOT_DEFINED(handler_name)
				return getattr(self, handler_name)
		return None
	

class ImportationPass(Pass):
	"""The importation pass will look for importation operations ('IImportation'),
	will try to resolve the importations (according to the current environment)
	and will trigger the loading and parsing of each module into the current
	program."""
	HANDLES = [interfaces.IModule]
	NAME = "Importation"
	def __init__ (self):
		Pass.__init__(self)
	
	def getModuleImportations(self, context, module):
		module_init=module.getSlot(interfaces.Constants.ModuleInit)
		return context.filter(module_init.getOperations(), interfaces.IImportOperation)
	
	def onModule(self, context, module):
		imports=self.getModuleImportations(context, module)
		for i in imports:
			if isinstance(i, interfaces.IImportModuleOperation):
				imported_module_name=i.getImportedModuleName()
				imported_module_origin=i.getAlias()
				imported=context.environment.importModule(imported_module_name)
			elif isinstance(i, interfaces.IImportSymbolOperation):
				imported_module_name=i.getImportOrigin()
				imported_module=context.environment.importModule(imported_module_name)
		return False
	

class TransformAsynchronousInvocations(Pass):
	HANDLES = [interfaces.IClosure]
	NAME = "AsynchronousInvocationsExpansion"

