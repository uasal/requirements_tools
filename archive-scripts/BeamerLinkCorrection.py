# HTML to LaTeX beamer link corrector

# For a temp fix to beamer links being incorrect for some L4 requirement references.
# Appears to be occurring at the HTML level / maybe how Doorstop is publishing for this version with longer prefixes?
# Later updates / open GitHub Issue tasks look like they will fix this but will be awhile until its fully working
# (Doorstop & Modules Updates)
# Eventually will combine some scripts or remove them (with updates) for fewer files / places to change overall.

import glob
import os

# Variables -----------------------------------------------------------------------------------------------------------

# File variables
beamer_files = sorted(glob.glob("dist/documents/L*_beamer.tex"))

replacements = {"{L4-FOA-M1.html\\#": "{",
                "{L4-FOA-M2.html\\#": "{",
                "{L4-FOA-Structure.html\\#": "{",
                "{L4-FOA-PMSS.html\\#": "{"}


# For replacing parts of the line with different values to convert to markdown ----------------------------------------

def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text


# Shows what files were used in the process (for checking / verifying) ------------------------------------------------
# Can be removed or commented out if not desired.

print("---------------Used the following files:---------------")
for x in range(len(beamer_files)):
    print(beamer_files[x], )
print("--------------End of the following files:--------------")

# For fixing the html reference showing up in beamer links for some L4 ------------------------------------------------

for beamer in beamer_files:
    with open(beamer, "r") as reading_file:
        with open(beamer +".out", "w") as output_file:
            for line in reading_file:
                # Uses the replacements dict for this process. To add more, edit the replacements dict variable.
                adjusted_line = replace_all(line, replacements)
                output_file.write(adjusted_line)
    reading_file.close()
    output_file.close()
    # Remove existing beamer file with link issues and replace with new one.
    if os.path.exists(beamer):
        os.remove(beamer)
        os.rename(beamer+".out", beamer)

print("Completed beamer link correction.")