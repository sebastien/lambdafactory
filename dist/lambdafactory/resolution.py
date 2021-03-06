#8< ---[lambdafactory/resolution.py]---
#!/usr/bin/env python
# encoding: utf-8
import sys
__module__ = sys.modules[__name__]
import lambdafactory.interfaces as interfaces
from lambdafactory.passes import Pass
import re, math
__module_name__ = 'lambdafactory.resolution'
LETTERS = u'abcdefghijklmnopqrstuvwxyz'
class BasicDataFlow(Pass):
	""" The basic dataflow pass will associate DataFlow objects to elements which
	 don't have any already, and will make sure that Context slots are defined
	 in the dataflow, as well as allocations.
	
	 It is safe to apply this pass more than once on the program, but as it will
	 keep the existing dataflow information, you should make sure that if you
	 modified the program model in the meantime, you clear the dataflow out of the
	 elements that you changed.
	
	 TODO: Implement an 'invalidateDataFlow' when an operation is replaced/deleted,
	 so that we ensure that the DF remains consitent.
	
	 Rules:
	
	 - DataFlows are created for Context and Processes
	 - DataFlowSlots begin with nothing or an allocation
	 - DataFlowSlots operations are the operations that reference the slot (stage 2)
	
	 Stages:
	
	 1) Create dataflows for Contexts, Processes, Importations and Allocations
	 2) Properly flow classes (so that resolution in parents can happen)
	 3) Attaches operations that reference a value to the original slot (this
	    prepares the path for the typing pass)"""
	RE_IMPLICIT = re.compile(u'^_[0-9]?$')
	HANDLES = [interfaces.IProgram, interfaces.IModule, interfaces.IClass, interfaces.IMethod, interfaces.IClosure, interfaces.IBlock, interfaces.IProcess, interfaces.IContext, interfaces.IAllocation, interfaces.IAssignment, interfaces.IIteration, interfaces.IChain, interfaces.ISelection, interfaces.IOperation, interfaces.IAnonymousReference, interfaces.IImplicitReference, interfaces.IReference, interfaces.IValue]
	NAME = u'Resolution'
	def __init__ (self):
		Pass.__init__(self)
	
	def getParentDataFlow(self):
		""" Returns the dataflow of the parent element. It is supposed to exist."""
		if self.hasParentElement():
			i=(len(self.context) - 2)
			while (i >= 0):
				d=self.context[i].getDataFlow()
				if d:
					return d
				i = (i - 1)
			return None
		elif True:
			return None
	
	def ensureDataFlow(self, element):
		""" Ensures that the given element has an attached DataFlow"""
		dataflow=element.getDataFlow()
		if (not dataflow):
			dataflow = self.getFactory().createDataFlow(element)
			parent_df=self.getParentDataFlow()
			if (self.hasParentElement()) and (not parent_df):
				sys.stderr.write(" create dataflow for {0}:{1}\n".format(element,self.getParentDataFlow()))
			dataflow.setParent(parent_df)
			element.setDataFlow(dataflow)
		return dataflow
	
	def _ensureAnnotationsDataflow(self, element):
		for _ in element.getAnnotations(u'where'):
			self.ensureDataFlow(_.getContent())
	
	def onProgram(self, element):
		dataflow=self.ensureDataFlow(element)
		dataflow.declareEnvironment(u'Undefined', None)
		dataflow.declareEnvironment(u'True', None)
		dataflow.declareEnvironment(u'False', None)
		dataflow.declareEnvironment(u'Null', None)
	
	def onModule(self, element):
		dataflow=self.ensureDataFlow(element)
		self.onContext(element)
		self._ensureAnnotationsDataflow(element)
	
	def onType(self, element):
		pass
	
	def onEnumerationType(self, element):
		self.ensureDataFlow(element)
		for _ in element.getSymbols():
			df=self.ensureDataFlow(_)
			df.declareLocal(_.getName(), _)
	
	def onClass(self, element):
		dataflow=self.ensureDataFlow(element)
		dataflow.declareEnvironment(u'super', None)
		dataflow.declareEnvironment(u'self', None)
		self.onContext(element)
	
	def onMethod(self, element):
		dataflow=self.ensureDataFlow(element)
		dataflow.declareEnvironment(u'super', None)
		dataflow.declareEnvironment(u'self', None)
		self.onClosure(element)
	
	def onClosure(self, element):
		dataflow=self.ensureDataFlow(element)
		for argument in element.getArguments():
			dataflow.declareArgument(argument.getName(), argument)
		self._ensureAnnotationsDataflow(element)
	
	def onBlock(self, element):
		if isinstance(element.parent, interfaces.IMatchOperation):
			element.setDataFlow(element.parent.dataflow)
		elif True:
			dataflow=self.ensureDataFlow(element)
	
	def onProcess(self, element):
		dataflow=self.ensureDataFlow(element)
		self._ensureAnnotationsDataflow(element)
	
	def onContext(self, element):
		dataflow=self.ensureDataFlow(element)
		for name_and_value in element.getSlots():
			dataflow.declareLocal(name_and_value[0], name_and_value[1], element)
	
	def onAllocation(self, element):
		self.onOperation(element)
		dataflow=element.getDataFlow()
		name=element.getSlotToAllocate().getName()
		dataflow.declareLocal(name, element.getDefaultValue(), element)
	
	def onAssignment(self, element):
		dataflow=element.getDataFlow()
		if (not dataflow):
			dataflow = self.getParentDataFlow()
			element.setDataFlow(dataflow)
		t=element.getTarget()
		if isinstance(t, interfaces.IReference):
			name=t.getReferenceName()
			slots=self.resolve(name)
			if (slots and slots[0]):
				slot=slots[0]
				scope=slot.getDataFlow().getElement()
				i=self.indexInContext(scope)
				j=self.lastIndexInContext(interfaces.IClosure)
				if (i < j):
					self.context[j].declareMutation(name, slot)
	
	def onOperation(self, element):
		dataflow=element.getDataFlow()
		if (not dataflow):
			dataflow = self.getParentDataFlow()
			element.setDataFlow(dataflow)
		return dataflow
	
	def onValue(self, element):
		dataflow=element.getDataFlow()
		if (not dataflow):
			dataflow = self.getParentDataFlow()
			element.setDataFlow(dataflow)
	
	def onIteration(self, element):
		""" We make sure to add `encloses` annotation to closures in iterations"""
		closure=element.getClosure()
		self.onOperation(element)
		if isinstance(closure, interfaces.IClosure):
			self.onClosure(closure)
			for p in closure.getParameters():
				name=p.getName()
				slots=self.resolve(name)
				if (slots and slots[0]):
					closure.declareEnclosure(name, slots[0])
	
	def onSelection(self, element):
		self.onOperation(element)
		implicit=element.getImplicitValue()
		if implicit:
			slot=element.dataflow.declareImplicit(implicit, element)
	
	def onChain(self, element):
		self.onOperation(element)
		implicit=element.getImplicitValue()
		if implicit:
			slot=element.dataflow.declareImplicit(implicit, element)
	
	def getAnonymousName(self, i):
		l=len(LETTERS)
		if (i < l):
			return LETTERS[i]
		elif True:
			return (self.getAnonymousName((int((i / l)) - 1)) + self.getAnonymousName((i % l)))
	
	def getAnonymousReferenceName(self):
		""" Gets the first anonymous reference name"""
		i = 0
		while True:
			n=self.getAnonymousName(i)
			s=self.resolve(n)
			if (not s[0]):
				return n
			i = (i + 1)
	
	def onAnonymousReference(self, element):
		""" Finds a name for the anonymous reference that does not conflict with
		 anything in scope."""
		dataflow=self.getCurrentDataFlow()
		name=self.getAnonymousReferenceName()
		dataflow.declareLocal(name, None, element)
		element.setReferenceName(name)
	
	def onImplicitReference(self, element):
		element.setReferenceName(self.getCurrentDataFlow().getImplicitSlotFor(element.getElement()).getName())
	
	def onReference(self, element):
		i=self.lastIndexInContext(interfaces.IClosure)
		j=self.lastIndexInContext(interfaces.IIteration)
		jj=self.lastIndexInContext(interfaces.IRepetition)
		name=element.getName()
		if ((i >= 0) and self.__class__.RE_IMPLICIT.match(name)):
			slot=self.resolve(element)
			if (not slot[0]):
				n=0
				if (len(name) > 1):
					n = int(name[1:])
				closure=self.context[i]
				dataflow=closure.dataflow
				parameters=closure.parameters
				while (len(parameters) <= n):
					l=len(parameters)
					p=self.environment.factory._param((u'_' + str(l)))
					parameters.append(p)
					if dataflow:
						dataflow.declareArgument(p.getName(), p)
				p=parameters[n]
				name = p.getName()
				element.setReferenceName(name)
		if (i and (((i > jj) and (jj >= 0)) or ((i > (j + 1)) and (j >= 0)))):
			slots=self.resolve(name)
			if (j == -1):
				j = jj
			if (slots and slots[0]):
				slot=slots[0]
				scope=slot.getDataFlow().getElement()
				k=self.indexInContext(scope)
				c=self.context[i]
				if (((scope and (k < i)) and (j < k)) and (not c.hasMutation(name))):
					c.declareEnclosure(name, slots)
	

