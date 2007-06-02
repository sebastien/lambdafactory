package lambdafactory;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;

public class Runtime {

	public static class BoundMethod {
		public String name;
		public Method[] methods;
		public java.lang.Object target;
		public BoundMethod( String name, java.lang.Object target, Method[] methods ) {
			this.name    = name;
			this.target  = target;
			this.methods = methods;
		}
		public final Method[] withArity( int a ) {
			Method[] list = new Method[methods.length];
			int j = 0;
			for ( int i=0 ; i<methods.length ; i++ ) {
				Method m = methods[i];
				if ( m.getParameterTypes().length == a ) {
					list[j++] = m;
				}
			}
			Method[] result = new Method[j];
			for ( int i=0 ; i<j ; i++ ) {
				result[i] = list[i];
			}
			return result;
		}
		public final java.lang.Object invoke(Method m, java.lang.Object[] args) {
			try {
				return m.invoke(target, args);
			} catch (InvocationTargetException e) {
				print("Error when invoking: " + e.toString());
				e.printStackTrace();
				return null;
			} catch (IllegalAccessException e) {
				print("Error when invoking: " + e.toString());
				e.printStackTrace();
				return null;
			}
		}
		public final java.lang.Object invoke(java.lang.Object[] args) {
			if ( methods.length == 1 ) {
				return this.invoke(methods[0], args);
			} else if ( methods.length == 0 ) {
				print("No method found");
				return null;
			} else {
				Method[] same_arity = this.withArity(args.length);
				if (same_arity.length == 1) {
					return this.invoke(same_arity[0], args);
				} else {
					print("Polymorphic dispatch not implemented");
					return null;
				}
			}
		}
	}

	public static final java.lang.Object _import( java.lang.Object c, String s ) {
		return null;
	}
	public static final java.lang.Object resolve( java.lang.Object o, String s ) {
		// FIXME:What about null fields ?
		java.lang.Object r = resolveField(o,s);
		if ( r != null ) { return r; }
		BoundMethod m = resolveMethod(o,s);
		if ( m != null ) { return m; }
		return null;
	}

	// UTILITY
	public static final Method[] methodsWithName( java.lang.Class c, String s ) {
		// TODO: This will have a huge performance impact
		Method[] methods = c.getMethods();
		Method[] list = new Method[methods.length];
		int j = 0;
		for ( int i=0 ; i<methods.length ; i++ ) {
			Method m = methods[i];
			if ( s.equals(m.getName()) ) {
				list[j] = m;
				j += 1;
			}
		}
		Method[] result = new Method[j];
		for ( int i=0 ; i<j ; i++ ) { result[i] = list[i]; }
		return result;
	}

	public static final java.lang.Object resolveField( java.lang.Object o, String s) {
		Field f = null;
		try {
			f = o.getClass().getField(s);
		} catch ( NoSuchFieldException e ) {
			// TODO: Fallback or warning
			return null;
		}
		try {
			return f.get(o);
		} catch ( IllegalAccessException e ) {
			// TODO: Fallback or warning
			return null;
		}
	}

	public static final BoundMethod resolveMethod( java.lang.Object o, String s) {
		java.lang.Class c;
		if ( ! (o instanceof java.lang.Class) ) { c = o.getClass(); }
		else { c = (java.lang.Class)o; }
		Method[] methods = methodsWithName(c,s);
		// If there is at least one method with a matching name, we return a
		// BoundMethod instance
		if ( methods != null && methods.length > 0 ) {
			return new Runtime.BoundMethod(s,o, methods);
		} else {
			return null;
		}
	}

	public static final java.lang.Object access( java.lang.Object value ) {
		return null;
	}
	public static final java.lang.Object invoke( java.lang.Object m, java.lang.Object[] args ) {
		// Here we have a set of methods
		if ( m instanceof BoundMethod ) {
			return ((BoundMethod)m).invoke(args);
		} else {
			print("Unknown invocable: " + m.toString());
			return null;
		}
	}
	public static final java.lang.Object getSlot( java.lang.Object o, String s ) {
		return null;
	}
	public static final java.lang.Object setSlot( java.lang.Object o, String s ) {
		return null;
	}
	public static final java.lang.Object respondsTo( java.lang.Object o, String s ) {
		return null;
	}
	public static final java.lang.Object respond( java.lang.Object o, String s, java.lang.Object[] a ) {
		return null;
	}
	public static final void print( java.lang.Object s ) {
		System.out.println(">> " + s.toString());
	}
	public static final void print( java.lang.Object s, java.lang.Object s1 ) {
		System.out.println(">> " + s.toString() + " "  + s1.toString());
	}
	public static final void print( java.lang.Object s, java.lang.Object s1, java.lang.Object s2 ) {
		System.out.println(">> " + s.toString() + " "  + s1.toString()+ " "  + s2.toString());
	}
	public static final java.lang.Object box( int i ) {
		return new Integer(i);
	}
	public static final java.lang.Object box( java.lang.Object o ) {
		return o;
	}
	public static final java.lang.Object computeAdd( java.lang.Object a, java.lang.Object b ) {
		if (a instanceof String || b instanceof String ) {
			return a.toString() + b.toString();
		} else if (a instanceof Number && b instanceof Number ) {
			if (a instanceof Double || b instanceof Double) {
				return new Double(((Number)a).doubleValue() + ((Number)b).doubleValue());
			}
			else if (a instanceof Float || b instanceof Float) {
				return new Float(((Number)a).floatValue() + ((Number)b).floatValue());
			}
			else {
				return new Integer(((Number)a).intValue() + ((Number)b).intValue());
			}
		} else {
			print("Unsupported operand types: ", a, b);
			return null;
		}
	}
	public static final java.lang.Object computeMultiply( java.lang.Object a, java.lang.Object b ) {
		if (a instanceof Number && b instanceof Number ) {
			if (a instanceof Double || b instanceof Double) {
				return new Double(((Number)a).doubleValue() * ((Number)b).doubleValue());
			}
			else if (a instanceof Float || b instanceof Float) {
				return new Float(((Number)a).floatValue() * ((Number)b).floatValue());
			}
			else {
				return new Integer(((Number)a).intValue() * ((Number)b).intValue());
			}
		} else {
			print("Unsupported operand types: ", a, b);
			return null;
		}
	}
}
