#8< ---[lambdafactory/passes.py]---
#!/usr/bin/env python
import sys
__module__ = sys.modules[__name__]
import lambdafactory.reporter as reporter
import lambdafactory.interfaces as interfaces
import json
__module_name__ = 'lambdafactory.passes'
ERR_NO_DATAFLOW_AVAILABLE = 'ERR_NO_DATAFLOW_AVAILABLE'
ERR_PASS_HANDLER_NOT_DEFINED = 'ERR_PASS_HANDLER_NOT_DEFINED'
class PassContext:
	"""The 'PassContext' represents the current state of one or more passes when
	walking the program. It offers access to the 'environment' (gives access
	to the program and various passes) but more importantly gives access
	to _dataflow-related primitives_ which allow you to resolve symbols
	an interrogate contexts.
	
	NOTE that a single pass context can be shared among various passes."""
	def __init__ (self, environment=None, programPass=None):
		self.environment = None
		self.context = []
		self.programPass = None
		self.program = None
		self.cache = {}
		if environment is None: environment = None
		if programPass is None: programPass = None
		self.environment = environment
		self.programPass = programPass
		if environment:
			self.program = environment.program
	
	def setEnvironment(self, environment):
		self.environment = environment
	
	def setPass(self, programPass):
		self.programPass = programPass
	
	def run(self, program):
		assert((self.program == None))
		self.program = program
		self.walk(program)
		self.program = None
	
	def handle(self, element):
		"""Handles a sungle element, without recursing through its children"""
		handle=self.programPass.getHandler(element)
		if handle:
			return handle(element)
		elif True:
			return None
	
	def walk(self, element):
		"""Walks the given element, recursively walking the child elements when the
		handler does not return False"""
		self.pushContext(element)
		continue_walking=True
		handle=self.programPass.getHandler(element)
		if handle:
			if (handle(element) != False):
				continue_walking = True
		if (continue_walking != False):
			self.walkChildren(element)
		self.popContext()
	
	def walkChildren(self, element):
		"""Walks the children of the given element"""
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
						assert(isinstance(arg, interfaces.IElement), 'Element expected, got {0}'.format(arg))
						self.walk(arg)
				elif True:
					self.walk(op_arg)
		if isinstance(element, interfaces.IList):
			for v in element.getValues():
				self.walk(v)
		if isinstance(element, interfaces.IDict):
			for v in element.getItems():
				self.walk(v[0])
				self.walk(v[1])
		if isinstance(element, interfaces.IArgument):
			self.walk(element.getValue())
	
	def pushContext(self, value):
		self.context.append(value)
	
	def popContext(self):
		self.context.pop()
	
	def filterContext(self, interface):
		return [_ for _ in self.context if isinstance(_,interface)]
		
	
	def filter(self, list, interface):
		return [_ for _ in list if isinstance(_,interface)]
		
	
	def findInContext(self, interface):
		res=self.filterContext(interface)
		if res:
			return res[-1]
		elif True:
			return None
	
	def indexInContext(self, value):
		for i,e in enumerate(self.context):
			if e is value:
				return i
		
		return -1
	
	def indexLikeInContext(self, interface):
		for i,e in enumerate(self.context):
			if isinstance(e,interface):
				return i
		
		return -1
	
	def lastIndexInContext(self, interface):
		i=(len(self.context) - 1)
		while (i >= 0):
			v=self.context[i]
			if isinstance(v, interface):
				return i
			i = (i - 1)
		return -1
	
	def getParentElement(self):
		return self.context[-2]
	
	def hasParentElement(self):
		return (len(self.context) > 1)
	
	def getCurrentElement(self):
		return self.context[-1]
	
	def getProgram(self):
		return self.program
	
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
	
	def getScopeName(self, limit=None):
		if limit is None: limit = -1
		r=[]
		for _ in self.context[0:limit]:
			if isinstance(_, interfaces.IReferencable):
				n=_.getName()
				if n:
					r.append(_.getName())
		return '.'.join(r)
	
	def getCurrentDataFlow(self):
		i=(len(self.context) - 1)
		while (i >= 0):
			dataflow=self.context[i].getDataFlow()
			if dataflow:
				return dataflow
			i = (i - 1)
		return None
	
	def getCurrentName(self, index=None):
		if index is None: index = 0
		i=((len(self.context) - 1) + index)
		while (i >= 0):
			c=self.context[i]
			if isinstance(c, interfaces.IReferencable):
				n=c.getName()
				if n:
					return n
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
	
	def getCurrentClassParents(self):
		return self.getClassParents(self.getCurrentClass())
	
	def getClassParents(self, theClass):
		parents=[]
		if (not theClass):
			return tuple([])
		current_class=theClass
		assert(isinstance(theClass, interfaces.IClass))
		for parent_class_ref in current_class.getParentClassesRefs():
			parent_class_name=parent_class_ref.getReferenceName()
			resolution=self.resolve(parent_class_name, current_class.getDataFlow().parent)
			if (resolution[1] == theClass):
				module=theClass.getParent()
				imported=module.getAnnotation('imported')
				if imported:
					resolution = [None, imported.content.get(parent_class_name)]
			elif (not resolution[1]):
				resolution = self.resolveAbsolute(parent_class_name)
			parent_class=resolution
			slot=parent_class[0]
			parent_class = parent_class[1]
			if parent_class:
				assert(isinstance(parent_class, interfaces.IClass))
				parents.append(parent_class)
			elif True:
				parents.append(parent_class_ref)
				self.environment.report.error('Unable to resolve parent class:', parent_class_name, 'from', current_class.getName())
		return parents
	
	def getCurrentClassAncestors(self):
		return self.getClassAncestors(self.getCurrentClass())
	
	def getClassAncestors(self, theClass=None):
		if theClass is None: theClass = None
		ancestors=[]
		if (not theClass):
			return tuple([])
		assert(isinstance(theClass, interfaces.IClass))
		parents=self.getClassParents(theClass)
		for parent in parents:
			if isinstance(parent, interfaces.IReference):
				self.environment.report.error('Cannot resolve reference to class', parent.getReferenceName())
				pass
			elif (not (parent in ancestors)):
				for ancestor in self.getClassAncestors(parent):
					if (not (ancestor in ancestors)):
						ancestors.append(ancestor)
		ancestors.extend(parents)
		return ancestors
	
	def annotate(self, value, name, content=None):
		if content is None: content = None
		value.addAnnotation(self.environment.factory.annotation(name, content))
	
	def resolve(self, referenceOrName, contextOrDataFlow=None):
		"""Resolves the given 'IReference' or String sing the given context
		('IContext') or dataflow ('IDataFlow'). This usually requires that
		you've applied a pass to create the dataflow (see the
		'lambdafactory.resolution.BasicDataFlow' pass)."""
		if contextOrDataFlow is None: contextOrDataFlow = None
		if (contextOrDataFlow is None):
			contextOrDataFlow = self.getCurrentDataFlow()
		elif isinstance(contextOrDataFlow, interfaces.IElement):
			contextOrDataFlow = contextOrDataFlow.getDataFlow()
		if isinstance(referenceOrName, interfaces.IReference):
			referenceOrName = referenceOrName.getReferenceName()
		if contextOrDataFlow:
			return contextOrDataFlow.resolve(referenceOrName)
		elif True:
			return [None, None]
	
	def resolveAbsolute(self, referenceOrName):
		"""Resolves the given reference or string expressed in absolute style
		('.'-separated list of names), starting from the root dataflow (the program
		dataflow)."""
		program=self.getProgram()
		assert(program)
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
			match_index=referenceOrName.find(mname)
			if (((match_index == 0) and referenceOrName.startswith(mname)) and (referenceOrName[mname_len] == '.')):
				if (not matching_module):
					matching_module = module
				elif (len(module.getName()) > len(matching_module.getName())):
					matching_module = module
		if (not matching_module):
			return tuple([None, None])
		elif True:
			symbol_name=referenceOrName[(len(matching_module.getName()) + 1):]
			slot_and_value = matching_module.getDataFlow().resolve(symbol_name)
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
	NAME = ''
	def __init__ (self):
		self.options = {}
		PassContext.__init__(self)
		self.setPass(self)
	
	def getHandler(self, element):
		"""Tells if the pass handles the given element. This basically iterates
		on the 'handles' property values (which are interfaces), when one
		interface matches the given 'element', then the corresponding 'onXXX'
		method is invoked, where 'XXX' is the interface
		name (without the leading 'I')."""
		for interface in self.__class__.HANDLES:
			if isinstance(element, interface):
				handler_name=('on' + interface.__name__[1:])
				if (not hasattr(self, handler_name)):
					self.environment.report.error('Handler does not define pass for:', handler_name)
					raise ERR_PASS_HANDLER_NOT_DEFINED(handler_name)
				return getattr(self, handler_name)
		return None
	
	def getName(self):
		"""Returns the name of this pass"""
		return self.__class__.NAME
	

