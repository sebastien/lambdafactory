# We expect A, B and C to be resolved as m.A, m.B, m.C without
# any error, as this assumes the module is incomplete. Of course, that
# would not work if type information was required.
@module m
@import A,B,C from m
@function f
	console log (A, B, C)
@end
