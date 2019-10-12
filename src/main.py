"""A wrapper around Github Semantic.
Mostly for the JS shell example right now.
"""

import argparse
import json
import tempfile
import subprocess
import visitor
import repostars
import sys
import os
import ipdb
import ruby
import glob

def keep_path(path):
    """Frequently occurring paths that a unlikely to contain anything
    interesting .
    """
    if "node_modules" in path:
       return False
    if "test" in path:
       return False
    if "gulp" in path:
       return False
    if "cordova" in path:
       return False

    return True

def keep_content(line):
    if "req." in line:
        return True
    return False

def parse_directory(data_dir):
    total = 0
    total_keep_content = 0
    total_keep_path = 0

    for fname in os.listdir(data_dir):
        print(fname)
        json_path = os.path.join(data_dir, fname)
        with open(json_path, 'r', encoding='utf-8') as f:
            json_lines = f.readlines()

        for line in json_lines:
            total += 1
            if not keep_content(line):
                continue
            total_keep_content += 1

    print("Total: {}".format(total))
    print("Total keep content: {}".format(total_keep_content))

# Iterates over every file in `data_dir` and for every file that
# matches `regex_to_match`, it will:
#   * Run `semantic` to parse it
#   * Parse the resulting JSON using visitor.py
#
# and return you a list of all of the parsed
def parse_directory_generic(data_dir, path_glob):
    visitors = []

    files = glob.glob(os.path.join(data_dir, path_glob), recursive=True)
    for f in files:
        #print("Parsing file: {}".format(f))
        parsed_semantic_ast = parse_file(f)
        ast_visitor = visitor.Visitor("", f)
        ast_visitor.build(parsed_semantic_ast, None)
        visitors.append(ast_visitor)

    return visitors

def batch_parse_json(json_path, min_stars):
    with open(json_path, 'r', encoding='utf-8') as f:
        json_lines = f.readlines()

    i = 0
    for line in json_lines:
        i = i + 1
        if not keep_content(line):
            continue

        parsed_json_line = json.loads(line)
        repo = parsed_json_line["repo_name"]
        path = parsed_json_line["path"]
        print("{} {} {}".format(i, repo, path), file=sys.stderr)

        if not keep_path(path):
            continue
        temp_file, temp_size = writefile(parsed_json_line)
        semantic_ast = semantic_parse(temp_file)
        parsed_semantic_ast = json.loads(semantic_ast.decode('utf-8'))

        ast_visitor = visitor.Visitor(repo, path)
        ast_visitor.build(parsed_semantic_ast, None)
        ast_visitor.visit(ast_visitor.root)

        for node in ast_visitor.sources:
            for target in ast_visitor.assignments[node]:
                print(json.dumps(target.value, indent=2))


        #for node in ast_visitor.sinks:
        #    visitor.print_node(node, repo, path)


def semantic_parse(temp_file):
    # Configuration in semantic/Config.hs
    # https://github.com/github/semantic/issues/240
    semantic_env = dict()
    semantic_env["SEMANTIC_ASSIGNMENT_TIMEOUT"] = "1000"
    semantic_env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    p = subprocess.Popen(['semantic', 'parse', '--json', temp_file], stdout=subprocess.PIPE, env=semantic_env)
    output, err = p.communicate()
    if (err):
      print(err)
    return output

def writefile(parsed_json_line):
    temp = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".js")

    content = parsed_json_line['content']
    content_lines = content.split('\n')

    for line in content_lines:
        temp.write("{}\n".format(line))

    return (temp.name, len(content_lines))

def parse_file(file_name):
    semantic_ast = semantic_parse(file_name)
    parsed_semantic_ast = json.loads(semantic_ast.decode('utf-8'))
    return parsed_semantic_ast

# grouped_dict is "key" => [list of AstNode objects, probably ClassNodes]
def print_grouped_objects(grouped_dict, print_func):
    for key, matched_list in grouped_dict.items():
        print(key)
        for cur_node in matched_list:
            print("  " + print_func(key, cur_node))
        print()

