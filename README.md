# Lightweight Static Analysis

This repo contains the PoC code for a ShellCon 2019 talk, "[Rolling Your Own:
How to Write Custom, Lightweight Static Analysis
Tools](https://shellcon.io/talks/#rolling-your-own)" ([slides](https://bit.ly/2019ShellCon_StaticAnalysis)).

In a nutshell, this repo demonstrates a few concrete examples of how you can
build some interesting static analyses using open source tools and a small
amount of custom code.

**Code examples in this repo**:

1. Iteratively exploring a Rails code base to understand the controllers it
   defines and the `before_action`s it uses.
2. Find command injection in NodeJS apps.

**How the examples work**

At a high level, the implementation of the examples works as follows:

1. Find some source code you want to analyze.
2. Parse the source code using GitHub's
   [semantic](https://github.com/github/semantic/) tool into an Abstract Syntax
   Tree (AST) and output that to JSON.
3. Parse the AST in JSON form with our Python code and then do some interesting
   anayses with it.

## Setup

This project is made to be run using Docker.

To do so, you'll need to set up a few things first.

Since our `Dockerfile` is based on the
[semantic](https://github.com/github/semantic) Docker image, which is hosted on
GitHub's package registry, you'll need to [configure Docker for use with GitHub
Package
Registry](https://help.github.com/en/articles/configuring-docker-for-use-with-github-package-registry).

1. Create a personal access token with the permissions the above article describes.
2. Authenticate to the GitHub package registry: `$ docker login docker.pkg.github.com -u USERNAME -p TOKEN`
3. Build the Docker container: `docker build -t lightweight_static_analysis .`
4. Run a `bash` shell within the Docker container and then run our scripts.

~~~bash
# Run this 
# (Make sure to run this from a terminal in this repo's project root)
$ docker run -it --rm --entrypoint /bin/bash -v $PWD:/lightweight_static_analysis lightweight_static_analysis

# cd into this project's source code within the 
# running container
$ cd /lightweight_static_analysis

# Run main.py with different config options, described further below
~~~

## Running

After you have a `bash` shell in the Docker container (see above for the `docker
run` command), you can run `main.py` with one of several possible modes.

~~~bash
/lightweight_static_analysis> $ python3 src/main.py <options>
~~~

You can see all of the available options by running `src/main.py` with no
options or by viewing the `parser.add_argument` section of `main.py`.

### Exploring Rails code bases

Here are a few commands that can help you interactively explore a Rails code base.

First, you want to clone down one or more Rails repos and put them into `examples/`. If you need some example repos, you can use the source code for [rubygems.org](https://github.com/rubygems/rubygems.org), or one of the repos listed on [Open Source Rails](http://www.opensourcerails.com/).

~~~bash
# Print out the class, super class, defined methods, and before actions
# for all controllers
$ python3 src/main.py --rails-summarize-controllers examples/<repo_name>

# Print out every controller name, grouped by super class
#
# This can find examples where security protections defined in a parent class
# (e.g. ApplicationController or Api::BaseController) aren't applied because
# the vulnerable controller didn't subclass the appropriate class.
$ python3 src/main.py --rails-controllers-by-superclass examples/<repo_name>

# For every before_action used by any controller, list the controllers that
# use that before_action and the routes that it is and isn't applied to
# (e.g. handle the 'except' and 'only" keywords)
#
# This can:
# * Give you quick insight the various before_actions the application defines,
#   yielding some intuition as to the code's flow and organization.
#   * `verify_with_otp` - Hm, that sounds interesting, I probably want to
#      review how that filter is implemented.
# * Show you where a given before_action is and isn't applied across an entire
#   code base, potentially leading to bugs where it is inconsistently used
#
# For example
# * Is there a before_action that's used to protect all state0-changing API
#   routes except for 1 model? That's strange.
# * Is there an authentication or authorization before_action applied to every
#   action in a controller except one? Why?
$ python3 src/main.py --rails-controllers-by-before_action examples/<repo_name>
~~~

If you'd like to drop to an [ipdb](https://github.com/gotcha/ipdb) REPL after
the parsing has completed so that you can interactively examine the parsed Ruby
code, you can do so by also passing in the `--repl` flag to the above commands. 

These examples rely on the various `AstNode` classes defined in `ast_node.py`,
and all of the Rails-specific code is in `ruby.py`.

### Finding command injection via JS shell `exec()`s

This implementation has not yet been cleaned up and documented, but see `batch_parse_json()` in `main.py` and `visit()` and the other methods it calls in `visitor.py`.

## Keep in touch

We're happy to chat about this work in more detail, feel free to open an issue
or reach out on Twitter: [@clintgibler](https://twitter.com/clintgibler),
[@defreez](https://twitter.com/defreez).

If you want to keep up with this and other projects we work on, check out our [tl;dr sec newsletter](https://programanalys.is/newsletter/), where we send out detailed summaries of top security talks and links to the best security tools and resources.

It's a low volume, high signal newsletter aimed at keeping you up-to-date with the latest and greatest in security so you can do your job more efficiently and effectively, and have useful tidbits to share at your infosec watercooler.