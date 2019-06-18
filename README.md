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
* This step is responsible to fetch Github using its API to retrieve issues and comments of a specific project.

```bash
$ sh extract-data.sh <slug> <tokens_file_path> <output_dir>
```  
* ***Input***   
    * `<slug>`: The slug (cloned in the previus step) to process.
    * `<tokens_file_path>`: The Github API tokens to use in fetching issues and comments. 
    useful to start over from scratch. This option must be used alone. 
    * `<output_dir>`: The directory in which `issues.csv` and `comments.csv` file will be stored.
    issues reported on GitHub will be downloaded.
* ***Output***
    * All extracted issues are stored in the `issues.csv` file, which has the following structure:
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
        * `is_pl` (`True` if the issue is a Pull Request, `False`)
    * All comments extracted from issues and pull requests are stored in the `comments.csv` file, having the same str:
        * `comment_id`                 
        * `slug`
        * `issue_id`
        * `issue_number`
        * `created_at`
        * `updated_at`
        * `user_github_id`
        * `user_login`
        * `body`
        
### Step 3: Analysis of blamed commits
**Notes:**

* This script leverages the SZZ algorithm to mine bug-inducing commits from the repository.
* You could run in MPI mode or in standard python mode. 
* To run in MPI mode, use the following:

    ```bash
    $ sh szz.sh <num_mpi_process> <repo_path> <issue_file_path> <out_folder>
    ``` 
* In case of error running `mpiexec` command, you could specify the command path adding it as first paramether to the `szz.sh` command:
    ```bash
    $ sh szz.sh <mpi_exec_path> <num_mpi_process> <repo_path> <issue_file_path> <out_folder>
    ```  
* If you prefer to run in standard python mode, it is enough to omit the MPI required processes:
    ```bash
    $ sh szz.sh <repo_path> <issue_file_path> <out_folder>
    ```  
* ***Input***
    * `<mpi_exec_path>`: Optional. The path where MPIEXEC command is located. 
    * `<num_mpi_process>`:Optional. The number of MPI processes to run.
    * `<repo_path>`: The path of a folder containing the local clones of the repositories whose commits will be 
    blamed. Each repo folder must be in the format `owner____name`, corresponding to the GitHub slug `owner/name`. 
    This folder is typically the result of *Step 1*.
    * `<issue_file_path>`: The file path of `issues.cvs` containing the issues extracted with the *Step 2*.
    * `<out_folder>`: The directory in which to store the processing output.
