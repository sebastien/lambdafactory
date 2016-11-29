λ-factory, to-do list
=====================

High-priority
=============

N/A

Nice to have
============

[ ] Check: pass should have a constructor
[ ] Check: parent class not resolved
[ ] Check: function/method redefined


Notes/Ideas
===========

Core modules
------------

The original idea was that `extend` would be the base for a cross-platform
λ-factory. Here is a quick list of the main operations taht would be
needed as part of a common runtime.

Core functions/predicates

	- like
	- isa
	- isinstance
	 
Conversion:

	- describe
	- string
	- list
	- tuple

Manipulation/Introspection:

	- getSlot
	- hasSlot
	- setSlot
	- keysOf
	- slotsOf
	- methodsOf
	- propertiesOf
	- operationsOf
	- sharedOf
	- classOf
	- typeOf

Functional arithmetic operators:

	- add
	- mul
	- div
	- mod
	- sub
	- ceil
	- floor
	- round
	- random
	- sin
	- cos
	- PI

Functional programming:

	- car
	- cdr
	- map
	- filter
	- reduce
	- fold

Self-hosting
------------

Strategy for making LambdaFactory self-hosted:

 - Parallel re-implementation
 - Rewrite Interfaces first, with a proper hierarchy and S-Expressions support
 - Properly model the relations between Element, DataFlow (Scope), Types
   (Abstract=typecast,Concrete=Element,Info=Type Description elements)
 - Implement modelbase after the interfaces
 - Write a small S-Expression parser to create modelbases
 - Design a flexible "pass" module, with "traits" that can be assigned to 
 - Front-End and Back-Ends easily integrated into LF
 - Common command-line interface
 - Importance of elements name: some are (classes, functions, modules), some
   aren't (program, closure, iterations, selection, etc)
 - Importations should go into the module "meta" (like version and stuff), and
   not into module init

Conceptual model
----------------

Ideas

- A program is composed of elements (''program model elements'')

- Each element represents either a structural (program, module, class, block),
  procedural (closure, functions, methods), operational (conditionals,
  repetitions, instanciations) or state-related (globals, variables,
  attributes) element.

- Each element has an associated abstract type, and an associated concrete
  type, which may be itself. For instance, the concrete type of a 'Class'
  program element is the program element itself (or is it ?)

Add a resolution scheme:

 - Program, Scope
   Program uses Namespace (modules)
   Scope uses the context (and dataflow)

 - Resolution should happen for a specific operation: if the resolved symbol is
   declared later in the current scope or a child scope, then it may not be
   available (see 'bug-scoping.sg' in Sugar)

```
    [Abstract Type] <------+
        |                  |
        |                  |
        |                  |
        |   +-------[Dataflow Slot]
        |   |              |
        |   |              |
        |   v              |
    [Element] ------> [Dataflow] <---+
        |                            |
        |                            |
    (is process)                  (alter)
        |                            |
        |                            |
        +---> [Operations] ----------+
                   |
                   (when evaluable)
                   |
            [Result Abstract Type]
```

Refactoring
-----------

```
lambdafactory                      (main package)

    main.spy                       (main, command-line interface)

    core                           (the core)
        environment.spy            (aggregates interfaces, passes, etc)
        interfaces.spy             (program model interface)
        model.spy                  (default model implementation)
        types.spy                  (the type system)

    passes                         (transformation passes)
        writing.py                 (writing passes)
        resolving.spy              (add dataflow pass)
        typing.spy                 (add type information pass)
        async.spy                  (rewrite asynchronous invocations)
        sdoc.spy                   (create documentation)
        uml.spy                    (UML diagram)

    tools
        splitter.spy               (Splitter utility)

    languages                      (available languages)

        javascript
            runtime/               (language-specific files)
                  runtime.js       (specific runtime library)
                  ...
            importer.spy           (importing mechanisms)
            writer.spy             (code generation)
            reader.spy             (source code reading)
            runner.spy             (interpreter/compiler wrapper)
            interfaces.spy         (additional interfaces)

        actionscript               (ActionScript back-end)
            runtime.as
            importer.spy
            writer.spy
            runner.spy

        python                     (Python back-end)
            runtime.py
            importer.spy
            writer.spy
            runner.spy

        sugar                      (Sugar front-end and back-end)
            reader.spy
            writer.spy
            runner.spy

      library                       (default lambda-factory library)
          core                      (core module)
             datatypes.sg           (core.datatypes module)
             operations.sg          (core.operations module)
          ...
```
