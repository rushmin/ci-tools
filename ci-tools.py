#Version : 0.1.0

import os
import sys
import time
from subprocess import call, PIPE, Popen, STDOUT
import argparse
import requests
import json
import re

class GitEngine:

    def __init__(self, settings):
        self.settings = settings

    def mergePullRequest(self, cloneLocation, pullRequestUrl, shouldDeleteMergeBranch, shouldPush):

        print '\n== Pull request merge =='

        # Change the directory to clone location
        os.chdir(cloneLocation)
        print "\nSwitched to the clone location '{}'".format(os.getcwd())

        print "\nProcessing pull request '{}' on '{}'".format(pullRequestUrl, os.getcwd())

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
            print '\nBye\n'
            exit()

        validationResult = self.validatePullRequest(pullRequestInfo)

        if validationResult['status'] is False:
            print '\nError : Cannot merge the pull requet. Reason : {}  \n'.format(validationResult['reason'])
            exit(101)

        print "\nMerging pull requeust. repo : '{}', repo-owner : '{}', pull-request-id : '{}'".format(repoName, repoOwner, pullRequestId)

        # Fetch from the origin
        self.git('fetch')

        # Checkout the base branch
        baseBranch = pullRequestInfo['base']['ref']
        self.git('checkout', [baseBranch])

        # Print the git status
        self.git('status')

        # Pull changes from the origin
        self.git('pull')

        # Checkout a new branch for the merge
        pullRequestCreator = pullRequestInfo['user']['login']
        pullRequestBranch = pullRequestInfo['head']['ref']
        tempBranchName = 'PR/' + '-'.join([pullRequestId, pullRequestCreator, pullRequestBranch])
        self.git('checkout', ['-b', tempBranchName])

        # Pull the changes from the pull request
        pullRequestRepoUrl = pullRequestInfo['head']['repo']['clone_url']
        self.git('pull', ['--no-edit', pullRequestRepoUrl, pullRequestBranch])

        # Merge the pull request
        mergeMessage = '"Merge pull request #{} from {}/{}"'.format(pullRequestId, pullRequestCreator, pullRequestBranch)
        self.git('checkout', [baseBranch])
        self.git('merge', ['--no-ff', '-m', mergeMessage, tempBranchName])

        # Push the changes
        if shouldPush:
            self.git('push', ['origin', baseBranch])

        # Delet the temporary merge branch
        if shouldDeleteMergeBranch:
            self.git('branch', ['-d', tempBranchName])

        print '\nOK. Pull request merge was successful.\n'


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

        # Check whether the current directory is a git repo.
        try:
            shell('git status')
        except SystemError:
            return {'status':False, 'reason':"'{}' is not a git repository.".format(os.getcwd())}

        # Compare the URL of the base repo and the origin URL of the clone
        baseRepoUrl = pullRequestInfo['base']['repo']['html_url']
        origin = self.gitConfig('.git/config', 'remote.origin.url')

        if baseRepoUrl != origin:
            return {'status':False, 'reason':"Clone origin ('{}') and the pull request base repo ('{}') are different".format(origin, baseRepoUrl)}

        # Check whether the pull request is already merged
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

        if exitCode is not 0:
            print '\nGIT ERROR : Cannot proceed. Exiting ...\n'
            exit(102)

    def gitConfig(self, file, key):
        return shell('git config --file {} {}'.format(file, key))

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

    mergePullRequest = subparsers.add_parser('merge')
    mergePullRequest.add_argument('-c', '--clone-location', help='Clone location of the base repo')
    mergePullRequest.add_argument('pullRequestUrl', help='URL of the pull request. e.g. https://github.com/john/ci-tools-test/pull/2')
    mergePullRequest.add_argument('-d', '--delete-merge-branch', action='store_true', help='Delete the temporary merge branch')
    mergePullRequest.add_argument('-p', '--push', action='store_true', help='Flag to push the merge to the origin')

    args = parser.parse_args()

    # Load settings
    settings = loadSettings(args.settings)

    # Init the git engine
    gitEngine = GitEngine(settings);

    # Read the clone location. Use the currently directory, if not specified.
    cloneLocation = os.getcwd()
    if args.clone_location is not None:
        cloneLocation = args.clone_location

    # Read the pull request URL
    gitEngine.mergePullRequest(cloneLocation, args.pullRequestUrl, args.delete_merge_branch, args.push);

def loadSettings(location):

    if location is None:

        defaultSettingsFileName = '/ci-tools-settings.json'
        if os.path.exists(os.getcwd() + defaultSettingsFileName):
            location = os.getcwd() + defaultSettingsFileName
        else:
            location = os.environ['HOME'] + '/.ci-tools'+ defaultSettingsFileName

    return json.loads(open(location).read())

# --------- Util methods ---------

def shell(command):
    process = Popen(command, stdout=PIPE, stdin=PIPE, stderr=STDOUT, shell=True)
    r = process.communicate()
    if process.returncode != 0:
        raise SystemError(r[0])
    else:
        # Remove line break
        return "\n".join(r[0].splitlines())


if __name__ == '__main__':
   main(sys.argv[1:])
