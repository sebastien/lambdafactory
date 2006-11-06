import interfaces

__doc__ = """
The *model writer* modules define a default program model to text conversion
class and a set of useful functions to help writing program model to text
translators.

Model writers can be used to convert a program model to source code in a
specific language. As writer are stateful, you can add many checkings and
transformations while writing a program, or parts of it.
"""

PREFIX = "\t"

def _format( value, level=-1 ):
	"""Format helper operation. See @format."""
	if type(value) in (list, tuple):
		res = []
		for v in value:
			if v is None: continue
			res.extend(_format(v, level+1))
		return res
	else:
		assert type(value) in (str, unicode)
		return ["\n".join((level*PREFIX)+v for v in value.split("\n"))]

def format( *values ):
	"""Formats a combination of string ang tuples. Strings are joined by
	newlines, and the content of the inner tuples gets indented"""
	return "\n".join(_format(values))

def _flatten(value, res):
	"""Flatten helper operation. See @flatten."""
	if type(value) in (tuple, list):
		for v in value:
			_flatten(v, res)
	else:
		res.append(value)

def flatten( *lists ):
	"""Flattens the given lists in a single list."""
	res = [] ; _flatten(lists, res)
	return res

class Writer:
	"""This is the default writer implementation that outputs a text-based
	program representation. You can call the main @write method to get the
	representatio of any model element."""

	def writeClass( self, classElement ):
		"""Writes a class element."""
		return self._format(
			"@class %s:" % (classElement.getName()),
			flatten([self.writeMethod(m) for m in classElement.getMethods()])
		)

	def writeMethod( self, methodElement ):
		"""Writes a method element."""
		return self._format(
			"@method %s ( %s ):" % (
				methodElement.getName(),
				", ".join(map(self.writeArgument, methodElement.getArguments()))
			), map(self.write, methodElement.getOperations())
		)

	def writeArgument( self, argElement ):
		"""Writes an argument element."""
		return "%s %s" % (
			(argElement.getTypeInformation() or "any"),
			argElement.getReferenceName(),
		)

	def writeOperator( self, operator ):
		"""Writes an operator element."""
		return "%s" % (operator.getReferenceName())

	def writeNumber( self, number ):
		"""Writes a number element."""
		return "%s" % (number.getActualValue())

	def writeAllocation( self, allocation ):
		"""Writes an allocation operation."""
		s = allocation.getSlotToAllocate()
		if s.getTypeInformation() is None: return None
		return "%s %s" % (
			s.getTypeInformation(),
			s.getReferenceName(),
		)

	def writeAssignation( self, assignation ):
		"""Writes an assignation operation."""
		return "%s = %s" % (
			assignation.getTargetReference().getReferenceName(),
			self.write(assignation.getAssignedValue())
		)

	def writeResolution( self, resolution ):
		"""Writes a resolution operation."""
		return "%s" % ( resolution.getReference().getReferenceName())

	def writeComputation( self, computation ):
		"""Writes a computation operation."""
		# FIXME: For now, we supposed operator is prefix or infix
		operands = computation.getOperands()
		operator = computation.getOperator()
		if len(operands) == 1:
			return "%s %s" % (
				self.write(operator),
				self.write(operands[0])
			)
		else:
			return "%s %s %s" % (
				self.write(operands[0]),
				self.write(operator),
				self.write(operands[1])
			)

	def writeInvocation( self, invocation ):
		"""Writes an invocation operation."""
		return "%s(%s)" % (
			self.write(invocation.getTarget()),
			", ".join(map(self.write, invocation.getArguments()))
		)

	def writeTermination( self, termination ):
		"""Writes a termination operation."""
		return "return %s" % ( self.write(termination.getReturnedEvaluable()) )

	def write( self, element ):
		res = None
		if element is None:
			pass
		elif isinstance(element, interfaces.IClass):
			res = self.writeClass(element)
		elif isinstance(element, interfaces.IMethod):
			res = self.writeMethod(element)
		elif isinstance(element, interfaces.IArgument):
			res = self.writeArgument(element)
		elif isinstance(element, interfaces.IOperator):
			res = self.writeOperator(element)
		elif isinstance(element, interfaces.INumber):
			res = self.writeNumber(element)
		elif isinstance(element, interfaces.IAllocation):
			res = self.writeAllocation(element)
		elif isinstance(element, interfaces.IAssignation):
			res = self.writeAssignation(element)
		elif isinstance(element, interfaces.IComputation):
			res = self.writeComputation(element)
		elif isinstance(element, interfaces.IInvocation):
			res = self.writeInvocation(element)
		elif isinstance(element, interfaces.IResolution):
			res = self.writeResolution(element)
		elif isinstance(element, interfaces.ITermination):
			res = self.writeTermination(element)
		else:
			raise Exception("No write method implemented for: %s" % (element))
		return res

	def _format( self, *values ):
		return format(*values)

# EOF
