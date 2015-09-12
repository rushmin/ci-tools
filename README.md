# ci-tools

####What ?
Some CI extensions for Git and Maven

####How ?

```
ci-tools.py mergePullRequest "{'repo':'ci-tools-test', 'id':'1'}" --push
```

A data file which contains the repo information should be there in the current directory. The name of the file should be **ci-tools-data.json**

#####Sample file

```json
{
  "repositories": {
    "ci-tools-test": {
      "name": "ci-tools-test",
      "cloneLocation": "/wso2dev/rnd/poc/wso2-ci-tools/builder/ci-tools-test",
      "github": {
        "url": "https://github.com/sumuditha-viraj/ci-tools-test",
        "owner": "sumuditha-viraj"
      }
    }
  },
  "conf": {
    "github": {
      "username": "rushmin",
      "password": "Password",
      "api": {
        "root": "https://api.github.com",
        "getPullRequest": "/repos/{}/{}/pulls/{}"
      }
    }
  }
}
```