class ClearDataFlow(Pass):
	""" Cleares the dataflows from the elements"""
	HANDLES = [interfaces.IProgram, interfaces.IModule, interfaces.IClass, interfaces.IMethod, interfaces.IClosure, interfaces.IProcess, interfaces.IContext, interfaces.IAllocation, interfaces.IOperation, interfaces.IArgument, interfaces.IValue]
	NAME = u'ClearDataflow'
	def __init__ (self):
		Pass.__init__(self)
	
	def getParentDataFlow(self):
		""" Returns the dataflow of the parent element. It is supposed to exist."""
		if self.hasParentElement():
			return self.getParentElement().getDataFlow()
		elif True:
			return None
	
	def clearDataFlow(self, element):
		""" Ensures that the given element has an attached DataFlow"""
		element.setDataFlow(None)
	
	def onProgram(self, element):
		self.clearDataFlow(element)
	
	def onModule(self, element):
		self.clearDataFlow(element)
		self._clearAnnotationsDataFlow(element)
	
	def onClass(self, element):
		self.clearDataFlow(element)
		for _ in element.parentClasses:
			self.clearDataFlow(element)
		self._clearAnnotationsDataFlow(element)
	
	def onMethod(self, element):
		self.clearDataFlow(element)
		self._clearAnnotationsDataFlow(element)
	
	def onClosure(self, element):
		self.clearDataFlow(element)
	
	def onProcess(self, element):
		self.clearDataFlow(element)
		self._clearAnnotationsDataFlow(element)
	
	def onContext(self, element):
		self.clearDataFlow(element)
		self._clearAnnotationsDataFlow(element)
	
	def onAllocation(self, element):
		self.clearDataFlow(element)
	
	def onOperation(self, element):
		self.clearDataFlow(element)
	
	def onArgument(self, element):
		pass
	
	def onValue(self, element):
		self.clearDataFlow(element)
	
	def _clearAnnotationsDataFlow(self, element):
		for _ in (element.getAnnotations(u'where') or []):
			self.clearDataFlow(_)
	

