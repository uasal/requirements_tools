
# python MakeLinksGitHubFriendly.py

# For version of markdown / pandoc being used and for them to work in the github environment, 
# link portions to the sections must be lower-cased. 
# Example: [L1-0002](L1.markdown#l1-0002)

import glob
import os

md_files=glob.glob("dist/markdown/L*.markdown")
for markd_file in md_files:
    with open(markd_file+".out", "wt") as fout:
        with open(markd_file, "rt") as fin:
            for line in fin:
                if "#" in line:
                    split_into_lines=line.split("[")
                    new_line=''
                    for i,s2 in enumerate(split_into_lines):
                    #print(s2)
                        if "#" in s2:
                            split_links=s2.split("#")
                            new_link=split_links[0] + "#" + split_links[1].lower().replace('.', '').replace(' ','').replace(")",") ")#+'-'
                        if i >0:
                            new_line+="  ["+new_link
                        else:
                            new_line = s2
                    #print(new_line)
                    line=new_line
                #else:
                #print(line)
                fout.write(line) 
    fout.close()
    fin.close()
    os.rename(markd_file+".out", markd_file)

