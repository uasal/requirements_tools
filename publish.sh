#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# This makes latex beamers / no need for markdown creation with doorstop update
# make -f $SCRIPT_DIR/MakeBeamers

#if [[ "$OSTYPE" == "darwin"* ]]; then
#    #(https://stackoverflow.com/a/8597411)
#    #sed -e 's/{{find}}/{{replace}}/' -e 's/{{find}}/{{replace}}/' {{filename}}
#    # Mac OSX
#    #clean up the titles of the published requirements by remove everything between {# and }
#    sed -i '' -e 's/{.*}//' dist/*.markdown
#    #change published links to point to markdown files:
#    sed -i '' -e 's/.html/.markdown/g' dist/*.markdown
#elif [[ "$OSTYPE" == "freebsd"* ]]; then
#    # assuming FreeBSD is not running GNU sed
#    sed -i '' -e 's/{.*}//' dist/*.markdown
#    sed -i '' -e 's/.html/.markdown/g' dist/*.markdown
#else
#    #run GNU sed in place commands:
#    sed -i -e 's/{.*}//' dist/*.markdown
#    sed -i -e 's/.html/.markdown/g' dist/*.markdown
#fi

python3 $SCRIPT_DIR/RunGraphviz.py

# For generating the Pearl_Requirements.markdown file
# These should no longer be needed with doorstop update that is pending completion (moved to archive-scripts)
#python $SCRIPT_DIR/MarkdownCombiner.py
#python $SCRIPT_DIR/MakeLinksGitHubFriendly.py
#python $SCRIPT_DIR/BeamerLinkCorrection.py

#sed -i 's/{{find}}/{{replace}}/g' {{filename}}
# Note- This doesn't appear to be working. Keeping it for now until verified.
#sed -i ''  -e 's|L0.html\\\#||g' dist/*.tex
#sed -i ''  -e 's|L1.html\\\#||g' dist/*.tex
#sed -i ''  -e 's|L2.html\\\#||g' dist/*.tex
#sed -i ''  -e 's|L3.html\\\#||g' dist/*.tex
#sed -i ''  -e 's|L4-FOA-M1.html\\\#||g' dist/*.tex
#sed -i ''  -e 's|L4-FOA-M2.html\\\#||g' dist/*.tex
#sed -i ''  -e 's|L4-FOA-M2.PMSS.html\\\#||g' dist/*.tex
#sed -i ''  -e 's|L4-FOA-M2.Structure.html\\\#||g' dist/*.tex
#fix internal links:
#sed -i ''  -e 's|href{L|hyperlink{L|g' dist/*.tex  # should not break weblinks so long as they don't start with L

# Commenting this out for now for testing GitHub Workflow with latex compilation so this wouldn't need to be edited
# in this file but just the workflow for directory or name changes.
#cd dist/latex
#xelatex Pearl_Requirements.tex
#xelatex Pearl_Requirements.tex

