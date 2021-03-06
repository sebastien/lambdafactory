#8< ---[lambdafactory/modelwriter.py]---
#!/usr/bin/env python
# encoding: utf-8
import sys
__module__ = sys.modules[__name__]
import lambdafactory.interfaces as interfaces
from lambdafactory.model import isString, ensureUnicode
from lambdafactory.passes import Pass
from lambdafactory.splitter import SNIP
import string, types
__module_name__ = 'lambdafactory.modelwriter'
PREFIX = u'\t'
def _format (value, level=None):
	""" Format helper operation. See @format"""
	self=__module__
	if level is None: level = -1
	if type(value) in (list, tuple, types.GeneratorType):
		res = []
		for v in value:
			if v is None: continue
			res.extend(_format(v, level+1))
		return res
	else:
		if value is None: return u""
		assert isString(value), "Type not suitable for formatting: %s" % (value)
		return [u"\n".join((max(0,level)*PREFIX)+ensureUnicode(v) for v in value.split("\n"))]


def format (*values):
	""" Formats a combination of string ang tuples. Strings are joined by
	 newlines, and the content of the inner tuples gets indented"""
	self=__module__
	return u"\n".join(_format(values))


def _flatten (value, res):
	""" Flatten helper operation. See 'flatten'"""
	self=__module__
	if (type(value) in [tuple, list]):
		for v in value:
			_flatten(v, res)
	elif True:
		res.append(value)


def flatten (*lists):
	""" Flattens the given lists in a single list"""
	self=__module__
	res=[]
	_flatten(lists, res)
	return res


def notEmpty (p):
	""" Returns None if the given parameter is empty."""
	self=__module__
	return ((p and p) or None)


class AbstractWriter(Pass):
	HANDLES = [interfaces.IProgram, interfaces.ISingleton, interfaces.ITrait, interfaces.IClass, interfaces.IModule, interfaces.IAccessor, interfaces.IMutator, interfaces.IDestructor, interfaces.IConstructor, interfaces.IClassMethod, interfaces.IMethod, interfaces.IInitializer, interfaces.IFunction, interfaces.IClosure, interfaces.IWithBlock, interfaces.IBlock, interfaces.IModuleAttribute, interfaces.IClassAttribute, interfaces.IEnumerationType, interfaces.IType, interfaces.IEvent, interfaces.IAttribute, interfaces.IArgument, interfaces.IParameter, interfaces.IOperator, interfaces.IImplicitReference, interfaces.IReference, interfaces.INumber, interfaces.IString, interfaces.IList, interfaces.IDict, interfaces.IInterpolation, interfaces.IEnumeration, interfaces.IAllocation, interfaces.IAssignment, interfaces.IComputation, interfaces.IEventTrigger, interfaces.IEventBindOnce, interfaces.IEventBind, interfaces.IEventUnbind, interfaces.IInvocation, interfaces.IInstanciation, interfaces.IDecomposition, interfaces.IResolution, interfaces.IChain, interfaces.ISelection, interfaces.IRepetition, interfaces.IFilterIteration, interfaces.IMapIteration, interfaces.IReduceIteration, interfaces.IIteration, interfaces.IAccessOperation, interfaces.ISliceOperation, interfaces.ITypeIdentification, interfaces.IEvaluation, interfaces.ITermination, interfaces.INOP, interfaces.IBreaking, interfaces.IContinue, interfaces.IExcept, interfaces.IInterception, interfaces.IImportSymbolOperation, interfaces.IImportSymbolsOperation, interfaces.IImportModuleOperation, interfaces.IImportModulesOperation, interfaces.IEmbed]
	def __init__ (self):
		self._generatedSymbols = {}
		Pass.__init__(self)
	
	def setOption(self, name, value):
		self.options[name] = value
		return self
	
	def _prepend(self, element, value):
		""" Takes care of prepending value to element, managing both
		 string and arrays"""
		if (isinstance(element, list) or isinstance(element, tuple)):
			element = list(element)
			element.insert(0, value)
		elif True:
			if (isinstance(value, list) or isinstance(value, tuple)):
				value = list(value)
				value.append(element)
				return value
			elif True:
				return (value + element)
	
	def lines(self, value, prefix=None):
		if prefix is None: prefix = u''
		if isString(value):
			yield prefix + value
		elif type(value) in (tuple, list, types.GeneratorType):
			for _ in value:
				for l in self.lines(_, prefix + "\t"):
					yield l
		else:
			raise NotImplementedError
	
	def write(self, element):
		res=None
		if (element is None):
			return u''
		elif True:
			if isString(element):
				return element
			elif ((type(element) is list) or (type(element) is tuple)):
				return u"\n".join(self.write(_) for _ in element)
			elif element.hasAnnotation(u'shadow'):
				return u''
			elif True:
				this_interfaces = self.HANDLES
				for  the_interface in this_interfaces:
					name = the_interface.__name__[1:]
					if isinstance(element, the_interface):
						if not hasattr(self, "on" + name ):
							raise Exception("Writer does not define write method for: " + name + " in " + str(self))
						else:
							self.context.append(element)
							result = getattr(self, "on" + name)(element)
							self.context.pop()
							# We support write rules returning generators
							if type(result) is types.GeneratorType:
								result = u"\n".join(_format(result, -2))
							return result
				raise Exception("Element implements unsupported interface: " + str(element))
	
	def run(self, program):
		self.program = program
		return self.write(program)
	
	def onProgram(self, element):
		""" Writes a Program element"""
		lines=[]
		for module in element.getModules():
			if (not module.isImported()):
				line=self.write(module)
				if line:
					lines.append(line)
		return u'\n'.join(lines)
	
	def _format(self, *values):
		return format(*values)
	
	def _expand(self, values, kw):
		return [string.Template(_).substitute(**kw) for _ in values]
	
	def _unique(self, name):
		i=0
		while True:
			new_name = (name + str(i))
			if (self._generatedSymbols.get(new_name) == None):
				self._generatedSymbols[new_name] = True
				return new_name
			i = (i + 1)
	

