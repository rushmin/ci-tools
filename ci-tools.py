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

    def __init__(self, settings, isVerboseEnabled):
        self.settings = settings
        self.isVerboseEnabled = isVerboseEnabled

    def mergePullRequest(self, cloneLocation, pullRequestUrl, branch, shouldCleanup, isStrictMode, shouldUpdate, shouldPush):

        print '\n== Pull request merge {} ==='.format('(Strict Mode)' if isStrictMode else '(Relaxed Mode)')

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

        if self.isVerboseEnabled:
            print '\n\tResponse Content\n\n<START>{}<END>'.format(response.text)

        pullRequestInfo = response.json();

        if self.shouldContinue(pullRequestInfo) is False:
            print '\nBye\n'
            exit()

        validationResult = self.validatePullRequest(pullRequestInfo, isStrictMode)

        if validationResult['status'] is False:
            print '\nError : Cannot merge the pull requet. Reason : {}  \n'.format(validationResult['reason'])
            exit(101)

        print "\nMerging pull requeust. repo : '{}', repo-owner : '{}', pull-request-id : '{}'".format(repoName, repoOwner, pullRequestId)

        # Fetch from the origin
        if shouldUpdate:
            self.git('fetch')

        # Checkout the base branch.
        # If a base branch is not explicitly specified, then the one in the pull request is used.
        baseBranch = branch

        if baseBranch is None:
            baseBranch = pullRequestInfo['base']['ref']

        self.git('checkout', [baseBranch])

        # Print the git status
        self.git('status')

        # Pull changes from the origin
        if shouldUpdate:
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
        if shouldCleanup:
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

    def validatePullRequest(self, pullRequestInfo, isStrictMode):

        # Check whether the current directory is a git repo.
        try:
            shell('git status')
        except SystemError:
            return {'status':False, 'reason':"'{}' is not a git repository.".format(os.getcwd())}

        # If 'strict' mode is enabled, compare the URL of the base repo and the origin URL of the clone
        if isStrictMode:
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

        if response.status_code is not requests.codes.ok:
            print '\n\tError ! Status code : {}'.format(response.status_code)
            exit()

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

class CITools:

    def __init__(self, settings, args):
        self.settings = settings
        self.args = args
        self.isVerboseEnabled = args.isVerboseEnabled
        self.gitEngine = GitEngine(settings, self.isVerboseEnabled);

    def execute(self):

        if self.args.command == 'pr':
            self.handlePullRquestMerge()

    def handlePullRquestMerge(self):

        # Read the clone location. Use the currently directory, if not specified.
        cloneLocation = os.getcwd()
        if self.args.clone_location is not None:
            cloneLocation = self.args.clone_location

        # Read the pull request URL
        self.gitEngine.mergePullRequest(cloneLocation,
                                     self.args.pullRequestUrl,
                                     self.args.branch,
                                     self.args.shouldCleanup,
                                     self.args.isStrictMode,
                                     self.args.shouldUpdate,
                                     self.args.shouldPush);


def main(argv):

    # Parse command line arguments
    parser = getArgParser();
    args = parser.parse_args()

    # Load settings
    settings = loadSettings(args.settings)

    # Execute the command
    ciTools = CITools(settings, args)
    ciTools.execute()


def getArgParser():

    parser = argparse.ArgumentParser(description='CI Tools.')
    parser.add_argument('--settings', help='settings file location')
    parser.add_argument('-v', '--verbose', dest='isVerboseEnabled', action='store_true', help='enable verbose logging')

    mergeCommandParser = parser.add_subparsers(dest='command').add_parser('merge', help='merge remote branches')

    mergePullRequestCommandParser = mergeCommandParser.add_subparsers(dest='command').add_parser('pr', help='merge GitHub pull requests')

    mergePullRequestCommandParser.add_argument('-c', '--clone-location', help='clone location of the base repo')
    mergePullRequestCommandParser.add_argument('-b', '--branch', help='local base branch for the merge')

    mergePullRequestCommandParser.add_argument('--no-cleanup', dest='shouldCleanup', action='store_false', help='do not clean up intermediate artifacts')
    mergePullRequestCommandParser.set_defaults(shouldCleanup=True)

    mergePullRequestCommandParser.add_argument('--no-strict-mode', dest='isStrictMode', action='store_false', help='switch off the strict mode')
    mergePullRequestCommandParser.set_defaults(isStrictMode=True)

    mergePullRequestCommandParser.add_argument('--no-update', dest='shouldUpdate', action='store_false', help='update the clone before the merge')
    mergePullRequestCommandParser.set_defaults(shouldUpdate=True)

    mergePullRequestCommandParser.add_argument('-p', '--push', dest='shouldPush', action='store_true', help='push the merge to the origin')

    mergePullRequestCommandParser.add_argument('pullRequestUrl', help='URL of the pull request. e.g. https://github.com/john/ci-tools-test/pull/2')

    return parser;

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