class ExtendJSRuntime(Pass):
	"""This pass is like an importation and will simply bind the symbols"""
	HANDLES = [interfaces.IProgram, interfaces.IModule]
	NAME = 'GlobalRuntime'
	FUNCTIONS = ['access', 'add', 'asMap', 'assert', 'bool', 'capitalize', 'car', 'cdr', 'cmp', 'copy', 'debug', 'difference', 'equals', 'equals', 'error', 'exception', 'fail', 'filter', 'find', 'findLike', 'findOneOf', 'first', 'foldl', 'greater', 'insert', 'intersection', 'isDefined', 'isFunction', 'isIn', 'isInstance', 'isIterable', 'isList', 'isMap', 'isNumber', 'isObject', 'isString', 'isUndefined', 'items', 'itemsAsMap', 'iterate', 'json', 'keys', 'last', 'list', 'len', 'lower', 'map', 'map0', 'map1', 'map2', 'map3', 'merge', 'module', 'offset', 'pairs', 'print', 'range', 'reduce', 'remove', 'removeAt', 'replace', 'require', 'reverse', 'slice', 'smaller', 'sorted', 'sprintf', 'str', 'strip', 'type', 'union', 'unjson', 'upper', 'values', 'warning', 'words', 'xor']
	def __init__ (self):
		self.runtime = None
		Pass.__init__(self)
	
	def onProgram(self, program):
		self.runtime = self.environment.factory.createModule('extend')
		self.runtime.addAnnotation(self.environment.factory.annotation('shadow'))
		for f in self.__class__.FUNCTIONS:
			fun=self.environment.factory.createFunction(f)
			fun.addAnnotation(self.environment.factory.annotation('shadow'))
			self.runtime.setSlot(f, fun)
		program.addModule(self.runtime, 0)
	
	def onModule(self, module):
		imports=module.getImportOperations()
		assert self.runtime, "No runtime defined in ExtendJSRuntime pass"
		
		module.addImportOperation(self.environment.factory.importSymbols(self.runtime.getSlotNames(), self.runtime.getAbsoluteName()), 0)
		return False
	

