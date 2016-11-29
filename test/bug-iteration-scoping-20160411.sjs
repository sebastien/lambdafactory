# DESCRIPTION: at some point, the wrapping of nested function
# included out-of-scope references like `True`. For instance:
#	r.push((function(i, i, True, j){return (	function(){
#			if ( (i > 10) )
#				return i
#			else
#				return j
#		})}(i, i, True, j)))
# What we expect is  that top-level symbols are excluded from the enclosing,
# and that duplicate enclosings are filtered out.
var r = []
var i =0
for _ in 0..10
	var j = _ + 30
	r push {
		if i > 10
			return i
		else
			return j
		end
	}
end
