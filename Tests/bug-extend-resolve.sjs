# BUG: values is resolved in extend, not as an argument of the iteration
# EXPECTS <<<
# a1 1
# a2 2
# b1 1
# b2 2
# <<<
for values, category in {a:{a1:1, a2:2},b:{b1:1,b2:2}}
	for v,k in values
		console log (k,v)
	end
end
