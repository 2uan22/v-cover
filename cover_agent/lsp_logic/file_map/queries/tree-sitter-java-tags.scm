(class_declaration
  name: (identifier) @name.definition.class) @definition.class

(method_declaration
  name: (identifier) @name.definition.method) @definition.method

(method_invocation
  name: (identifier) @name.reference.call
  arguments: (argument_list) @reference.call)

(interface_declaration
  name: (identifier) @name.definition.interface) @definition.interface

; New query to find a method within an interface
(interface_declaration
  body: (interface_body
    (method_declaration
      name: (identifier) @name.definition.method.interface
    ) @definition.method.interface
  )
)

(type_list
  (type_identifier) @name.reference.implementation) @reference.implementation

(object_creation_expression
  type: (type_identifier) @name.reference.class) @reference.class

(superclass (type_identifier) @name.reference.class) @reference.class

(method_declaration) @test

(import_declaration) @import

; # TODO find a better name for this maybe
(class_literal) @dot.class
