# ci-tools

####What is 'ci-tools'?
Some CI utils for Git and Maven. Only supports merging GitHub pull requests as of now.

####Requirements
Python 2.7.5+

[Python-requests](http://www.python-requests.org/en/latest/user/install/#install)
(In some environments this module is pre-installed)

####Installation

#####1. Get the 'ci-tools.py' file from the [latest release] (https://github.com/rushmin/ci-tools/releases/latest).

#####2. Add an alias

```
alias ci-tools='python /path/to/ci-tools.py'
```

#####3. Create the settings file

ci-tools needs a settings file which contains settings to access git providers like GitHub. (See the sample settings file below)

The settings file can be specified using the **_--settings_** argument.

If the file is not specified, ci-tools searches for a local settings file named **_ci-tools-settings.json_** in the **_current directory_**

If ci-tools can't find such file, it tries to load the default setting file located in **_HOME/.ci-tools/ci-tools-settings.json_**

So make sure a settings file is located at least in of these locations.

**NOTE :** You only have to change the username and the password in this settings file, unless the git providers has changed their HTTP resource URLs.

#####Sample settings file

```json
{
  "github": {
    "username": "your_username",
    "password": "your_password",
    "api": {
      "root": "https://api.github.com",
      "urls": {
        "getPullRequest": "/repos/{}/{}/pulls/{}"
      }
    },
    "urlPatternsRegEx": {
      "pullRequest": {
        "pattern": "https://github.com/(.+)/(.+)/pull/([0-9]+)",
        "groups": {
          "owner": 1,
          "repo": 2,
          "pullRequestId": 3
        }
      }
    }
  }
}
```

####Usage

```
ci-tools.py [-h] [--settings SETTINGS] [-v] merge pr [-h] [-c CLONE_LOCATION] [-b BRANCH]
                                                     [--no-cleanup] [--no-strict-mode] [--no-update]
                                                     [-p]
                                                     pullRequestUrl

required arguments:

  pullRequestUrl
    URL of the pull request. e.g. https://github.com/john/ci-tools-test/pull/2

optional arguments:

         -h, --help
           show this help message and exit

         -c CLONE_LOCATION, --clone-location CLONE_LOCATION
           clone location of the base repo

         -b BRANCH, --branch BRANCH
           local base branch for the merge

         --no-cleanup
           do not clean up intermediate artifacts

         --no-strict-mode
           switch off the strict mode

         --no-update
           update the clone before the merge

         -p, --push
           push the merge to the origin


```


####Recipes

#####1. Testing and closing a pull request

* Clone the base repo
* Merge the pull request locally, using the following command

```
ci-tools merge pr  https://github.com/john/ci-tools-test/pull/8
```

* Build the repo and test it.
* Push the base branch to the origin. (This step will close the pull request)

**Tip:**
If the merge should be pushed to the base repo right after the merge, the following command can be used. But this exactly what we do using the GitHub UI

```
ci-tools merge pr --push https://github.com/john/ci-tools-test/pull/8
```

#####2. Merging a pull request locally on to a branch other than the base branch of the pull request.

```
ci-tools merge pr -b new-branch  https://github.com/john/ci-tools-test/pull/8
```

**NOTE** : If the target branch doesn't exist in the origin, **--no-update** switch should be used. This switch tells ci-tools not to pull the target branch from the origin.

#####3. Merging a pull request on to a local repo which is not a clone of the pull request base. e.g. a fork of the base

```
ci-tools merge pr --no-strict-mode https://github.com/john/ci-tools-test/pull/8
```

**--no-strict-mode** switch, disables the strict mode. This allows ci-tools to merge a pull request to a repo whose origin is not the base of the pull request.