class DataFlowBinding(Pass):
	""" This pass will target classes, resolving their parent classes and binding the
	 dataflow slot to the proper value. If the binding fails, an exception will be
	 raised, meaning that either the passes were not set up properly, or that the
	 resolution has failed (and there is an inconsistency in the program model)."""
	FAILED = tuple([None, None])
	HANDLES = [interfaces.IModule, interfaces.IClass, interfaces.IContext, interfaces.IEnumerationType]
	NAME = u'ClassParentsResolution'
	def __init__ (self):
		Pass.__init__(self)
	
	def _importSymbol(self, operation, symbolName, fromModuleName, moduleDest, alias=None):
		if alias is None: alias = None
		module_name=fromModuleName
		symbol_name=symbolName
		element=moduleDest
		slot_and_value=self.resolveAbsolute(module_name)
		result={}
		imported_name=(alias or symbol_name)
		df=element.getDataFlow()
		if (slot_and_value == self.__class__.FAILED):
			self.environment.report.error(u'Imported module not found in scope:', module_name, u'in', element.getName())
			self._ensureModule(fromModuleName, operation)
			return self._importSymbol(operation, symbolName, fromModuleName, moduleDest, alias)
		elif (symbol_name == u'*'):
			imported_module=slot_and_value[1]
			for slot_name in imported_module.getSlotNames():
				result.update(self._importSymbol(operation, slot_name, fromModuleName, moduleDest))
		elif True:
			symbol_slot_and_value=self.resolve(symbol_name, slot_and_value[1])
			if (symbol_slot_and_value == self.__class__.FAILED):
				if (fromModuleName != self.getCurrentModule().getAbsoluteName()):
					self.environment.report.error(u'Symbol not found in module scope:', symbol_name, u'in', module_name)
				if (not df.hasSlot(imported_name)):
					df.declareImported(imported_name, None, operation)
				result[imported_name] = None
			elif True:
				value=symbol_slot_and_value[1]
				assert((df.getElement() == element))
				previous_slot=df.getSlot(imported_name)
				if previous_slot:
					previous_slot.overrides = df._slot(imported_name, value, operation, u'imported')
				elif True:
					df.declareImported(imported_name, value, operation)
					assert((df.resolve(imported_name)[0].getDataFlow() == df))
					assert((df.resolve(imported_name)[0].getDataFlow().getElement() == element))
				result[imported_name] = value
		return result
	
	def _importModule(self, module, operation, fullname, alias=None):
		if alias is None: alias = None
		imported={}
		slot_and_value=self.resolveAbsolute(fullname)
		if (slot_and_value == self.__class__.FAILED):
			self.environment.report.error(u'Imported module not found in scope:', fullname, u'in', module.getName())
		elif True:
			name=(alias or fullname)
			module.getDataFlow().declareImported(name, slot_and_value[1], operation)
			imported[name] = slot_and_value[1]
			assert((module.getDataFlow().getElement() == module))
			assert((module.getDataFlow().resolve(name)[0].getDataFlow() == module.getDataFlow()))
			assert((module.getDataFlow().resolve(name)[0].getDataFlow().getElement() == module))
		return imported
	
	def _ensureModule(self, moduleName, operation):
		""" Ensures that the given module is registered, even if it cannot be
		 located."""
		module=self.program.getModule(moduleName)
		if (not module):
			module = self.program.factory.createModule(moduleName)
			df=self.program.factory.createDataFlow(module)
			df.setParent(self.program.getDataFlow())
			module.setDataFlow(df)
			module.setImported(True)
			df.declareImported(moduleName, None, operation)
			self.program.addModule(module)
		return module
	
	def onEnumerationType(self, element):
		df=self.getCurrentModule().getDataFlow()
		for _ in element.symbols:
			df.declareLocal(_.getName(), _, element)
	
	def onModule(self, element):
		""" Processes the module import operations and adds them to the module
		 dataflow"""
		imports=element.getImportOperations()
		imported={}
		for i in imports:
			if isinstance(i, interfaces.IImportModuleOperation):
				imported.update(self._importModule(element, i, i.getImportedModuleName(), i.getAlias()))
			elif isinstance(i, interfaces.IImportModulesOperation):
				for n in i.getImportedModuleNames():
					imported.update(self._importModule(element, i, n))
			elif isinstance(i, interfaces.IImportSymbolOperation):
				module_name=i.getImportOrigin()
				symbol_name=i.getImportedElement()
				alias=i.getAlias()
				imported.update(self._importSymbol(i, symbol_name, module_name, element, alias))
			elif isinstance(i, interfaces.IImportSymbolsOperation):
				module_name=i.getImportOrigin()
				for s in i.getOpArgument(0):
					imported.update(self._importSymbol(i, s.getImportedElement(), s.getImportOrigin(), element, s.getAlias()))
			elif True:
				self.environment.report.error((u'DataFlowBinding: operation not implemented ' + repr(i)))
		if element.hasAnnotation(u'imported'):
			element.getAnnotation(u'imported').setContent(imported)
		elif True:
			element.setAnnotation(u'imported', imported)
		return imported
	
	def onClass(self, element):
		for parent_class in self.getClassParents(element):
			assert((parent_class != element))
			if isinstance(parent_class, interfaces.IConstruct):
				assert(parent_class.getDataFlow())
				element.getDataFlow().addSource(parent_class.getDataFlow())
			elif isinstance(parent_class, interfaces.IReference):
				self.environment.report.error((((u'Unresolved parent class: ' + parent_class.getReferenceName()) + u' in ') + element.getAbsoluteName()))
	
	def onContext(self, element):
		element.dataflow.ensureImplicitsNamed()
	

