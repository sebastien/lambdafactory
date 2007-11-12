# BUG: Writer outputs x:__this__.getClass().X.A0 instead of x:A.X.A0
@class A
	@shared   X = {A0:1,A1:2,A2:3}
	@property x = X A0
@end
