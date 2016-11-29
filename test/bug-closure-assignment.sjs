@function run times, callback
	0..times :: callback
@end

for i in 0..5
	var c = 0
	run (100, {
		c += 1
	})
	console log (c)
end
