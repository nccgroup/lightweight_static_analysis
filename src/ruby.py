import ipdb

# Simple heuristic to that returns if a class is likely a controller class
# i.e. the pretty printed class name ends with "Controller"
def is_controller_class(class_ast_node):
    return class_ast_node.pprint().endswith("Controller")

# Returns a dict of
# {
#   "superclass name" => [array of ClassNode objects that inherit from it]
# }
def group_controllers_by_superclass(visitors):
    result = {}
    for v in visitors:
        for klass in v.class_nodes():

            # Filter out non controller classes
            if not is_controller_class(klass):
                continue

            superclass_name = ""
            if klass.classSuperClass is not None:
                superclass_name = klass.classSuperClass.pprint()

            if superclass_name in result:
                result[superclass_name].append(klass)
            else:
                result[superclass_name] = [klass]

    return result

# Returns a dict of
# {
#   "before_action name" => [array of ClassNode objects that use that before action]
# }
def group_controllers_by_before_action(visitors):
    result = {}
    for v in visitors:
        for klass in v.class_nodes():
            # Filter out non controller classes
            if not is_controller_class(klass):
                continue

            for before_action in before_actions(klass):
                ba_name = before_action.sendArgs[0].pprint()
                #ipdb.set_trace()
                #print("handling before action")
                if ba_name in result:
                    result[ba_name].append(klass)
                else:
                    result[ba_name] = [klass]

    return result

# For rails controllers, a `before_action` dictates a function that will be called before
# all (or some subset) of actions
#
# semantic represents as `before_action` calls as SendNodes
#
# Return the set of SendNodes representing before_actions on the provided
# ClassNode
def before_actions(class_node):
    return [x for x in class_node.send_nodes if
        type(x.sendSelector) is visitor.IdentifierNode and
        x.sendSelector.name == "before_action"]

def before_action(before_action_name, class_node):
    send_node = [x for x in before_actions(class_node) if x.sendArgs[0].pprint() == before_action_name]
    if len(send_node) > 1:
        print("[!] Warning: more than 1 send node matched in methods_affected_by_before_action")
        print(send_node)
    return send_node[0] # usually there should just be one with a given name

# Given a ClassNode and SendNode representing a before_acion in Rails,
# returns all of the MethodNodes on the ClassNode affected by the
# provided before action (ba_send_node)
#
# That is, this method knows how to interpret `only:` and `except:` args passed
# to `before_action`
#
# See the docs for before filters here:
# https://guides.rubyonrails.org/action_controller_overview.html#filters
#
# Note: this method does not attempt to handle edge cases or  idiosyncrasies of
# how Rails filters work, like:
#   "Calling the same filter multiple times with different options will not work,
#    since the last filter definition will overwrite the previous ones."
def methods_affected_by_before_action(before_action_name, class_node):
    methods_affected, methods_ignored = [], []

    all_methods = ruby_public_methods(class_node)
    send_node = before_action(before_action_name, class_node)

    send_args = send_node.sendArgs[1:]
    # We only care about "except" and "only" as they indicate which methods the
    # before_action is applied to.
    # - "unless" calls another method and is ignored here
    try:
        relevant_send_args = [x for x in send_args if
            # sometimes the second before_action arg is the name of another
            # method to call, a la:
            #      before_action :find_rubygem_by_name, :set_url, except: :index
            # for our uses here we want to ignore those (we only care about
            # except and only), so filter by node type
            type(x) is visitor.KeyValueNode and
            x.node_key.pprint() in ["except", "only"]]
    except:
        ipdb.set_trace()
        print("exception in rel send args")

    len_send_args = len(relevant_send_args)

    if len_send_args == 0:
        methods_affected = all_methods
        #ipdb.set_trace()
        #print("[+] No args passed to before_action, apply to all methods")
    elif len_send_args > 1:
        ipdb.set_trace()
        print("[+] More than 1 arg passed to before_action, need to handle this")
    else:
        # Handle the passed args (e.g. only:, except:)
        arg = relevant_send_args[0]
        method_names_specified = method_name_list_from_kv_arg(arg)

        key = arg.node_key.pprint()
        if key == 'only':
            for m in all_methods:
                if m.methodName.pprint() in method_names_specified:
                    methods_affected.append(m)
                else:
                    methods_ignored.append(m)

        elif key == 'except':
            for m in all_methods:
                if m.methodName.pprint() in method_names_specified:
                    methods_ignored.append(m)
                else:
                    methods_affected.append(m)
        elif key == 'unless':
            pass # ignore for now
        else:
            ipdb.set_trace()
            print("Unknown before_action key")

    return [methods_affected, methods_ignored]

# For before_actions, when the `only` or `except` keywords are used,
# the variables to apply the before_action to can be either a single
# symbol:
#   before_action :some_action, only: :index
# or an array:
#   before_action :some_action, only: %i[create destroy]
#
# This method will handle both cases and return a list of the methods listed
# (removing the ":" before symbols)
def method_name_list_from_kv_arg(kv_node):
    value_type = type(kv_node.node_value)
    if value_type is visitor.SymbolElementNode:
        # use sub to strip off the symbol ':'
        return [ kv_node.node_value.pprint().replace(":", "") ]
    elif value_type is visitor.ArrayNode:
        result = []
        for cur_node in kv_node.node_value.values:
            if type(cur_node) is visitor.SymbolElementNode:
                result.append(cur_node.pprint().replace(":", ""))
            else:
                ipdb.set_trace()
                print("non symbol in array")
        return result
    else:
        ipdb.set_trace()
        print("non symbol element")
        return []

# Given a Ruby ClassNode object, return a list of its public MethodNodes
#
# The reason we have to do this is semantic by default returns all MethodNodes
# as `access_control="Public"`, so we have to find the LOC where the `private`
# keyword is used and only return methods defined before that.
def ruby_public_methods(class_node):
    private_node = class_node.send_by_name("private")
    if len(private_node) == 0:
        return class_node.method_nodes
    else:
        private_start_loc = private_node[0].start_loc()
        return [x for x in class_node.method_nodes if x.start_loc() < private_start_loc]

def print_class_before_action_info(before_action_name, class_node):
    methods_affected, methods_ignored = methods_affected_by_before_action(before_action_name, class_node)
    methods_affected_names = [x.methodName.pprint() for x in methods_affected]
    methods_ignored_names = [x.methodName.pprint() for x in methods_ignored]

    return "{} || methods_affected = {} | methods_ignored = {}".format(
        class_node.classIdentifier.pprint(),
        ", ".join(methods_affected_names),
        ", ".join(methods_ignored_names))