from subprocess import call
import os

# Merges remote branches in to local given repos.
class GitEngine:

    def __init__(self, repoInfo, mergeInfo):
        self.repoInfo = repoInfo
        self.mergeInfo = mergeInfo

    def merge(self, repoName):
        repoLocation = self.repoInfo[repoName]["location"];
        mergeBaseBranch = self.repoInfo[repoName]["branch"];

        remoteName = self.mergeInfo[repoName]["remote"]
        mergeTargetBranch = self.mergeInfo[repoName]["branch"]

        print "Processing git repo : ", repoLocation

        os.chdir(repoLocation)

        # Fetch the origin
        self.git("fetch", ['origin'])

        # Checkout the merge base
        self.git("checkout", [mergeBaseBranch])

        # Pull the remote changes
        self.git("pull")

        # Fetch the remote
        self.git("fetch", [remoteName])

        # Merge the remote target branch
        mergeArgs = ['--no-ff']

        pullRequestId = self.mergeInfo[repoName]["pullRequestId"]

        if pullRequestId is None:
            mergeArgs.append('--no-edit')
        else:
            mergeArgs.append('-m')
            mergeArgs.append('"Merge pull request #' + pullRequestId + ' from ' + remoteName + '/' + mergeTargetBranch + '"')

        mergeArgs.append(remoteName + "/" + mergeTargetBranch)

        self.git("merge", mergeArgs)

        self.git("push", ['origin', mergeBaseBranch])

    def git(self, command, arguments=[]):

        gitCommand = ['git']
        gitCommand.append(command);

        for argument in arguments:
            gitCommand.append(argument)

        print "\nGitCommand :: ", " ".join(gitCommand)

        exitCode = call(gitCommand)

        if exitCode == 1:
            print "GIT ERROR : Cannot proceed."
            exit(1)

repoInfo = {'carbon-appmgt':{'name':'carbon-appmgt', 'branch':'support', 'location':'/wso2dev/rnd/poc/wso2-ci-tools/builder/carbon-appmgt'}}
mergeInfo = {'carbon-appmgt':{'remote':'john', 'branch':'fix2', 'pullRequestId':'2'}}


gitEngine = GitEngine(repoInfo, mergeInfo);

gitEngine.merge('carbon-appmgt');
