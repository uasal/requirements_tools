## Branch Info / Summary
- Contains publish.sh updates for adding L4 requirements
  - Part of this script looks like it has components that are not working but leaving them as is for now and have comments to the areas in question
- Contains Markdown combiner test script for if someone is viewing the markdown requirements on GitHub for the links to work better
  - Separate files for the markdown requirements on GitHub (if viewing in browser) will go to the right section now but the page refreshed to the top requiring the user to manually refresh the page again to be linked to the section they clicked on
- Fix to the Markdown links
- Visual fix to latex href links (pink -> blue)
  - Pandocs defaults to pink for the external url links
- Graphviz fix for level 4 requirements
  - (Once the level fix for doorstop is implemented this file should no longer have to be edited further)
- Latex Beamer Link Fix
  - L4-FOA-PMSS and L4-FOA-Struct not linking correctly in latest.pdf produced from beamers
  - Error in beamers / .html is being kept in converting html to beamer  
- Doorstop Update Adjustments
  - Directory updates / changes to appropriate impacted files.
  - RunGraphviz.py adjustments for Doorstop change to 'header' variable instead of 'short name'
    - Additional adjustments to directory change to point to dist/latex
  - Scripts that are no longer being used with updates have been moved to the Archives-Scripts directory.
  - Name to output latex beamer document changes to Pearl_Requirements.
    - (Primarily naming it something that doesn't start with an 'l' for the L?.tex outputs to be the only ones targeted)
  - Previous MakeMarkdown (copy in archive-scripts directory) renamed to MakeBeamers.
    - Adjusted for latex beamers to be generated from L?.tex doorstop outputs in the dist/latex directory.
  - Publish.sh adjusted with script changes.
    - Directories updated for compiling latex beamer (Pearl_Requirements.tex)