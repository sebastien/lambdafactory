#!/usr/bin/env python
# Encoding: iso-8859-1
# vim: tw=80 ts=4 sw=4 noet
# -----------------------------------------------------------------------------
# Project   : XXX
# -----------------------------------------------------------------------------
# Author    : Sebastien Pierre                               <sebastien@ivy.fr>
# License   : Revised BSD License
# -----------------------------------------------------------------------------
# Creation  : 02-Nov-2006
# Last mod  : 07-Jan-2007
# -----------------------------------------------------------------------------

# FIXME: Evaluable == Expression ?

import model
import modeltypes as mt
import interfaces

def assertImplements(v,i):
	return True

class ModelException(Exception):
	pass

class ModelBadArgument(Exception):
	def __init__( self, someClass, expectedClass, argument ):
		Exception.__init__(self, "Bad argument: %s expected %s, got %s" \
		% (someClass, expectedClass, argument))

# ------------------------------------------------------------------------------
#
# FACTORY
#
# ------------------------------------------------------------------------------

class Factory:
	"""This class takes a module and look for classes with the same name as the
	`createXXX` methods and instanciates them.

	For instance, if you define a module with classes like `Value`, `Literal`,
	`Invocation`, `Function`, etc. you just have to give this module to the
	factory constructor and it will be used to generate the given element."""


	def __init__( self, module=model ):
		self._module = module
		self.MainFunction  = model.Constants.MainFunction
		self.CurrentModule = model.Constants.CurrentModule
		self.Constructor   = model.Constants.Constructor
		self.Destructor    = model.Constants.Destructor
		self.ModuleInit    = model.Constants.ModuleInit
		self.CurrentValue  = model.Constants.CurrentValue

	def _getImplementation( self, name ):
		if not hasattr(self._module, name ):
			raise ModelException("Module %s does not implement: %s" % \
			(self._module, name))
		else:
			return getattr(self._module, name)

	def createDataFlow( self, element, parent=None ):
		return self._getImplementation("DataFlow")(element, parent)

	def createDataFlowSlot( self, name, value, origin, slotType ):
		return self._getImplementation("DataFlowSlot")(name,value,origin,slotType)

	def createProgram( self ):
		return self._getImplementation("Program")()

	def createInterface( self ):
		return self._getImplementation("Interface")()

	def createBlock( self ):
		return self._getImplementation("Block")()

	def createClosure( self, arguments ):
		return self._getImplementation("Closure")(arguments)

	def createFunction( self, name, arguments ):
		return self._getImplementation("Function")(name, arguments)

	def createMethod( self, name, arguments=None ):
		return self._getImplementation("InstanceMethod")(name, arguments)

	def createConstructor( self, arguments=None ):
		return self._getImplementation("Constructor")(arguments)

	def createDestructor( self ):
		return self._getImplementation("Destructor")()

	def createClassMethod( self, name, arguments=() ):
		return self._getImplementation("ClassMethod")(name, arguments)

	def createClass( self, name, inherited=() ):
		return self._getImplementation("Class")(name, inherited)

	def createInterface( self, name, inherited=() ):
		return self._getImplementation("Interface")(name, inherited)
	
	def createModule( self, name ):
		return self._getImplementation("Module")(name)

	def importSymbol( self, name, origin, alias ):
		return self._getImplementation("ImportSymbolOperation")(name, origin, alias)

	def importSymbols( self, names, origin ):
		return self._getImplementation("ImportSymbolsOperation")(names, origin)

	def importModule( self, name, alias ):
		return self._getImplementation("ImportModuleOperation")(name, alias)
			
	def importModules( self, names ):
		return self._getImplementation("ImportModulesOperation")(names)
			
	def evaluate( self, evaluable ):
		return self._getImplementation("Evaluation")(evaluable)

	def allocate( self, slot, value=None ):
		return self._getImplementation("Allocation")(slot, value)

	def assign( self, name, evaluable ):
		return self._getImplementation("Assignation")(name, evaluable)

	def compute( self, operatorName, leftOperand, rightOperand=None ):
		return self._getImplementation("Computation")(operatorName, leftOperand, rightOperand)

	# FIXME: ADD APPLICATION, which only takes values. Invocation takes
	# parameters that can be named.
	def invoke( self, evaluable, *arguments ):
		arguments = map(self._ensureParam, arguments)
		return self._getImplementation("Invocation")(evaluable, arguments)

	def instanciate( self, evaluable, *arguments ):
		return self._getImplementation("Instanciation")(evaluable, arguments)

	def resolve( self, reference, context=None ):
		return self._getImplementation("Resolution")(reference, context)

	def select( self ):
		return self._getImplementation("Selection")()

	def matchProcess( self, evaluable, process ):
		return self._getImplementation("MatchProcessOperation")(evaluable, process)

	def matchExpression( self, evaluable, expression ):
		return self._getImplementation("MatchExpressionOperation")(evaluable, expression)

	def iterate( self, evaluable, process ):
		return self._getImplementation("Iteration")(evaluable, process)

	def repeat( self, condition, process ):
		return self._getImplementation("Repetition")(condition, process)

	def access( self, target, _index ):
		return self._getImplementation("AccessOperation")(target, _index)
	
	def slice( self, target, _start, _end=None ):
		return self._getImplementation("SliceOperation")(target, _start, _end)

	def enumerate( self, start, end, step=None ):
		return self._getImplementation("Enumeration")(start, end, step)

	def returns( self, evaluable ):
		return self._getImplementation("Termination")(evaluable)
	
	def breaks( self ):
		return self._getImplementation("Breaking")()

	def exception( self, exception ):
		return self._getImplementation("Except")(exception)
	
	def intercept( self, tryProcess, catchProcess=None, finallyProcess=None ):
		return self._getImplementation("Interception")(tryProcess, catchProcess, finallyProcess)
	
	def embed(self, lang, code):
		return self._getImplementation("Embed")(lang,code)

	def embedTemplate(self, lang, code):
		return self._getImplementation("EmbedTemplate")(lang,code)
		
	def comment( self, content ):
		return self._getImplementation("Comment")(content)
	
	def doc( self, content ):
		return self._getImplementation("Documentation")(content)
	
	def annotation( self, name, content ):
		return self._getImplementation("Annotation")(name, content)
	
	# FIXME: RENAME TO SYMBOL
	def _ref( self, name ):
		return self._getImplementation("Reference")(name)

	def _slot( self, name, typeinfo=None ):
		return self._getImplementation("Slot")(name, typeinfo)

	def _arg( self, name, typeinfo=None, optional=False ):
		arg = self._getImplementation("Argument")(name, typeinfo)
		arg.setOptional(optional)
		return arg
	
	def _param( self, name=None, value=None, asList=False, asMap=False ):
		param = self._getImplementation("Parameter")(name,value)
		if asList: param.setAsList()
		if asMap:  param.setAsMap()
		return param

	def _ensureParam( self, value ):
		if isinstance(value, interfaces.IParameter):
			return value
		else:
			return self._param(None, value)

	def _attr( self, name, typeinfo=None, value=None):
		return self._getImplementation("Attribute")(name, typeinfo, value)

	def _classattr( self, name, typeinfo=None, value=None):
		return self._getImplementation("ClassAttribute")(name, typeinfo, value)

	def _moduleattr( self, name, typeinfo=None, value=None):
		return self._getImplementation("ModuleAttribute")(name, typeinfo, value)
	
	def _op( self, symbol, priority=0 ):
		return self._getImplementation("Operator")(symbol, priority)

	def _number( self, number ):
		return self._getImplementation("Number")(number)

	def _string( self, value ):
		return self._getImplementation("String")(value)

	def _list( self, *args ):
		r = self._getImplementation("List")()
		map(lambda a:r.addValue(a), args)
		return r

	def _dict( self ):
		return self._getImplementation("Dict")()
	

# EOF
