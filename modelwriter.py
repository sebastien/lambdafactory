PREFIX = "\t"

def _format( value, level=-1 ):
	if type(value) in (list, tuple):
		res = []
		for v in value:
			res.extend(_format(v, level+1))
		return res
	else:
		assert type(value) in (str, unicode)
		return [level*PREFIX + value]

def format( *values ):
	"""Formats a combination of string ang tuples. Strings are joined by
	newlines, and the content of the inner tuples gets indented"""
	return "\n".join(_format(values))

def _flatten(value, res):
	if type(value) in (tuple, list):
		for v in value:
			_flatten(v, res)
	else:
		res.append(value)

def flatten( *lists ):
	res = [] ; _flatten(lists, res)
	return res

class Writer:

	def writeClass( self, classElement ):
		return format(
			"class %s:" % (classElement.getName()),
			flatten([self.writeMethod(m) for m in classElement.getMethods()])
		)

	def writeMethod( self, methodElement ):
		return format(
			"method %s (...):" % (methodElement.getName()),
		)

	def writeAllocation( self, methodElement ):
		pass

	def write( self, element ):
		if isinstance(element, IAllocation):
			self.writeAllocation(element)

