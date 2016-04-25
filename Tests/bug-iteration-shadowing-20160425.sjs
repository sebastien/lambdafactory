# BUG: In the `for` loop, `value` is not recognized as shadowing the parameter.
# EXPECTS <<<
# 1: 1
# 1: 2
# 1: 3
# 2: 1
# 2: 2
# 2: 3
# <<<
var value={values:[1,2,3]}
for value in value values
	console log ("1:", value)
end
for  value in value values
	console log ("2:", value)
end
