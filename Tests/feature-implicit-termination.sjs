# DESCRIPTION: This tests the feature of automatically returning the last
# value.
@function a1
@end

@function a2
	a
@end

@function a3
	[1,2,3]
@end

@function a4
	if a > 10
		1
	else
		2
	end
@end

@function a5
	var i = 0
	while i < 0
		i += 1
	end
@end

@function a5
	var i = 0
	for i in 0..10
		i += 1
	end
@end

@function a6
	{return 10}
@end

@function a7
	{return 10}()
@end

@function a8
	var r = 1
@end

@function a8
	pass
@end

@function a8
	try
		f()
	catch e
		False
	end
@end
