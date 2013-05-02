Sugar
=====

Sugar is the core component of a worldwide effort to provide every
child with equal opportunity for a quality education. Available in
more than twenty-five languages, Sugar’s Activities are used every
school day by nearly three million children in more than forty
countries.

Originally developed for the One Laptop per Child XO-1 netbook, Sugar
runs on most computers. Sugar is free/libre and open-source software.

Hacking
-------

For hacking you can use the sugar-build tool. Sugar is made of several modules and it often depends on libraries which has not yet been packaged in linux distributions. To make it easier for developers to build from sources, we developed a set of scripts that automates builds and other common development tasks. 

For details see: http://sugarlabs.org/~buildbot/docs/build.html

Contributing
------------

We use the pull-request model, see [github's help on
pull-request](https://help.github.com/articles/using-pull-requests).

In short, you will:

* do your changes in a new branch
* push your branch and submit a pull-request for it
* go through the review process

### Forking

You should fork the repository first.  This step is needed only once.
See [complete help in
github](https://help.github.com/articles/fork-a-repo).  Brief
instructions follow:

* navigate <https://github.com/sugarlabs/sugar/> and press **Fork** button
* git clone https://github.com/YOUR-NAME/sugar.git
* cd sugar
* git remote add upstream https://github.com/sugarlabs/sugar.git
* git fetch upstream

### Sending a pull-request

* Create one branch per topic

  git checkout -b topic1

* Make one or more commits
* Push the branch

  git push origin topic1

* Submit a pull request for the branch (web UI)

After that, the review process will happen in the pull-request page on
github.  The process ends with one of this:

1. The reviewer merges your request.
2. The reviewer rejects your request (and closes the request).
3. The reviewer requires changes (and closes the request).

In case they ask you for changes,

* Make changes using interactive rebase
<http://git-scm.com/book/en/Git-Tools-Rewriting-History#Changing-Multiple-Commit-Messages>

  git rebase -i master

* Push the changes to another remote branch

  git push origin topic1:topic1-try2

* Submit the new pull request (web UI)

To provide your next pull-request, don't forget to pull in changes
from the master repository.

### Keep your fork up to date

Pull in upstream changes:

* git fetch upstream
* git merge upstream/master

### Reviewing

We encourage testing before merging a pull-request.  So instead of
merging directly with the "merge" button on github UI, you do a local
merge, then test, then push.  See [github help on merging a
pull-request](https://help.github.com/articles/merging-a-pull-request).

The github page for the pull-request will provide you the right
commands to do the local merge.  They will be something like:

* get the changes from that branch to a new local branch:

  git checkout -b SOME-USER-topic1 master

  git pull https://github.com/SOME-USER/sugar.git topic1

* Test!

* If everything is fine, merge:

  git checkout master

  git merge SOME-USER-topic1

  git push origin master
