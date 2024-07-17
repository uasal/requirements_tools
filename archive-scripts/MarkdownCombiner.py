# For correcting the markdown output for pandoc / combining them into one file
# Changes will need to be made for this if the 'level fix' is merged (multiple level 4 csv and how doorstop handles it)
# For now, doing it like this for it to work as the way it is as changes are still being done to the requirements.
# Updates to markdown being used and conversion methods will adjust what needs to be fixed for it to work as intended.

# Imports -------------------------------------------------------------------------------------------------------------

import glob
import os

# Variables -----------------------------------------------------------------------------------------------------------

# File variables
md_files = sorted(glob.glob("dist/markdown/L*.markdown"))
output_file = "dist/markdown/Pearl_Requirements.markdown"

# Dict of items to replace for each line (varies on version / temp fix) for the combined markdown file generation.
replacements = {"==================": "------------------", "================": "----------------",
                "==============": "--------------", "=======": "-------", ":*\\": ":*", "\\_": "_",
                "(L0.markdown#L": "(#L", "(L1.markdown#L": "(#L", "(L2.markdown#L": "(#L", "(L3.markdown#L": "(#L",
                "(L4-FOA-M1.markdown#L4-FOA-M1": "(#L4-FOA-M1", "(L4-FOA-M2.markdown#L4-FOA-M2": "(#L4-FOA-M2",
                "(L4-FOA-Structure.markdown#L4-FOA-Struct": "(#L4-FOA-Struct",
                "(L4-FOA-PMSS.markdown#L4-FOA-PMSS": "(#L4-FOA-PMSS"}

# Dict of items to replace for generating subsections in the toc correctly (temp fix / will change with level fix)
toc_replacements = {"L4-FOA-M1-0001 \n": "   - [FOA-M1](#L4-FOA-M1-0001)",
                    "L4-FOA-M2-0001 \n": "   - [FOA-M2](#L4-FOA-M2-0001)",
                    "L4-FOA-PMSS-0001 \n": "   - [FOA-PMSS](#L4-FOA-PMSS-0001)",
                    "L4-FOA-Struct-0001 \n": "   - [FOA-Structure](#L4-FOA-Struct-0001)"}

# For checking if a subsection is present in a line
subsections = ("L4-FOA-M1-0001 \n", "L4-FOA-M2-0001 \n", "L4-FOA-PMSS-0001 \n", "L4-FOA-Struct-0001 \n")

# Placeholder if matrix is desired to be added to file (don't really recommend this for this version of doorstop)
traceability_file = "dist/index.markdown"

# Level variables for methods to utilize. Max level shouldn't be needed after the level fix / temp solution to deal
# with the extra files that are being read that go past the actual levels.
max_level = 4
level = int()


# For replacing parts of the line with different values to convert to markdown ----------------------------------------

def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text


# Removes the previous output file if it exists -----------------------------------------------------------------------

if os.path.exists(output_file):
    os.remove(output_file)
    print("Removed existing file: " + output_file)

# Shows what files were used in the process (for checking / verifying) ------------------------------------------------
# Can be removed or commented out if not desired.

print("---------------Used the following files:---------------")
for x in range(len(md_files)):
    print(md_files[x], )
print("--------------End of the following files:--------------")

# Table of Contents Generator -----------------------------------------------------------------------------------------

output = open(output_file, "wt")
output.write("# Table of Contents\n")

# For every level that is within what should be the max level (set manually), it will generate a bullet list with a
# link to that location in the markdown. Otherwise, it will check if it is a subsection (set manually) and indent from
# the last level with a link. Will change after level fix / should have the subsection for both cases but know that
# there are no subsections currently for levels 0-3.

for file in md_files:
    if level <= max_level:
        output.write("- [Level " + str(level) + "](#Level-" + str(level) + ")\n")
        level = level + 1
    with open(file, "rt") as reading_file:
        for line in reading_file:
            if any(s in line for s in subsections):
                adjusted_line = replace_all(line, toc_replacements)
                output.write(adjusted_line + "\n")

# Extra space before copying over the lines from the other files
output.write("\n")

# Resetting level for the next process
level = 0

# Reading / Writing process -------------------------------------------------------------------------------------------

# Added a line for the level for each file that is read that is within the max level range (temp until level fix)
# Replaces / corrects lines based on the replacements dict

for file in md_files:
    with open(file, "rt") as reading_file:
        if level <= max_level:
            output.write("\n----\n# Level-" + str(level) + "\n\n")
            level = level + 1
            for line in reading_file:
                adjusted_line = replace_all(line, replacements)
                output.write(adjusted_line)
        else:
            output.write("\n")
            for line in reading_file:
                adjusted_line = replace_all(line, replacements)
                output.write(adjusted_line)
    reading_file.close()

# Closing out opened files --------------------------------------------------------------------------------------------

output.close()
print("Completed markdown link correction.")
