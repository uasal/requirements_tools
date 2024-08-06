# requirements_tools
## General Overview
Scripts and tools for primarily the `pearl_requirements` repository both in [GitHub](https://github.com/uasal/pearl_requirements) and in [GitLab](https://gitlab.sc.ascendingnode.tech/pearl-systems/pearl_requirements) to use. 

Contains previously used tools for the repository (_in the archive-scripts directory_) that are no longer being used but could be useful still in another repository or a later application.

------------------------
## Tools Overview
### [RunGraphviz.py](RunGraphviz.py)
For generating Requirement Flow and Requirement Connections graphs from requirements that are imported with doorstop.

### [get_gitinfo.sh](get_gitinfo.sh)
For collecting the git information to be used in requirements' documentation.

### [publish.sh](publish.sh)
Runs the commands for starting scripts within the repository. (Currently only running `get_gitinfo.sh` and `RunGraphviz.py`)

### [requirements.txt](requirements.txt)
Update this file for updating any versions of tools that are being utilized for `requirements_tools` repository or within `pearl_requirements`.

### [archive-scripts](archive-scripts/)
Directory of previously used scripts for `requirements_tools` that are now '_archived_' but could be used again in a different application or repository. 

###### Contains the following:
- [`BeamerLinkCorrection.py`](archive-scripts/BeamerLinkCorrection.py)
- [`MakeBeamers`](archive-scripts/MakeBeamers)
- [`MakeMarkdown`](archive-scripts/MakeMarkdown)
- [`MakeLinksGitHubFriendly.py`](archive-scripts/MakeLinksGitHubFriendly.py)
- [`MarkdownCombiner.py`](archive-scripts/MarkdownCombiner.py)