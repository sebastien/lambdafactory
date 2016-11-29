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
	if value == 10
		value = 5
	else
		value = value
	end
	console log ("2:", value)
	console log ("2.1:", value)
	console log ("2.3:", value)
end
for  value in value values
	var r = {
		console log ("2:", value)
		console log ("2.1:", value)
		console log ("2.3:", value)
	}
end
