# szz-mpi
HPC implementation of the SZZ algorithm using MPI

## Installation instructions

### Mac OS X
Assuming that [Homebrew](https://brew.sh) and [Homebrew-Cask](https://caskroom.github.io) are already installed, run:
```bash
$ brew install libgit2 openmpi
```
After that, clone the repo to your machine and create a Python 3 virtual environment in the destination directory:
```bash
$ virtualenv -p /path/to/python3/bin/file .env
$ source ./env/bin/activate
```
Remember, to go back using the default Python version installed on your machine, simply execute `$ deactivate`.

Alternatively, you can create the virtual environment using [Conda](https://conda.io) (or [MiniConda](https://conda.io/miniconda.html), if you want to save some storage space).
```bash
$ brew cask install miniconda
```
After the installation, you first create and activate a Python 3 virtual environment named `venv3` as follows:

```bash
$ conda update conda
$ conda create -n venv3 python=3
$ source activate venv3
``` 
Remember, to go back using the default Python version installed on your machine, this time yo have to execute `$ source deactivate`.

Whichever method you chose, next you have to install the package dependencies listed into the `requirements.txt` file:
```bash
$ pip install -r requirements.txt
```
   
### Ubuntu Linux
First, after creating the virtual environment, move inside the directory where `szz` is cloned.
First make sure `cmake` is installed.
```bash
$ sudo apt-get install cmake openmpi
```
Then, install the `libgit2` library in it, following the [official installation guidelines](https://github.com/libgit2/pygit2/blob/master/docs/install.rst#quick-install).
Finally, before installing the required packages via `pip` as described above, make sure to have the following 
development libraries already installed.
```bash
$ sudo apt-get install python3-dev libgit2-dev

```
### Centos 7
First, install the required packages:
```bash
$ yum install libgit2 openmpi

```
Then, run the following command:
```bash
$ env MPICC=path_to_your_mpicc -r requirements.txt
```
*Troubleshooting*
  - In case of failure while installing `pygit2`, check if `libgit2` command is available in your PATH. If not, please add it or try to execute the `libgit2-installation.sh`:
    ```bash
    $ sh  libgit2-installation.sh
    ```
    It will install `libgit2` in `usr/local` folder, which is on PATH.

### Step 1: GitHub API tokens connection
In the root folder, create a new file called `github_tokens.txt`. Then, enter GitHub API tokens (one per line) for grating access rights to the scripts.  
They are required for getting content off GitHub via its APIs. The more the better. Refer to this [short guide](https://github.com/blog/1509-personal-api-tokens) if you don't know how to generate one.

## Execution
The SZZ script takes several steps to complete. For each of them, a shell script has been created for the sake of convenience, 
which must be executed in the give order.

### Step 1: Get the local clones of projects 
```bash
$ sh clone-projects.sh project-list.txt /path/to/git/clones/dir [/path/to/symlinks/dir]
```  
* ***Input***
    * `project-list.txt`: A txt file with the slugs (i.e., `owner/name`) of the GitHub project repositories to be cloned (e.g., `apache/kubernets`), one per line.
    * `/path/to/git/clones/dir`: Destination folder where GitHub repos will be cloned to. If the clone is already available, a `git pull` will be executed, instead.
    * `/path/to/simlinks/dir`: For each of the project given in input, a symbolic link will be create, pointing to the related sub-folder in the clone dir.
* ***Output***
    * Projects are cloned (and eventually updated )locally in the given destination folders; slugs are transformed as follows: `apache/metron` =&gt; `apache_____metron` (i.e., '`/`' replaced by 5 underscore chars).

### Step 2: Extract issue and comments for projects
**Notes**: 
* if the `issues` and `comments` tables already contains pre-existing data, the script will add only new data, avoiding 
adding duplicates;
* in GitHub, pull requests are just a different kind of issues; in the database, you can distinguish an issue from a 
pull request by the `pr_num` field, which is not `NULL` for PRs.
* the project input file will be split into smaller files (to suppor resume, see next); they will be stored in the 
`tmp/` sub-folder; the size of these temp files is the same of the number of GitHub access tokens entered in the file
`github-api-tokens.txt`
* the script supports resume on crashes; just relaunch, it will resume where it stopped. Make sure **not** to use the 
`-r` switch, though.

```bash
$ sh extract-data.sh (-r|-i) -f project-list.txt (-n N)
```  
* ***Input***   
    * `-i`: Mutually exclusive command, on the first run it will setup the temp folder content to support auto-resume on re-runs.
    * `-r`: Mutually exclusive command, it will clean the temp folder where to store all the extracted issues; 
    useful to start over from scratch. This option must be used alone. 
    * `-f project-list.txt`: Specifies the txt file with the slugs (one per line) project repositories for which the 
    issues reported on GitHub will be downloaded. Usually, it is the same from *Step 1*.
    * `-n N`: Optional, specifies the size of chunks in which `file` will be split.
* ***Output***
    * All extracted issues are stored in the `issues` table of the database, which has the following structure:
        * `slug`
        * `issue_id`
        * `issue_number`
        * `state`
        * `created_at`
        * `closed_at`
        * `created_by_login`
        * `closed_by_login`
        * `assignee_login`
        * `title`
        * `num_comments`
        * `labels`
        * `pr_num` (is a number whenever the issue is a pull request)
    * All comments extracted from issues and pull requests are stored in the `issue_comments` table, having the same str:
        * `comment_id`                 
        * `slug`
        * `issue_id`
        * `issue_number`
        * `created_at`
        * `updated_at`
        * `user_github_id`
        * `user_login`
        * `body`
    * `tmp/data/`
        * Completed sub-files are deleted as completed; those remaining in there are those that generated an error; 
        try to re-run the script;
    * `extracted/`
        * `done.txt` contains the list of the sub-files removed from `tmp/` that have been processed without errors;
        there are also a bunch of csv files in here, one for the issues and one for the comments extracted from *each* 
        of the sub-files and imported into the database (for debugging purposes, can be safely deleted).
    
### Step 3: Analysis of project developers, and commits plus their linked issues
**Notes:**

* By default, the script runs 16 parallel threads. If you need to adjust this, edit the file `analyze-commits.sh` and 
change the option `--thread=16` to your liking.

```bash
$ sh analyze-commits.sh /path/to/git/repos
``` 

* ***Input***
    * `/path/to/git/repos`: The path of a folder containing the local clones of the repositories whose commits will be 
    blamed. Each repo folder must be in the format `owner_____name`, corresponding to the GitHub slug `owner/name`. 
    This folder is typically the result of *Step 1*. Commits, instead, data are queried from the `commits` table.
* ***Output***
    * The following tables are created in the `multitasking` database:
        * `users`: Info about developers
        * `repos`: The list of project repositories processed
        * `commits`: All the commits extracted from the projects' repositories
        * `commit_files`: Size of changes (LOC added and deleted) to the files changed in a commit
        * `issue_links`: List of issues that that were referenced in a commit (i.e., probably bug fixes) 

### Step 4: Analysis of blamed commits
**Notes:**

* This script leverages the SZZ algorithm to mine bug-inducing commits from the repositories in the database.
* By default, the script runs 16 parallel threads. If you need to adjust this, edit the file `blame-commits.sh` and 
change the option `--thread=16` to your liking.

```bash
$ sh blame-commits.sh /path/to/git/repos
``` 

* ***Input***
    * `/path/to/git/repos`: The path of a folder containing the local clones of the repositories whose commits will be 
    blamed. Each repo folder must be in the format `owner____name`, corresponding to the GitHub slug `owner/name`. 
    This folder is typically the result of *Step 1*. Commits, instead, data are queried from the `commits` table.
* ***Output***
    * Bug-inducing commits are stored in the `blame` table, which has the following structure:
        * `id` 
        * `repo_id`
        * `sha` (the sha of the current, bug-fixing commit)
        * `path`
        * `type` (file types: SRC=0, TEST=1, DOC=2, CFG_BUILD_OTHER=3)
        * `blamed_sha` (the sha of the previous commit that is blamed for introducing a bug)
        * `num_blamed_lines` (the number of lines blamed lines, which required changes to fix the bug)

### Step 5: Developers' alias unmasking
```bash
$ sh alias-unmask.sh
``` 
* ***Input***
    * `None`: The List of developers' `user_id`, `name`, and `emails` is retrieved from the `User` table of the `multitasking` database.
* ***Output***
    * `./dim/dict/aliasMap.dict`: the alias map pickled to a binary file; it contains both the *certain* and the *probable* unmasked aliases (see below)
    * `./dim/idm_map.csv`: the alias map linearized as a CSV file; it contains both the certain and the probable unmasked aliases (see below)
    * `./dim/idm_log.csv`: the rules activated for each *certain* set of unmasked aliases
    * `./dim/idm_log.csv `: the rules activated for each *probable* set of unmasked aliases

### Step 6: Extract cross-references 
This step parses comments from issues/PRs and commits to match references to other projects as either owner/project#number
(e.g., `rails/rails#123`) or owner/project@SHA (e.g., `bateman/dynkaas#70460b4b4aece5915caf5c68d12f560a9fe3e4`).
```bash
$ sh extract-crossrefs.sh
``` 
* ***Input***
    * `None`: Comments are extracted directly from tables `commits` and `issue_comments`
* ***Output***
    * Cross-references are stored in the table `cross_refs`, with the following structure:
        * `id`
        * `from_slug`: the slug of the project where the cross-reference was found in
        * `ref`: the cross-reference itself
        * `comment_type`: indicate whether the reference was found in an issue/pr or in a commit message

### Step 7: Export results as CSV file 
This step already includes developer aliases merging.
```bash
$ sh export-results.sh 
```
* ***Input***
    * `None`: 
* ***Output***
    * `user_project_date_totalcommits.csv`: the file containing the daily contributions for the developers identified through the previous steps working on the given GitHub projects.
    * `user_language_date_totalcommits.csv`: the file containing daily contributions for the developers identified through the previous steps, plus the info on which programming language they used to work on the given GitHub projects.

### Step 8: Compute metrics 

**Notes:**

* The files `user_project_date_totalcommits.csv` and `user_language_date_totalcommits.csv` from the previous step
are implicitly used here to calculate metrics.
%% TODO implement SLanguage metric%%
%% fix issue when parsing user_project_date_totalcommits.csv %%

```bash
$ sh compute-metrics.sh week|month 
``` 
* ***Input***
    * `week|month`: the unit of time to consider, chosen in `{week, month}`.
* ***Output***  
    * `user_week_aggr.csv` / `user_month_aggr.csv`: the file containing the metrics, aggregated by week or month.

