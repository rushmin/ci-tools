# ci-tools

####What ?
Some CI extensions for Git and Maven. Only supports merging GitHub pull requests as of now.

####Requirements
Python 2.7.5+

####Usage

```
ci-tools.py [-h] [--settings SETTINGS] mergePullRequest [-h] [--push] pullRequest

positional arguments:

  pullRequest  e.g. => "{'repoLocation':'ci-tools-test','pullRequestUrl':'https://github.com/john/ci-tools-test/pull/1'}"

optional arguments:
  -h, --help   show the message and exit
  --settings   settings file location
  --push       flag to push the merge to the origin
```

####Settings

ci-tools needs a settings file which contains settings to access git providers like GitHub. (See the sample settings file below)

**NOTE : ** You only have to change the username and password in this setting file, unless the git providers has changed their HTTP resource URLs.


The settings file can be specified using the **_--settings_** argument.

If the file is not specified, ci-tools searches for a local settings file named **_ci-tools-settings.json_** in the **_current directory_**

If ci-tools can't find such file, it tries to load the default setting file located in **_HOME/.ci-tools/ci-tools-settings.json_**

So make sure a settings file is located at least in of these locations.

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
