#!/usr/bin/env python
import sys
__module__ = sys.modules[__name__]
import lambdafactory.interfaces as interfaces
from lambdafactory.passes import Pass
from lambdafactory.splitter import SNIP
__module_name__ = 'lambdafactory.modelwriter'
PREFIX = '\t'
def _format (value, level=None):
	"""Format helper operation. See @format"""
	self=__module__
	if level is None: level = -1
	if type(value) in (list, tuple):
		res = []
		for v in value:
			if v is None: continue
			res.extend(_format(v, level+1))
		return res
	else:
		if value is None: return ""
		assert type(value) in (str, unicode), "Type not suitable for formatting: %s" % (value)
		return ["\n".join((level*PREFIX)+v for v in value.split("\n"))]
	


def format (*values):
	"""Formats a combination of string ang tuples. Strings are joined by
	newlines, and the content of the inner tuples gets indented"""
	self=__module__
	return '\n'.join(_format(values))


def _flatten (value, res):
	"""Flatten helper operation. See 'flatten'"""
	self=__module__
	if (type(value) in [tuple, list]):
		for v in value:
			_flatten(v, res)
	elif True:
		res.append(value)


def flatten (*lists):
	"""Flattens the given lists in a single list"""
	self=__module__
	res=[]
	_flatten(lists, res)
	return res


def notEmpty (p):
	"""Returns None if the given parameter is empty."""
	self=__module__
	return ((p and p) or None)


class AbstractWriter(Pass):
	HANDLES = [interfaces.IProgram, interfaces.IClass, interfaces.IModule, interfaces.IAccessor, interfaces.IMutator, interfaces.IDestructor, interfaces.IConstructor, interfaces.IClassMethod, interfaces.IMethod, interfaces.IFunction, interfaces.IClosure, interfaces.IBlock, interfaces.IModuleAttribute, interfaces.IClassAttribute, interfaces.IAttribute, interfaces.IArgument, interfaces.IParameter, interfaces.IOperator, interfaces.IReference, interfaces.INumber, interfaces.IString, interfaces.IList, interfaces.IDict, interfaces.IEnumeration, interfaces.IAllocation, interfaces.IAssignation, interfaces.IComputation, interfaces.IInvocation, interfaces.IInstanciation, interfaces.IResolution, interfaces.ISelection, interfaces.IRepetition, interfaces.IIteration, interfaces.IAccessOperation, interfaces.ISliceOperation, interfaces.IEvaluation, interfaces.ITermination, interfaces.IBreaking, interfaces.IExcept, interfaces.IInterception, interfaces.IImportSymbolOperation, interfaces.IImportSymbolsOperation, interfaces.IImportModuleOperation, interfaces.IImportModulesOperation, interfaces.IEmbed]
	def __init__ (self):
		self._generatedSymbols = {}
		Pass.__init__(self)
	
	def write(self, element):
		res=None
		if (element is None):
			return ''
		elif True:
			if (type(element) in [str, unicode]):
				return element
			elif element.hasAnnotation('shadow'):
				return ''
			elif True:
				this_interfaces = self.HANDLES
				for  the_interface in this_interfaces:
					name = the_interface.__name__[1:]
					if isinstance(element, the_interface):
						if not hasattr(self, "on" + name ):
							raise Exception("Writer does not define write method for: " + name)
						else:
							self.context.append(element)
							result = getattr(self, "on" + name)(element)
							self.context.pop()
							return result
				raise Exception("Element implements unsupported interface: " + str(element))
				
	
	def run(self):
		return self.write(self.environment.getProgram())
	
	def onProgram(self, element):
		"""Writes a Program element"""
		lines=[]
		for module in element.getModules():
			if (not module.isImported()):
				lines.append(self.write(module))
		return '\n'.join(lines)
	
	def _format(self, *values):
		return format(*values)
		
	
	def _unique(self, name):
		i=0
		while True:
			new_name = (name + str(i))
			if (self._generatedSymbols.get(new_name) == None):
				self._generatedSymbols[new_name] = True
				return new_name
			i = (i + 1)
	