class Importation(Pass):
	"""The importation pass will look for importation operations ('IImportation'),
	will try to resolve the importations (according to the current environment)
	and will trigger the loading and parsing of each module into the current
	program."""
	HANDLES = [interfaces.IModule]
	NAME = 'Importation'
	def __init__ (self):
		Pass.__init__(self)
	
	def onModule(self, module):
		imports=module.getImportOperations()
		for i in imports:
			imported_modules=[]
			if isinstance(i, interfaces.IImportModuleOperation):
				imported_module_name=i.getImportedModuleName()
				imported_module_origin=i.getAlias()
				if (not self.program.hasModuleWithName(imported_module_name)):
					imported_modules.append(self.environment.importModule(imported_module_name))
			elif isinstance(i, interfaces.IImportModulesOperation):
				for imported_module_name in i.getImportedModuleNames():
					if (not self.program.hasModuleWithName(imported_module_name)):
						imported_modules.append(self.environment.importModule(imported_module_name))
			elif isinstance(i, interfaces.IImportSymbolOperation):
				imported_module_name=i.getImportOrigin()
				if (not self.program.hasModuleWithName(imported_module_name)):
					imported_modules.append(self.environment.importModule(imported_module_name))
			elif isinstance(i, interfaces.IImportSymbolsOperation):
				imported_module_name=i.getImportOrigin()
				if (not self.program.hasModuleWithName(imported_module_name)):
					imported_modules.append(self.environment.importModule(imported_module_name))
			elif True:
				self.environment.report.error(('Importation pass: operation not implemented ' + repr(i)))
			for m in imported_modules:
				if (m and (not self.program.hasModule(m))):
					self.program.addModule(m)
		return False
	

