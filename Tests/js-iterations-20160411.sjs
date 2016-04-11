# DESCRIPTION: This test cases shows how for/while loops are converted to JavaScript,
# creating extra nested scopes whenever necessary.

@function regularLoops
	var r = []
	var i = 0

	r = []
	while i < 10
		r push (i)
	end
	r :: {_|console log (_)}

	# NOTE: This should be written as a regular for-loop, and the range
	# should be written as-is
	r = []
	for v in 0..10
		r push (v)
	end
	r :: {_|console log (_)}

	# NOTE: This should be written as a regular for-loop
	r = []
	for v in [0,1,2]
		r push (v)
	end
	r :: {_|console log (_)}

	# NOTE: This should be written as a regular for-loop
	r = []
	for v in [0,1,2]
		r push ({return v}())
	end
	r :: {_|console log (_)}

	i = 0
	r = []
	while i < 10
		r push (i)
		i += 1
	end
	r :: {_|console log (_)}

@end

@function enclosedLoops
	var r = []
	var i = 0

	for v in 0..10
		r push {print (v)}
	end

	for v in [0,1,2]
		r push {print (v)}
	end

	for v in [0,1,2]
		r push ({return v})
	end

	var i = 0
	while i < 10
		r push ({_|return i})
		i += 1
	end

@end

