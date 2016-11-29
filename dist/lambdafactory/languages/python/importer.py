#8< ---[lambdafactory/languages/python/importer.py]---
#!/usr/bin/env python
import sys
__module__ = sys.modules[__name__]
import types
__module_name__ = 'lambdafactory.languages.python.importer'
class Importer:
	"""Imports Python module into the current environment."""
	MODULE_IGNORES = ['__builtins__']
	def __init__ (self, environment):
		self.environment = None
		self.environment = environment
	
	def importModule(self, moduleName):
		try:
			__import__(moduleName)
			
		except Exception as e:
			return False
		python_module=eval(moduleName)
		module=self.environment.getFactory().createModule(moduleName)
		for slot_name in dir(python_module):
			slot_value=getattr(python_module, slot_name)
			slot_type=type(slot_value)
			imported_value=self.importValue(slot_value)
			if imported_value:
				module.setSlot(slot_name, imported_value)
		return module
	
	def importClass(self, classObject):
		f=self.environment.getFactory()
		c=f.createClass(classObject.__name__)
		for slot_name in dir(classObject):
			slot_value=getattr(classObject, slot_name)
			imported_value=self.importValue(slot_value)
			if imported_value:
				c.setSlot(slot_name, imported_value)
		return c
	
	def _getPythonFunctionArguments(self, function):
		if hasattr(function, 'im_func'):
			function = function.im_func
		f=self.environment.getFactory()
		defaults=function.func_defaults
		code=function.func_code
		arguments=[]
		args = list(code.co_varnames[:code.co_argcount])
		# We split the args in args / default_args
		if defaults:
			default_args = args[-len(defaults):]
			args         = args[:-len(defaults)]
		else:
			default_args = []
		# We add the default arguments (properly formatted) to the arguments
		# list
		for i in range(len(default_args)):
			d = default_args[i]
			args.append("%s=%s" % (d, repr(defaults[i])) )
		# We append the arguments
		if code.co_flags & 0x0004: # CO_VARARGS
			args.append('*'+code.co_varnames[len(args)])
		if code.co_flags & 0x0008: # CO_VARKEYWORDS
			args.append('**'+code.co_varnames[len(args)])
		
		arguments=[]
		for arg in args:
			arguments.append(f._arg(arg, None))
		return arguments
	
	def importInstanceMethod(self, methodObject):
		f=self.environment.getFactory()
		args=self._getPythonFunctionArguments(methodObject)
		return f.createMethod(methodObject.__name__, args)
	
	def importFunction(self, functionObject):
		pass
	
	def importList(self, l):
		pass
	
	def importDict(self, d):
		pass
	
	def importValue(self, value):
		value_type=type(value)
		if (value_type == types.ClassType):
			return self.importClass(value)
		elif (value_type == types.UnboundMethodType):
			return self.importInstanceMethod(value)
		elif (value_type == types.ListType):
			return self.importList(value)
		elif (value_type == types.DictType):
			return self.importDict(value)
		elif True:
			v=None
	

MAIN_CLASS = Importer
