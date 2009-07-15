#!/usr/bin/env python
import sys
__module__ = sys.modules[__name__]
import lambdafactory.interfaces as interfaces
from lambdafactory.passes import Pass
__module_name__ = 'lambdafactory.resolution'
class BasicDataFlow(Pass):
	"""The basic dataflow pass will associate DataFlow objects to elements which
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
	HANDLES = [interfaces.IProgram, interfaces.IModule, interfaces.IClass, interfaces.IMethod, interfaces.IClosure, interfaces.IProcess, interfaces.IContext, interfaces.IAllocation, interfaces.IOperation, interfaces.IParameter, interfaces.IValue]
	NAME = 'Resolution'
	def __init__ (self):
		Pass.__init__(self)
	
	def getParentDataFlow(self):
		"""Returns the dataflow of the parent element. It is supposed to exist."""
		if self.hasParentElement():
			return self.getParentElement().getDataFlow()
		elif True:
			return None
	
	def ensureDataFlow(self, element):
		"""Ensures that the given element has an attached DataFlow"""
		dataflow=element.getDataFlow()
		if (not dataflow):
			dataflow = self.getFactory().createDataFlow(element)
			dataflow.setParent(self.getParentDataFlow())
			element.setDataFlow(dataflow)
		return dataflow
	
	def onProgram(self, element):
		dataflow=self.ensureDataFlow(element)
		dataflow.declareEnvironment('Undefined', None)
		dataflow.declareEnvironment('True', None)
		dataflow.declareEnvironment('False', None)
		dataflow.declareEnvironment('Null', None)
	
	def onModule(self, element):
		dataflow=self.ensureDataFlow(element)
		self.onContext(element)
	
	def onClass(self, element):
		dataflow=self.ensureDataFlow(element)
		dataflow.declareEnvironment('super', None)
		dataflow.declareEnvironment('self', None)
		self.onContext(element)
	
	def onMethod(self, element):
		dataflow=self.ensureDataFlow(element)
		dataflow.declareEnvironment('super', None)
		dataflow.declareEnvironment('self', None)
		self.onClosure(element)
	
	def onClosure(self, element):
		dataflow=self.ensureDataFlow(element)
		for argument in element.getArguments():
			dataflow.declareArgument(argument.getName(), argument)
	
	def onProcess(self, element):
		dataflow=self.ensureDataFlow(element)
	
	def onContext(self, element):
		dataflow=self.ensureDataFlow(element)
		for name_and_value in element.getSlots():
			dataflow.declareVariable(name_and_value[0], name_and_value[1], element)
	
	def onAllocation(self, element):
		self.onOperation(element)
		dataflow=element.getDataFlow()
		name=element.getSlotToAllocate().getName()
		dataflow.declareVariable(name, element.getDefaultValue(), element)
	
	def onOperation(self, element):
		dataflow=element.getDataFlow()
		if (not dataflow):
			dataflow = self.getParentDataFlow()
			element.setDataFlow(dataflow)
		if False:
			for op_arg in element.getOpArguments():
				if (type(op_arg) in [tuple, list]):
					for arg in op_arg:
						assert(isinstance(arg, interfaces.IElement))
						self.walk(arg)
				elif True:
					self.walk(op_arg)
	
	def onParameter(self, element):
		value=element.getValue()
	
	def onValue(self, element):
		dataflow=element.getDataFlow()
		if (not dataflow):
			dataflow = self.getParentDataFlow()
			element.setDataFlow(dataflow)
	

class DataFlowBinding(Pass):
	"""This pass will target classes, resolving their parent classes and binding the
	dataflow slot to the proper value. If the binding fails, an exception will be
	raised, meaning that either the passes were not set up properly, or that the
	resolution has failed (and there is an inconsistency in the program model)."""
	HANDLES = [interfaces.IModule, interfaces.IClass]
	NAME = 'ClassParentsResolution'
	def __init__ (self):
		Pass.__init__(self)
	
	def importSymbol(self, operation, symbolName, fromModuleName, moduleDest, alias=None):
		if alias is None: alias = None
		FAILED=tuple([None, None])
		module_name=fromModuleName
		symbol_name=symbolName
		element=moduleDest
		slot_and_value=self.resolveAbsolute(module_name)
		if (slot_and_value == FAILED):
			self.environment.report.error('Imported module not found in scope:', module_name, 'in', element.getName())
		elif True:
			symbol_slot_and_value=self.resolve(symbol_name, slot_and_value[1])
			if (symbol_slot_and_value == FAILED):
				self.environment.report.error('Symbol not found in module scope:', symbol_name, 'in', module_name)
			elif True:
				value=symbol_slot_and_value[1]
				assert((element.getDataFlow().getElement() == element))
				if alias:
					element.getDataFlow().declareImported(alias, value, operation)
					assert((element.getDataFlow().resolve(alias)[0].getDataFlow() == element.getDataFlow()))
					assert((element.getDataFlow().resolve(alias)[0].getDataFlow().getElement() == element))
				elif True:
					element.getDataFlow().declareImported(symbol_name, value, operation)
					assert((element.getDataFlow().resolve(symbol_name)[0].getDataFlow() == element.getDataFlow()))
					assert((element.getDataFlow().resolve(symbol_name)[0].getDataFlow().getElement() == element))
	
	def onModule(self, element):
		"""Processes the module import operations and adds them to the module
		dataflow"""
		imports=element.getImportOperations()
		FAILED=tuple([None, None])
		for i in imports:
			if isinstance(i, interfaces.IImportModuleOperation):
				absolute_name=i.getImportedModuleName()
				alias=i.getAlias()
				slot_and_value=self.resolveAbsolute(absolute_name)
				if (slot_and_value == FAILED):
					self.environment.report.error('Imported module not found in scope:', absolute_name, 'in', element.getName())
				elif alias:
					element.getDataFlow().declareImported(alias, slot_and_value[1], i)
					assert((element.getDataFlow().getElement() == element))
					assert((element.getDataFlow().resolve(alias)[0].getDataFlow() == element.getDataFlow()))
					assert((element.getDataFlow().resolve(alias)[0].getDataFlow().getElement() == element))
			elif isinstance(i, interfaces.IImportSymbolOperation):
				module_name=i.getImportOrigin()
				symbol_name=i.getImportedElement()
				alias=i.getAlias()
				self.importSymbol(i, symbol_name, module_name, element, alias)
			elif isinstance(i, interfaces.IImportSymbolsOperation):
				module_name=i.getImportOrigin()
				for symbol_name in i.getOpArgument(0):
					self.importSymbol(i, symbol_name, module_name, element, None)
			elif True:
				self.environment.report.error(('DataFlowBinding: operation not implemented ' + repr(i)))
	
	def onClass(self, element):
		for parent_class_ref in element.getParentClassesRefs():
			slot_and_value=self.resolveLocalOrAbsolute(parent_class_ref)
			if (not slot_and_value[0]):
				self.environment.report.error('Parent class not found:', parent_class_ref.getReferenceName(), 'in', element.getName())
			elif True:
				parent_class=slot_and_value[1]
				assert(isinstance(parent_class, interfaces.IClass))
				element.getDataFlow().addSource(parent_class.getDataFlow())
	

