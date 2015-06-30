from github import Github
from collections import Counter, defaultdict
import csv
import os
import pickle
import traceback
import time
import re


user = os.environ['GITHUB_USER']
pswd = os.environ['GITHUB_PASS']

g = Github(user, pswd, user_agent='grschafer/github-django-structure')
csv_file = 'django-repos.csv'
csv_header = ['link', 'name', 'index', 'search_url']
file_types = ['blob', 'tree']


blacklist_exts = [
        '.svn-base',
        '.pyc',
        '.js',
        '.png',
        '.gif',
        '.jpg',
        '.jpeg',
        '.pdf',
        ]

file_whitelist = [
        'docs',
        'scripts',
        'apps',
        'accounts',
        'settings',
        'static',
        'templates',
        'tests',
        'tmp',
        'management',
        'commands',
        'migrations',
        'admin',
        'middleware',
        '.gitignore',
        'urls',
        'wsgi',
        'setup',
        'tests',
        'settings',
        'requirements',
        'pytest',
        'tox',
        'travis',
        'manage',
        'models',
        'admin',
        'views',
        'utils',
        'license',
        'readme',
        'makefile',
        ]
whitelist_regexes = {name:re.compile(r'{}($|\W+.*$)$'.format(name), flags=re.IGNORECASE) for name in file_whitelist}

class Repo(object):
    def __init__(self, link, name, index, search_url):
        self.link = link
        self.name = name
        self.index = index
        self.search_url = search_url
        self.owner, _, self.repo = name.rpartition('/')


def load_repos():
    with open(csv_file) as f:
        reader = csv.reader(f)
        next(reader) # toss csv header
        repos = [Repo(*line) for idx,line in enumerate(reader) if idx < 20]
        return repos

def download_tree(repo):
    g_repo = g.get_repo(repo.name)
    g_ref = g_repo.get_git_ref('heads/{}'.format(g_repo.default_branch))
    g_tree = g_repo.get_git_tree(g_ref.object.sha, recursive=True)
    return g_tree

class TreeStat(object):
    def __init__(self, whitelist_name):
        self.filename = whitelist_name
        self.top_count = 0
        self.dirlevel_count = Counter()
        self.dirname_count = defaultdict(Counter)
        self.matches = Counter()

    def incr(self, path):
        self.top_count += 1

        match = os.path.basename(path)
        self.matches[match] += 1

        pieces = path.split('/')
        num_pieces = len(pieces)
        self.dirlevel_count[num_pieces] += 1
        for idx, piece in enumerate(reversed(pieces)):
            self.dirname_count[idx][piece] += 1

    def __str__(self):
        #return '\n\t'.join(str(x) for x in [self.filename, self.top_count, self.matches])
        return '\n\t'.join(str(x) for x in [self.filename, self.top_count, self.matches, self.dirlevel_count, self.dirname_count])


def compile_stats(compound_trees):
    stats = {}
    for name in file_whitelist:
        stats[name] = TreeStat(name)

    for tree in compound_trees:
        for elem in tree['tree'].tree:
            filename = os.path.basename(elem.path)
            _, ext = os.path.splitext(filename)
            if ext in blacklist_exts:
                continue

            for name, rx in whitelist_regexes.items():
                if rx.match(filename):
                    stats[name].incr(elem.path)
                #if name in pieces[0].lower():
                #    stats[name].incr(pieces)

            #for idx, piece in enumerate(pieces):
            #    for name in file_whitelist:
            #        if name in piece.lower():
            #            stats[name].incr(pieces[idx:])
            #    break
    return stats

def trim_trees(compound_trees):
    for tree in compound_trees:
        yield {'repo': tree['repo'], 'paths': [f.path for f in tree['tree'].tree]}

# TODO: % of repos with multiple apps
# TODO: locations of files
#   look for specific files
#   track % of repos with that file
#   track location(s) of that file

def persist_stats(stats):
    t = time.time()
    with open('stats.pkl', 'wb') as fout:
        pickle.dump(stats, fout)
    print('persist_stats took', time.time() - t)

def persist_trees():
    compound_trees = []
    for repo in load_repos():
        try:
            d = {'repo': repo}
            tree = download_tree(repo)
            d['tree'] = tree
            compound_trees.append(d)
        except Exception as e:
            print(traceback.format_exc())
            import ipdb; ipdb.set_trace()
    t = time.time()
    with open('trees.pkl', 'wb') as fout:
        pickle.dump(compound_trees, fout)
    print('persist_trees took', time.time() - t)

def load_trees():
    t = time.time()
    with open('trees.pkl', 'rb') as fin:
        trees = pickle.load(fin)
        print('load_trees took', time.time() - t)
        return trees

trees = None
stats = None
if __name__ == '__main__':
    global trees
    global stats

    #persist_trees()
    trees = load_trees()
    stats = compile_stats(trees[0:20])
    persist_stats(stats)
    for stat in stats.values():
        print(stat)


