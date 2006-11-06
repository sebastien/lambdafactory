# Encoding: ISO-8859-1
# vim: ts=4 tw=79 noet 

import typecast

class Data:pass
class Operations: 	pass
class Structure: pass
class Behaviour: pass
class Runtime: pass

Nil                            = typecast.Nil
Nothing                        = typecast.Nothing
Any                            = typecast.Any
Rest                           = typecast.Rest
Unresolved                     = typecast.Unresolved

Data.Char                      = typecast.Cell(typecast.bits(8))
Data.Integer                   = typecast.Cell(typecast.bits(32))
Data.UnsignedInteger           = typecast.Cell(typecast.bits(32))
Data.Long                      = typecast.Cell(typecast.bits(64))
Data.Float                     = typecast.Cell(typecast.bits(32))
Data.Double                    = typecast.Cell(typecast.bits(64))
Data.String                    = typecast.Array(Data.Char)

Operations.Operation           = typecast.Context("Operation")
Operations.Computation         = Operations.Operation.subtype("Computation")
Operations.Casting             = Operations.Operation.subtype("Casting")
Operations.Allocation          = Operations.Operation.subtype("Allocation")

Structure.Context              = typecast.Context("Context")
Structure.Program              = Structure.Context.subtype("Program")
Structure.Module               = Structure.Context.subtype("Module")
Structure.Class                = Structure.Context.subtype("Class")

Behaviour.Function             = typecast.Process()
Behaviour.Method               = typecast.Process()

Runtime.Instance               = typecast.Context()

def classToType( aclass ):
	name = aclass.__name__

# EOF