class DocumentationPass(Pass):
	"""The documentation pass will run SDoc on all the modules declared in this
	program, creating an HTML file."""
	HANDLES = [interfaces.IModule, interfaces.IModuleAttribute, interfaces.IClass, interfaces.IClassAttribute, interfaces.IClassMethod, interfaces.IAttribute, interfaces.IMethod, interfaces.IFunction]
	NAME = 'Documentation'
	def __init__ (self, args=None):
		self.doc = []
		self._module = None
		self._class = None
		self.texto = None
		self.writer = None
		if args is None: args = []
		Pass.__init__(self)
		import texto.main
		self.texto = lambda _:texto.main.text2htmlbody(_.decode("utf-8"))
		
	
	def setWriter(self, writer):
		self.writer = writer
	
	def onModule(self, module):
		m=self._base(module)
		m.update({'imports':[], 'classes':[], 'attributes':[], 'functions':[], 'shared':[]})
		self.doc.append(m)
		self._module = m
	
	def onClass(self, element):
		p=[]
		for _ in element.getParentClassesRefs():
			p.append(_.getReferenceName())
		c=self._base(element)
		c.update({'parents':p, 'shared':[], 'operations':[], 'attributes':[], 'methods':[]})
		self._module['classes'].append(c)
		self._class = c
	
	def onModuleAttribute(self, element):
		e=self._attribute(element)
		self._module['attributes'].append(e)
	
	def onClassAttribute(self, element):
		e=self._attribute(element)
		self._class['shared'].append(e)
	
	def onAttribute(self, element):
		e=self._attribute(element)
		(self._class or self._module)['attributes'].append(e)
	
	def onClassMethod(self, element):
		e=self._function(element)
		self._class['operations'].append(e)
	
	def onMethod(self, element):
		e=self._function(element)
		self._class['methods'].append(e)
	
	def onFunction(self, element):
		e=self._function(element)
		self._module['functions'].append(e)
	
	def _base(self, element):
		e={'type':self.getType(element), 'name':element.getName(), 'doc':self.getDocumentation(element), 'scope':self.getScopeName(), 'source':element.getSourcePath(), 'offsets':element.getOffsets()}
		return e
	
	def _attribute(self, element):
		e=self._base(element)
		e['value'] = self.writeValue(element)
		return e
	
	def _function(self, element):
		e=self._base(element)
		e['value'] = None
		p=[]
		for _ in element.getParameters():
			p.append({'name':_.getName(), 'scope':self.getScopeName(), 'value':self.writeValue(None)})
		return e
	
	def writeValue(self, element):
		if (not self.writer):
			return None
		elif element:
			source=self.writer.run(element)
			return source
		elif True:
			return None
	
	def getType(self, element):
		return element.__class__.__name__.rsplit('.', 1)[-1].lower()
	
	def getDocumentation(self, element):
		doc=element.getDocumentation()
		if (doc and doc.content):
			return self.texto(doc.content)
		elif True:
			return None
	
	def asJSON(self, title=None):
		"""Returns the HTML document generated by this pass"""
		if title is None: title = None
		return json.dumps(self.doc)
	

class TransformAsynchronousInvocations(Pass):
	HANDLES = [interfaces.IClosure]
	NAME = 'AsynchronousInvocationsExpansion'

class CountReferences(Pass):
	"""This pass adds "refcount" and "referers" annotations to all the referenced
	elements by handling every 'IReference' element.
	
	This is the first pass to be applied before actually removing the dead
	code."""
	HANDLES = [interfaces.IReference, interfaces.IFunction, interfaces.IElement]
	NAME = 'CountReferences'
	def addReferer(self, element, context=None):
		if context is None: context = self.getCurrentContext()
		refcount=element.getAnnotation('refcount')
		referers=element.getAnnotation('referers')
		if refcount:
			refcount.setContent((refcount.getContent() + 1))
			referers.getContent().append(context)
		elif True:
			self.annotate(element, 'refcount', 1)
			self.annotate(element, 'referers', [context])
	
	def onFunction(self, element):
		if (element.getName() == interfaces.Constants.ModuleInit):
			self.addReferer(element, element)
	
	def onReference(self, reference):
		if self.isIn(interfaces.IOperation):
			slot_and_value=self.resolve(reference)
			value=slot_and_value[1]
			if value:
				self.addReferer(value)
	
	def onElement(self, element):
		pass
	

class RemoveDeadCode(Pass):
	HANDLES = [interfaces.IConstruct, interfaces.IElement]
	NAME = 'RemoveDeadCode'
	def onConstruct(self, value):
		"""For every construct, we see if there is a refcount or not, and we
		see if at least one referer has a refcount. If it's not the case,
		then the value will be shadowed, and its refcount set to 0."""
		actual_count=0
		refcount=value.getAnnotation('refcount')
		referers=value.getAnnotation('referers')
		if refcount:
			referers = referers.getContent()
			for r in referers:
				r_refcount=r.getAnnotation('refcount')
				if (r_refcount and (r_refcount.getContent() > 0)):
					actual_count = (actual_count + 1)
			if (actual_count == 0):
				self.annotate(value, 'shadow')
				refcount.setContent(0)
			elif True:
				for element in self.context:
					element.removeAnnotation('shadow')
		elif True:
			self.annotate(value, 'shadow')
	
	def onElement(self, element):
		pass
	

