import modelbase

# We try to model this:
#
# class MyClass: 
#     method doThis( a, b, c )
#        value := a + b
#        return c(value)
#     end
# end

# class MyClass {
#    doThis( a, b, c ) {
#       var value = a + b
#       return c(value)
#    }
# }
f             = modelbase.Factory(modelbase)
class_myClass = f.createClass("MyClass")
method_doThis = f.createMethod("doThis", (f._arg("a"),f._arg("b"), f._arg("c")))
method_doThis.addOperations(
	f.allocate(f._slot("value")),
	f.assign(f._ref("value"), f.compute(f._op("+"), f.resolve(f._ref("a")), f.resolve(f._ref("b")))),
	# We could write the above line as
	f.assign(f._ref("value"), f.compute(f._op("+"), f.resolve(f._ref("a")), f.resolve(f._ref("b")))),
	f.returns(f.invoke(f.resolve(f._ref("c")), (f.resolve(f._ref("value")))))
)
class_myClass.setSlot("doThis", method_doThis)

from modelwriter import Writer
w = Writer()
print w.writeClass(class_myClass)

# We proceed with the evaluation of this model
# context = Context({"a":f._value(Unknown, mt.Number), "b":f._value(Unknown, mt.Number),
# "c":f._value(Unknown, mt.Function( mt.Number, mt.Number ))})