* ***Output***
    * Commits details are stored in the `commits.csv` file, which has the following structure:
        * `slug`: The repo from which commit are extracted. 
        * `sha`: the commit sha.
        * `timestamp`: UTC timestamp of commit.
        * `author_id`: (custom) identificator of commit author.
        * `commiter_id`: (custom) identificator of committer. 
        * `message`: commit message.
        * `num_parents`: number of commit parents.
        * `num_additions`: number of additions in the commit.
        * `num_deletions`: number of deletions in the commit.
        * `num_files_changed`: number of files chaged by the commit.
        * `files`: semicolon separated list of file involved in the commit.
        * `src_loc_added`
        * `src_loc_deleted`
        * `src_file_touched`
        * `src_files`
    * Contributors details are stored in the file `contributos.csv`, which has the following structure:
        * `slug`: the repo from which the contributors are extracted.
        * `contributor_id`: (custom) identificator assigned to the controìibutor.
        * `name`: the contributor name.
        * `email`: the contributor email.
    * Issue links details are stored in the `issue_links.csv` file. It contains the information about the link between issues and bug-fixing commit, identified by SZZ algorithm:
        * `slug`: the repo identifier analyzed by SZZ.
        * `commit_sha`: the identifier of the bug-fixing commit.
        * `line_num`: number of lines touched to fix the commit.
        * `issue_number`: number identified of the issue closed by the bug-fixing commit.
        * `issue_is_pl`: True if the issue is a pull request, false otherwise.
        * `delta_open`
        * `delta_closed`
    * Commit file details are stored in the `commit_files.csv`, which contains information about each file changed in commit:
        * `slug`: is the repo identified.
        * `sha`: is the identifier of the commit that which the file.
        * `commit_file`: is the changed file name.
        * `loc_ins`
        * `loc_del`
        * `lang`: file types: SRC=0, TEST=1, DOC=2, CFG_BUILD_OTHER=3
    * Blames commit details are stored in the `blames_commit.csv` file, which cotains the detailed information about bug-fixing commit identified by SZZ algorithm and the link with the blamed commit:
        * `slug`: is the repo identifier
        * `bug_fixing_commit`: the identifier of bug-fixing commit.
        * `path`: the file path involved in the commit.
        * `type`: file types: SRC=0, TEST=1, DOC=2, CFG_BUILD_OTHER=3
        * `blamed_commit`: the commit identified which is blamed to have introduced the bug.
        * `num_blamed_lines`: the number of lines blamed.
    * Blamed commit details are stored in the `blamed_commit.csv` file, which contains the details about the commit blamed to have introduced bugs from SZZ algorithm:
        * `slug`: The repo from which commit are extracted. 
        * `sha`: the commit sha.
        * `timestamp`: UTC timestamp of commit.
        * `author_id`: (custom) identificator of commit author.
        * `commiter_id`: (custom) identificator of committer. 
        * `message`: commit message.
        * `num_parents`: number of commit parents.
        * `num_additions`: number of additions in the commit.
        * `num_deletions`: number of deletions in the commit.
        * `num_files_changed`: number of files chaged by the commit.
        * `files`: semicolon separated list of file involved in the commit.
        * `src_loc_added`
        * `src_loc_deleted`
        * `src_file_touched`
        * `src_files`
         
### Step 4: Developers' alias unmasking
```bash
$ sh alias-unmask.sh <input_dir> <out_dir>
``` 
* ***Input***
    * `<input_dir>`: The path where `*_contributrs.csv` files are stored, to use as input.
    * `<out_dir>`: The path where to put the process result.
* ***Output***
    * `./dim/dict/aliasMap.dict`: the alias map pickled to a binary file; it contains both the *certain* and the *probable* unmasked aliases (see below)
    * `./dim/idm_map.csv`: the alias map linearized as a CSV file; it contains both the certain and the probable unmasked aliases (see below)
    * `./dim/idm_log.csv`: the rules activated for each *certain* set of unmasked aliases
    * `./dim/idm_log.csv `: the rules activated for each *probable* set of unmasked aliases

### Step 5: Extract cross-references 
This step parses comments from issues/PRs and commits to match references to other projects as either owner/project#number
(e.g., `rails/rails#123`) or owner/project@SHA (e.g., `bateman/dynkaas#70460b4b4aece5915caf5c68d12f560a9fe3e4`).
```bash
$ sh extract-crossrefs.sh <input_dir>
``` 
* ***Input***
    * `<input_dir>`: The directory to inspect to make cross references.
* ***Output***
    * Cross-references are stored in the file `cross_references.csv`, with the following structure:
        * `id`
        * `from_slug`: the slug of the project where the cross-reference was found in
        * `ref`: the cross-reference itself
        * `comment_type`: indicate whether the reference was found in an issue/pr or in a commit message

### Step 6: Export results as CSV file 
This step already includes developer aliases merging.
```bash
$ sh export-results.sh <input_dir> <out_dir>
```
* ***Input***
    * `<input_dir>`: the directory to fetch as input.
    * `<out_dir>`: the path where to store the export results.
* ***Output***
    * `user_project_date_totalcommits.csv`: the file containing the daily contributions for the developers identified through the previous steps working on the given GitHub projects.
    * `user_language_date_totalcommits.csv`: the file containing daily contributions for the developers identified through the previous steps, plus the info on which programming language they used to work on the given GitHub projects.
