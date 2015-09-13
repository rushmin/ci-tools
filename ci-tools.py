#Version : 0.1.0

import os
import sys
import time
from subprocess import call
import argparse
import requests
import json
import re

class GitEngine:

    def __init__(self, settings):
        self.settings = settings

    def mergePullRequest(self, pullRequestInfo, shouldPush):

        localRepoLocation = pullRequestInfo['repoLocation']
        pullRequestUrl = pullRequestInfo['pullRequestUrl']

        print "\nProcessing pull request '{}' on '{}'".format(pullRequestUrl, localRepoLocation)

        # Change the directory to the repo location
        os.chdir(localRepoLocation)
        print "\nSwitched to git repo '{}'".format(os.getcwd())

        # Parse the pull request url to get the repo info and the pull request id.
        parsedPullRequest = self.parsePullRequestUrl(pullRequestUrl)
        repoName = parsedPullRequest['repo']
        repoOwner = parsedPullRequest['owner']
        pullRequestId =parsedPullRequest['pullRequestId']

        # Fetch pull request info from github
        pullRequestInfoApiUrl = self.settings['github']['api']['root'] + self.settings['github']['api']['urls']['getPullRequest'].format(repoOwner, repoName, pullRequestId)
        response =  self.invokeGitHubApi(pullRequestInfoApiUrl)
        pullRequestInfo = response.json();

        if self.shouldContinue(pullRequestInfo) is False:
            exit()

        validationResult = self.validatePullRequest(pullRequestInfo)

        if validationResult['status'] is False:
            print '\nError : Cannot merge the pull requet. Reason : ' + validationResult['reason']

        print "\nMerging pull requeust. repo : '{}', repo-owner : '{}', pull-request-id : '{}'".format(repoName, repoOwner, pullRequestId)

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
        mergeMessage = '"Merge pull request #{} from {}/{}"'.format(pullRequestId, pullRequestCreator, pullRequestBranch)
        self.git('checkout', [baseBranch])
        self.git('merge', ['--no-ff', '-m', mergeMessage, tempBranchName])

        # Push the changes
        if shouldPush:
            self.git('push', ['origin', baseBranch])

    def shouldContinue(self, pullRequestInfo):

        message = '\nDo you want to merge the following pull request ?'

        baseRepo = pullRequestInfo['base']['repo']['full_name']
        baseBranch = pullRequestInfo['base']['ref']
        creator = pullRequestInfo['user']['login']
        title = pullRequestInfo['title']
        updatedAt = pullRequestInfo['updated_at']
        pullRequestBranch = pullRequestInfo['head']['ref']

        message = message + '\n\tbase-repo = {}\n\tbase-branch = {}\n\tcreator = {}\n\ttitle = {}\n\tupdated-at = {}\n\tpull-request-branch = {}\n\n ==>  [Yes/no] - '.format(baseRepo, baseBranch, creator, title, updatedAt, pullRequestBranch)

        response = raw_input(message);

        if response == 'Yes':
            return True
        else:
            return False

    def validatePullRequest(self, pullRequestInfo):

        if pullRequestInfo['merged'] is True:
            return {'status':False, 'reason':'Pull request is already merged.'}

        return {'status':True, 'reason':''}

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

        username = self.settings['github']['username']
        password = self.settings['github']['password']

        print "\nInvoking GitHub API '{}'".format(url)
        response = requests.get(url, auth=(username, password))
        return response

    def parsePullRequestUrl(self, pullRequestUrl):

        matcher = re.search(self.settings['github']['urlPatternsRegEx']['pullRequest']['pattern'], pullRequestUrl)

        groupConfig = self.settings['github']['urlPatternsRegEx']['pullRequest']['groups']

        parsedPullRequest = {
                             'owner':matcher.group(groupConfig['owner']),
                             'repo':matcher.group(groupConfig['repo']),
                             'pullRequestId':matcher.group(groupConfig['pullRequestId']),
                            }

        return parsedPullRequest


def main(argv):

    parser = argparse.ArgumentParser(description='CI Tools.')
    parser.add_argument('--settings', help='Settings file location')

    subparsers = parser.add_subparsers()

    mergePullRequest = subparsers.add_parser('mergePullRequest')
    mergePullRequest.add_argument('pullRequest', help="e.g. => {'repoLocation':'ci-tools-test', 'pullRequestUrl':'https://github.com/john/ci-tools-test/pull/1'}")
    mergePullRequest.add_argument('--push', action='store_true', help='Flag to push the merge to the origin')

    args = parser.parse_args()

    settings = loadSettings(args.settings)

    gitEngine = GitEngine(settings);

    if args.pullRequest is not None:
        gitEngine.mergePullRequest(eval(args.pullRequest), args.push);

def loadSettings(location):

    if location is None:

        defaultSettingsFileName = '/ci-tools-settings.json'
        if os.path.exists(os.getcwd() + defaultSettingsFileName):
            location = os.getcwd() + defaultSettingsFileName
        else:
            location = os.environ['HOME'] + '/.ci-tools'+ defaultSettingsFileName

    return json.loads(open(location).read())


if __name__ == '__main__':
   main(sys.argv[1:])
