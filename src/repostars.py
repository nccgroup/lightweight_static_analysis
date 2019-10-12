import json
#from github import Github
import sys

# TODO: Grab this token from the env
#g = Github("TODO")

cache_file = "stars.txt"

stars_cache = dict()

with open(cache_file, 'r') as f:
    for l in f.readlines():
        repo, stars = l.split()
        stars_cache[repo] = int(stars)

def get_repo_stars(repo_name):
    if repo_name in stars_cache:
        return stars_cache[repo_name]

    try:
        repo = g.get_repo(repo_name)
        stars = repo.stargazers_count

        with open(cache_file, 'a') as f:
            f.write("{} {}\n".format(repo_name, stars))
        stars_cache[repo_name] = int(stars)

        return stars
    except Exception:
        return -1
