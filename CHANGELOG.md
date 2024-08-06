# Change Log
Overview of adjustments done in `requirements_tools`. Broken down into changes done per branch updates.

----------------
## u/sfrinaldi/gitlab-workflow
Adjusted `publish.sh` for python command to be `python3` instead for working in gitlab. Changes work with doorstop (_v3.0b1.5-1.0.0_).
- Updated README.md for repository link references
  - _(Adding GitLab repository link)_


----------------
## u/sfrinaldi/doorstop-update
Adjustments to `requirements_tools` for working with the newer version of doorstop (_v3.0b1.5-1.0.0_) and updating other components (_like the graphviz version being used_).

Pull Request [#6](https://github.com/uasal/requirements_tools/pull/6)
- Update to `publish.sh` 
  - Part of this script looks like it has components that are not working but leaving them as is for now and have comments to the areas in question
  - Majority of scripts no longer need to run / doorstop update fixes formating issues with URL and pandocs not used anymore.
- `Graphviz.py` fix for level 4 requirements
  - Level fix for doorstop is implemented this file should no longer have to be edited often even if more levels are added to graph generation.
    - Should be able to handle up to 8 levels (_7 levels if starting at Level 0_)
  - `Graphviz.py` set to only display a graph with using _L0-L3_ requirements at the moment. _(Graph hard to visualize with all the levels)_ 
- Doorstop Update Adjustments
  - Directory updates / changes to appropriate impacted files.
  - `RunGraphviz.py` adjustments for Doorstop change to '`header`' variable instead of `short name`
    - Additional adjustments to directory change to point to dist/latex
    - **Switched this back to `short name` as `short name` attribute was added manually to `doorstop-ewan` clone** (_v3.0b1.5-1.0.0_).
  - Scripts that are no longer being used with updates have been moved to the `archives-scripts` directory.
  - Previous `MakeMarkdown` (_copy in archive-scripts directory_) renamed to `MakeBeamers`.
    - Adjusted for latex beamers to be generated from `L?.tex` doorstop outputs in the `dist/latex` directory.
    - No longer being uses / moved to `archives-scripts` directory.

----------------
## u/sfrinaldi/beamer-fix
Fixing linking format issues that were present in latex beamers that were generated with pandoc from doorstop html file outputs.

Pull Request [#4](https://github.com/uasal/requirements_tools/pull/4)
- Created `BeamerLinkCorrection.py` to fix formating 
  - Will later not be needed with doorstop update tasks
- Added call to `BeamerLinkCorrection.py` to `publish.sh `

----------------
## u/sfrinaldi/md-link-fix
Correction to markdown links to work correctly that were generated with pandocs from doorstop version (_v1.0.02-1.0.0_). Should no longer be needed with pending doorstop update tasks.

Pull Request [#3](https://github.com/uasal/requirements_tools/pull/3)
- Edited `MakeLinksGitHubFriendly.py`.
- Added `MarkdownCombiner.py` for if user is viewing on GitHub.
  - Links to other markdown files will automatically go to the right location but refresh back to the top unless you manually refresh again.
- Added call to `MarkdownCombiner.py` in `publish.sh`.

----------------
## u/sfrinaldi/L4_publish_fix
Fixes issues with publishing level 4 requirements with current doorstop version (_v1.0.2-1.0.0_) being used.

Pull Request [#2](https://github.com/uasal/requirements_tools/pull/2)
- Added additional `level_colors` for graphviz to pull from
  - Currently reading in all the requirement levels and treats each csv file read in as a 'level' instead of its actual value so it runs out of `color_levels` to pull from.
  - Level fix for how doorstop reads in multiple csv files for one level rank will fix this as well (_in doorstop update tasks_).

----------------
## u/sfrinaldi/graphviz_fix
First adjustment to graphviz for additional level 4 requirements to publish (_was only one csv files at the time_).

Pull Request [#1](https://github.com/uasal/requirements_tools/pull/1)
- Edited `graphviz.py` to have another color in level_colors for it to run. 
- Attempted to update graphviz version as well 

