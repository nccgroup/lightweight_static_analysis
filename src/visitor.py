import json
#from github import Github
import repostars
from collections import defaultdict
import ipdb
import sys
import ast_node
sys.setrecursionlimit(20000)

def print_node(node, repo, path):
    print("https://github.com/{}/blob/master/{}#L{}".format(repo,
        path, node.value["sourceSpan"]["start"][0]))


def match_node(ast_node):
    if isinstance(ast_node, ast_node.CallNode):
        return match_call(ast_node)
    else:
        return False

def is_req(ast_node):
    if isinstance(ast_node.value, dict) and "name" in ast_node.value.keys() and ast_node.value["name"] == "req":
        return True

def match_call(call_node):
    # called function is exec
    is_exec = False
    if call_node.callFunction["term"] == "Identifier":
        if call_node.callFunction["name"] == "exec":
            is_exec = True

    # First parameter is not a constant string
    is_not_string = False
    if len(call_node.callParams) > 0 and call_node.callParams[0].value["term"] != "TextElement":
        is_not_string = True

    return is_exec and is_not_string

class Visitor(object):
    def __init__(self, repo, path):
        self.repo = repo
        self.path = path

        # Dictionary of nodes to children
        self.tree = defaultdict(list)

        # Dictionary of nodes to parents
        self.revtree = dict()

        self.root = None

        self.sources = set()
        self.sinks = set()

        # Value -> variable name
        self.assignments = dict()

        self.tainted_vars = set()

        self.visit_count = 0

    # Return all of the class nodes we've parsed
    def class_nodes(self):
        return [x for x in self.tree if type(x) is ast_node.ClassNode]

    # Run func on each class
    def each_class(self, func):
        for c in self.class_nodes():
            func(c)

    def build(self, json_node, parent_ast_node):
       # Construct the node
        new_ast_node = ast_node.buildNode(json_node)

        if not self.root:
            # Empty tree, set the root
            self.root = new_ast_node
            parent_ast_node = None
        else:
            # Add links in tree
            if parent_ast_node != None:
                self.tree[parent_ast_node].append(new_ast_node)
            self.revtree[new_ast_node] = parent_ast_node

        # Visit all of the child nodes
        for child in new_ast_node.children():
            self.build(child, new_ast_node)

    def visit(self, ast_node):
        if self.visit_count > 100000:
            return

        self.visit_count += 1
        # If assignment
        if isinstance(ast_node, ast_node.AssignmentNode):
            # if source is subtree sink
            if self.subtree_source(ast_node):
                if isinstance(ast_node.destination, ast_node.IdentifierNode):
                    self.tainted_vars.add(ast_node.destination)

        if match_node(ast_node):
            self.sinks.add(ast_node)
            if ast_node.callParams[0] in self.tainted_vars:
                print_node(ast_node, self.repo, self.path)

        for child in self.tree[ast_node]:
            self.visit(child)

    def subtree_source(self, ast_node):
        is_source = False

        if isinstance(ast_node, ast_node.IdentifierNode):
            if ast_node.name == "req":
                return True

        for child in self.tree[ast_node]:
            is_source = is_source or self.subtree_source(child)

        return is_source