def print_classes(visitors, class_filter_func):
    for v in visitors:
        klasses = v.class_nodes()
        for klass in klasses:
            if not class_filter_func(klass):
                continue

            print(klass.pprint())

            for meth in klass.method_nodes:
                print("  " + meth.pprint())

            print()
            for send in klass.send_nodes:
                print("  " + send.pprint())

            print()
            print()

# Conditionally drop to an ipdb repl if the --repl
# command-line flag was passed
def repl(args):
    if args.repl:
        ipdb.set_trace()
        print("Dropping to REPL")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', help="Path to bigquery json export")
    parser.add_argument('--data', help="Path to data directory")
    parser.add_argument('--stars', help="Mininum number of GitHub stars")
    parser.add_argument('--parse-file', help="Parse one specific file with semantic and dump to JSON")
    parser.add_argument('--path-glob', help="Specify a path glob that will select the files to parse. Only used by --parse-directory.")
    parser.add_argument('--parse-directory', help="Parse every file in the provided directory. You can use --path-glob to only parse certain files")
    parser.add_argument('--rails-summarize-controllers', help="Parse every Controller class in a Rails repo and prints out the methods and before_actions. You can use --path-glob to only parse certain files")
    parser.add_argument('--rails-controllers-by-superclass', help="Print all Rails controllers, grouped by superclass. You can use --path-glob to only parse certain files")
    parser.add_argument('--rails-controllers-by-before-action', help="Print all Rails controllers, grouped by before_action. You can use --path-glob to only parse certain files")
    parser.add_argument('--repl', default=False, action="store_true", help="Drop to an ipdb REPL after parsing is complete")

    args = parser.parse_args()
    if args.json:
        batch_parse_json(args.json, args.stars)
    elif args.data:
        parse_directory(args.data)
    elif args.parse_file:
        path = args.parse_file
        repo = ""
        parsed_semantic_ast = parse_file(path)
# result = { "trees" = [...]} - when ran on 1 file, list is len == 1
# Each elem has the following keys:
# - 'path' => 'examples/shellcon2019_examples/rubygems.org/app/controllers/application_controller.rb'
# - 'language' => 'Ruby
# - 'tree' => AST
#
# Tree has keys:
# - 'sourceSpan' - {'end': [114, 1], 'start': [1, 1]}
# - 'term' - 'Statements'
# - 'sourceRange' - [0, 3486]
# - 'statements' - list of AST statements
        ast_visitor = visitor.Visitor(repo, path)
        ast_visitor.build(parsed_semantic_ast, None)

        if args.repl:
            class_node = ast_visitor.class_nodes()[0]
            print(class_node.pprint())
            for meth in class_node.method_nodes:
                print("  {}".format(meth.pprint()))

            ipdb.set_trace()
            print("Dropping to REPL")

        print(json.dumps(parsed_semantic_ast))

    elif args.parse_directory:
        visitors = parse_directory_generic(args.parse_directory, args.path_glob)

        repl(args)

    elif args.rails_summarize_controllers:
        visitors = parse_directory_generic(args.rails_summarize_controllers, args.path_glob)

        print_classes(visitors, ruby.is_controller_class)
        repl(args)

    elif args.rails_controllers_by_superclass:
        # Groups controllers by superclass and then prints them.
        #
        # Sometimes bugs can be introduced when user-defined controllers
        # inherit from Rails' base controllers and not from the app's
        # ApplicationController, as protections from this base class
        # are not actually applied.
        visitors = parse_directory_generic(args.rails_controllers_by_superclass, args.path_glob)

        superclass_dict = ruby.group_controllers_by_superclass(visitors)
        print_grouped_objects(superclass_dict, lambda k, v : v.classIdentifier.pprint() )

        repl(args)

    elif args.rails_controllers_by_before_action:
        # Groups controllers by superclass and then prints them.
        #
        # Sometimes bugs can be introduced when user-defined controllers
        # inherit from Rails' base controllers and not from the app's
        # ApplicationController, as protections from this base class
        # are not actually applied.
        visitors = parse_directory_generic(args.rails_controllers_by_before_action, args.path_glob)

        before_action_dict = ruby.group_controllers_by_before_action(visitors)

        print_grouped_objects(before_action_dict, lambda k, v : ruby.print_class_before_action_info(k, v) )
        repl(args)
