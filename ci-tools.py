import os
import sys
import time
from subprocess import call
import argparse
import requests
import json

class GitEngine:

    def __init__(self, repos, conf):
        self.repos = repos
        self.conf = conf

    def mergePullRequest(self, pullRequestInfo, shouldPush):

        print pullRequestInfo
        repoName = pullRequestInfo['repo']
        repoLocation = self.repos[repoName]['cloneLocation']
        repoOwner = self.repos[repoName]['github']['owner']
        pullRequestId = pullRequestInfo['id']

        print "Merging pull requeust. repo : '{}', clone : '{}', repo-owner : '{}', pull-request-id : '{}'".format(repoName, repoLocation, repoOwner, pullRequestId)

        os.chdir(repoLocation)
        print "Switched to git repo '{}'".format(repoLocation)

        # Fetch pull request info from github
        pullRequestInfoApiUrl = self.conf['github']['api']['root'] + self.conf['github']['api']['getPullRequest'].format(repoOwner, repoName, pullRequestId)
        response =  self.invokeGitHubApi(pullRequestInfoApiUrl)
        pullRequestInfo = response.json();

        # Fetch from the origin
        self.git('fetch')

        # Checkout the base branch
        baseBranch = pullRequestInfo['base']['ref']
        self.git('checkout', [baseBranch])

        # Pull changes from the origin
        self.git('pull')

        # Checkout a new branch for the merge
        pullRequestCreator = pullRequestInfo['user']['login']
        pullRequestBranch = pullRequestInfo['head']['ref']
        tempBranchName = 'PR/' + '-'.join([pullRequestCreator, pullRequestBranch, pullRequestId])
        self.git('checkout', ['-b', tempBranchName])

        # Pull the changes from the pull request
        pullRequestRepoUrl = pullRequestInfo['head']['repo']['git_url']
        self.git('pull', [pullRequestRepoUrl, pullRequestBranch])

        # Merge the pull request
        mergeMessage = 'Merge pull request #{} from {}/{}'.format(pullRequestId, pullRequestCreator, pullRequestBranch)
        self.git('checkout', [baseBranch])
        self.git('merge', ['--no-ff', '-m', mergeMessage, tempBranchName])

        # Push the changes
        if shouldPush:
            self.git('push', ['origin', baseBranch])

    def git(self, command, arguments=[]):

        gitCommand = ['git']
        gitCommand.append(command);

        for argument in arguments:
            gitCommand.append(argument)

        print '\nGitCommand :: ', ' '.join(gitCommand)

        exitCode = call(gitCommand)

        if exitCode == 1:
            print 'GIT ERROR : Cannot proceed.'
            exit(1)

    def invokeGitHubApi(self, url, params={}):

        username = self.conf['github']['username']
        password = self.conf['github']['password']

        print "Invoking GitHub API '{}'".format(url)
        response = requests.get(url, auth=(username, password))
        return response

def main(argv):

    parser = argparse.ArgumentParser(description='CI Tools.')

    subparsers = parser.add_subparsers()

    mergePullRequest = subparsers.add_parser('mergePullRequest')
    mergePullRequest.add_argument("pullRequest", help="Sample pull request => {'repo':'ci-tools', 'id':'1'}")
    mergePullRequest.add_argument("--push", action="store_true", help="Flag to push the merge to the origin")

    args = parser.parse_args()

    data = json.loads(open(os.getcwd()+'/ci-tools-data.json').read())
    repos = data['repositories']
    conf = data['conf']
    gitEngine = GitEngine(repos, conf);

    if args.pullRequest is not None:
        gitEngine.mergePullRequest(eval(args.pullRequest), args.push);

if __name__ == "__main__":
   main(sys.argv[1:])
