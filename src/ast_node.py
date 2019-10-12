import json
import ipdb

# Gradual AST parsing representation
# Use generic values for everything we aren't interested in.
# Overparsed.
class AstNode(object):
    def __init__(self, value):
        # Generic, unparsed AST node.
        self.value = value

    def children(self):
        if isinstance(self.value, dict):
            for k in self.value.keys():
                yield self.value[k]
        elif isinstance(self.value, list):
            for i in self.value:
                yield i
        else:
            return None

    def pprint(self):
        return str(self)

    # Return the LOC where this AST node starts
    def start_loc(self):
        return self.value['sourceSpan']['start'][0]

    # Return the LOC where this AST node ends
    def end_loc(self):
        return self.value['sourceSpan']['end'][0]

class CallNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node

        # The name function being called
        self.callFunction = json_node["callFunction"]

        # Parameters of the function call
        self.callParams = [buildNode(x) for x in json_node["callParams"]]

        # ???
        self.callContext = json_node["callContext"]

        # Source code stuff. We should parse this out.
        self.sourceRange = json_node["sourceRange"]
        self.sourceSpan = json_node["sourceSpan"]

        # ???
        self.callBlock = json_node["callBlock"]

class AssignmentNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node

        self.source = buildNode(json_node["assignmentValue"])
        self.destination = buildNode(json_node["assignmentTarget"])

class ClassNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node

        # Source code stuff. We should parse this out.
        self.sourceRange = json_node["sourceRange"]
        self.sourceSpan = json_node["sourceSpan"]


        self.classIdentifier = buildNode(json_node['classIdentifier']) #['name']

        # Not every class has a parent class. Use "None" if not present,
        # not sure how best to handle this.
        if json_node['classSuperClass'] is not None:
            self.classSuperClass = buildNode(json_node['classSuperClass'])
        else:
            self.classSuperClass = None

        # Send nodes represent top-level method calls, see class definition for details
        self.send_nodes = []

        # Corresponds to methods defined in the class
        self.method_nodes = []

        # print_helper(json_node['classBody']['children'])
        if 'children' in json_node['classBody']:
            for cur_child in json_node['classBody']['children']:
                node = buildNode(cur_child)
                self.add_send_or_method_node(node, cur_child['term'])

        elif isinstance(json_node['classBody'], dict) and 'term' in json_node['classBody']:
            self.add_send_or_method_node(buildNode(json_node['classBody']), json_node['classBody']['term'])



    # Given a node object, add it to the appropriate instance var is it's a SendNode or MethodNode
    def add_send_or_method_node(self, node, term):
        if term == 'Send':
            self.send_nodes.append(node)
        elif term == 'Method':
            self.method_nodes.append(node)

    # Returns all method nodes on this class whose name match the provided name
    # Note: returns a list
    def method_by_name(self, name):
        methods = [x for x in self.method_nodes if x.methodName.pprint() == name]

        if len(methods) > 1:
            print("Warning: more than one method defined on class with name={}".format(name))

        return methods

    def send_by_name(self, name):
        sends = [x for x in self.send_nodes if x.sendSelector.pprint() == name]

        if len(sends) > 1:
            print("Warning: more than one send on class with name={}".format(name))
            print(self)

        return sends

    def __repr__(self):
        return "<ClassNode name={} superclass={}>".format(self.classIdentifier, self.classSuperClass)

    def pprint(self):
        try:
            klass = ""
            super_klass = ""

            if type(self.classIdentifier) is ThisNode:
                klass = "this"
            else:
                klass = self.classIdentifier.pprint()

            if self.classSuperClass is not None:
                super_klass = "< {}".format(self.classSuperClass.pprint() )

            return "{} {}".format(klass, super_klass)
        except:
            ipdb.set_trace()
            print("exception pprint ClassNode")

class MethodNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node

        self.methodName = buildNode(json_node['methodName'])
        self.methodReceiver = buildNode(json_node['methodReceiver'])

        if type(self.methodReceiver) is AstNode:
            ipdb.set_trace()
            print("unknown receiver")

        self.methodAccessControl = json_node['methodAccessControl']

        self.methodParameters = [buildNode(x) for x in json_node['methodParameters']]

        if len(json_node['methodContext']) != 0:
            ipdb.set_trace()
            print("params")
            self.methodContext = "cat"

        # self.methodBody = TODO

        # Hack to store before_actions for Rails controller methods
        self.before_actions = []

    def __repr__(self):
        return "<Method name={} access_control={} methodReceiver={} methodParameters={}>".format(self.methodName,
            self.methodAccessControl, self.methodReceiver, self.methodParameters)


    def pprint(self):
        try:
            return "{}({})".format(self.methodName.pprint(), ", ".join([x.pprint() for x in self.methodParameters]))
        except:
            ipdb.set_trace()
            print("method __repr__")

class FunctionNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.functionName = buildNode(json_node['functionName'])

        if json_node['functionContext'] == []:
            self.functionContext = []
        else:
            self.functionContext = buildNode(json_node['functionContext'])

        self.functionParameters = [buildNode(x) for x in json_node['functionParameters']]

        if 'children' in json_node['functionBody']:
            self.functionBody = [buildNode(x) for x in json_node['functionBody']['children']]
        else:
            self.functionBody = buildNode(json_node['functionBody'])

        #ipdb.set_trace()
        #print("function")
    def __repr__(self):
        return "<Function name={} functionContext={} functionParameters={}>".format(self.functionName,
            self.functionContext, self.functionParameters)

    #def pprint(self):
    #    return ""

# Used by Rails superclass when it's ActionController::Base
class ScopeResolutionNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node

        # There will be a list of identifiers
        self.identifiers = []
        for cur in json_node['scopes']:
            cur_node = buildNode(cur)
            if type(cur_node) is AstNode:
                print(cur)
                ipdb.set_trace()

            self.identifiers.append(cur_node)

    def pprint(self):
        return "::".join([x.pprint() for x in self.identifiers])

    def __repr__(self):
        return "<ScopeResolutionNode {}>".format(self.identifiers)

# Top-level method calls, like:
#   include Clearance::Authorization
#   rescue_from ActiveRecord::RecordNotFound, with: :render_not_found
#   before_action :set_locale
class SendNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node

        if json_node['sendReceiver'] is not None:
            self.sendReceiver = buildNode(json_node['sendReceiver'])
        else:
            self.sendReceiver = ""

        self.sendSelector = buildNode(json_node['sendSelector'])
        self.sendBlock = buildNode(json_node['sendBlock'])
        self.sendArgs = [buildNode(x) for x in json_node['sendArgs']]

        for arg in self.sendArgs:
            if type(arg) is AstNode:
                print(json_node['sendArgs'])
                print()
                print(arg.value)
                print()
                print_helper(arg.value)
                ipdb.set_trace()
                print("unknown SendNode sendArg type")

    def __repr__(self):
        return "<SendNode \n  sendReceiver={}\n  sendSelector={}\n  sendArgs={}>".format(self.sendReceiver, self.sendSelector, self.sendArgs)

    def pprint(self):
        rec = ""
        if self.sendReceiver:
            try:
                rec = self.sendReceiver.pprint() + "."
            except:
                ipdb.set_trace()
                print("except sendReceiver")

        return "{}{} [{}]".format(rec, self.sendSelector.pprint(),
            ", ".join([x.pprint() for x in self.sendArgs]))

class IdentifierNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.name = json_node["name"]

    def __eq__(self, other):
        if not other:
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "<IdentifierNode name={}>".format(self.name)

    def pprint(self):
        return self.name

class SymbolElementNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.symbolContent = json_node["symbolContent"]

    def __repr__(self):
        return "<SymbolElementNode symbolContent={}>".format(self.symbolContent)

    def pprint(self):
        return self.symbolContent

class KeyValueNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node

        self.node_key = buildNode(json_node['key'])
        self.node_value = buildNode(json_node['value'])

        if type(self.node_key) is AstNode:
            print(json_node['key'])
            print_helper(json_node['key'])
            ipdb.set_trace()
            print("KeyValueNode - node_key")

        if type(self.node_value) is AstNode:
            print(json_node['value'])
            print_helper(json_node['value'])
            ipdb.set_trace()
            print("KeyValueNode - node_value")

    def __repr__(self):
        return "<KeyValueNode key={} value={}>".format(self.node_key, self.node_value)

    def pprint(self):
        middle = "{} => {}".format(self.node_key.pprint(), self.node_value.pprint())
        return "{ " + middle + " } "

class EmptyNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node

    def __repr__(self):
        return "<EmptyNode>"

class ThisNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node

    def __repr__(self):
        return "<ThisNode>"

class ArrayNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.values = [buildNode(x) for x in json_node['arrayElements']]

    def __repr__(self):
        return "<ArrayNode values={}>".format(self.values)

    def pprint(self):
        return "[{}]".format(", ".join([x.pprint() for x in self.values]))

class IntegerNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.integerContent = json_node['integerContent']

    def __repr__(self):
        return "<IntegerNode integerContent={}>".format(self.integerContent)

class HashNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.hashElements = [buildNode(x) for x in json_node['hashElements']]

    def __repr__(self):
        return "<HashNode hashElements={}>".format(self.hashElements)

class TextElementNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.textElementContent = json_node['textElementContent']

    def __repr__(self):
        return "<TextElementNode textElementContent={}>".format(self.textElementContent)

class StringNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.stringElements = [buildNode(x) for x in json_node['stringElements']]

    def __repr__(self):
        return "<StringNode stringElements={}>".format(self.stringElements)

class InterpolationElementNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.interpolationBody = buildNode(json_node['interpolationBody'])

    def __repr__(self):
        return "<InterpolationElementNode interpolationBody={}>".format(self.interpolationBody)

class SubscriptNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.lhs = buildNode(json_node['lhs'])
        self.rhs = [buildNode(x) for x in json_node['rhs']]

    def __repr__(self):
        return "<SubscriptNode lhs={} rhs={}>".format(self.lhs, self.rhs)

class PlusNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.lhs = buildNode(json_node['lhs'])
        self.rhs = buildNode(json_node['rhs'])

    def __repr__(self):
        return "<PlusNode lhs={} rhs={}>".format(self.lhs, self.rhs)

class MinusNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.lhs = buildNode(json_node['lhs'])
        self.rhs = buildNode(json_node['rhs'])

    def __repr__(self):
        return "<MinusNode lhs={} rhs={}>".format(self.lhs, self.rhs)

class OrNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.lhs = buildNode(json_node['lhs'])
        self.rhs = buildNode(json_node['rhs'])

    def __repr__(self):
        return "<OrNode lhs={} rhs={}>".format(self.lhs, self.rhs)

class BooleanNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.booleanContent = json_node['booleanContent']

    def __repr__(self):
        return "<BooleanNode booleanContent={}>".format(self.booleanContent)

class NullNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node

    def __repr__(self):
        return "<NullNode>"

class RegexNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.regexContent = json_node['regexContent']

    def __repr__(self):
        return "<RegexNode regexContent={}>".format(self.regexContent)

class EnumerationNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.enumerationStart = buildNode(json_node['enumerationStart'])
        self.enumerationStep = buildNode(json_node['enumerationStep'])
        self.enumerationEnd = buildNode(json_node['enumerationEnd'])

    def __repr__(self):
        return "<EnumerationNode enumerationStart={} enumerationStep={} enumerationEnd={}>".format(
            self.enumerationStart, self.enumerationStep, self.enumerationEnd)

# Generic AstNode representing when there's a dict with the following attributes:
# - children, sourceSpan, and sourceRange
class ParentNode(AstNode):
    def __init__(self, json_node):
        self.value = json_node
        self.children_nodes = [buildNode(x) for x in json_node['children']]

    def __repr__(self):
        return "<ParentNode children_nodes={}>".format(self.children_nodes)


# Given a json node, simply print:
# term - [list of keys]
def print_helper(json_node, already_iterated = False):
    term = ""
    if 'term' in json_node:
        term = json_node['term']

    if isinstance(json_node, dict):
        print("{} - {}".format(term, json_node.keys()))
    elif isinstance(json_node, list):
        if not already_iterated:
            for cur in json_node:
                print_helper(cur, True)

def buildNode(json_node):
    if isinstance(json_node, dict):
        if "term" in json_node.keys():
            if json_node["term"] == "Call":
                return CallNode(json_node)
            elif json_node["term"] == "Identifier":
                return IdentifierNode(json_node)
            elif json_node["term"] == "Assignment":
                return AssignmentNode(json_node)
            elif json_node["term"] == "Class":
                return ClassNode(json_node)
            elif json_node["term"] == "ScopeResolution":
                return ScopeResolutionNode(json_node)
            elif json_node["term"] == "Send":
                return SendNode(json_node)
            elif json_node["term"] == "SymbolElement":
                return SymbolElementNode(json_node)
            elif json_node["term"] == "KeyValue":
                return KeyValueNode(json_node)
            elif json_node["term"] == "Method":
                return MethodNode(json_node)
            elif json_node["term"] == "Empty":
                return EmptyNode(json_node)
            elif json_node["term"] == "This":
                return ThisNode(json_node)
            elif json_node["term"] == "Array":
                return ArrayNode(json_node)
            elif json_node["term"] == "Integer":
                return IntegerNode(json_node)
            elif json_node["term"] == "Function":
                return FunctionNode(json_node)
            elif json_node["term"] == "Hash":
                return HashNode(json_node)
            elif json_node["term"] == "TextElement":
                return TextElementNode(json_node)
            elif json_node["term"] == "String":
                return StringNode(json_node)
            elif json_node["term"] == "InterpolationElement":
                return InterpolationElementNode(json_node)
            elif json_node["term"] == "Subscript":
                return SubscriptNode(json_node)
            elif json_node["term"] == "Boolean":
                return BooleanNode(json_node)
            elif json_node["term"] == "Null":
                return NullNode(json_node)
            elif json_node["term"] == "Regex":
                return RegexNode(json_node)
            elif json_node["term"] == "Plus":
                return PlusNode(json_node)
            elif json_node["term"] == "Enumeration":
                return EnumerationNode(json_node)
            elif json_node["term"] == "Minus":
                return MinusNode(json_node)
            elif json_node["term"] == "Or":
                return OrNode(json_node)
        elif 'children' in json_node:
            return ParentNode(json_node)

    return AstNode(json_node)
