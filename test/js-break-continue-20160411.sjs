# DESCRIPTION: Break/continue in JavaScript have to work both
# with straight iterations and within closures wrapping an environment
# EXPECTS: <<<
# A 5
# A 6
# <<<

# The following is a straight JS iteration
for i in 0..10
	if i < 5 -> continue
	console log ("A", i)
	if i > 6 -> break
end

# The following closes over the value
var r = []
for i in 0..10
	if i < 5 -> continue
	r push {console log ("A", i)}
	if i > 6 -> break
end
r :: {_|_()}
