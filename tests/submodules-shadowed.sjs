# TEST: Ensures that importing a module that has the same local name
# as the current module does not introduce any conflict.
@module sub.module.app
@import app
@import A from app
@class B: A
@end
