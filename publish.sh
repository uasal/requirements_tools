doorstop publish all ./dist
#doorstop publish all ./markdown -m
#call pandoc to convert html to markdown
make -f MakeFile

if [[ "$OSTYPE" == "darwin"* ]]; then
    #(https://stackoverflow.com/a/8597411)
    #sed -e 's/{{find}}/{{replace}}/' -e 's/{{find}}/{{replace}}/' {{filename}}
    # Mac OSX
    #clean up the titles of the published requirements by remove everything between {# and } 
    sed -i '' -e 's/{.*}//' dist/*.markdown
    #change published links to point to markdown files:
    sed -i '' -e 's/.html/.markdown/g' dist/*.markdown
elif [[ "$OSTYPE" == "freebsd"* ]]; then
    # assuming FreeBSD is not running GNU sed
    sed -i '' -e 's/{.*}//' dist/*.markdown
    sed -i '' -e 's/.html/.markdown/g' dist/*.markdown
else
    #run GNU sed in place commands:
    sed -i -e 's/{.*}//' dist/*.markdown
    sed -i -e 's/.html/.markdown/g' dist/*.markdown
fi
python RunGraphviz.py
python MakeLinksGitHubFriendly.py

#./guides/example_hook.sh

#to make latex beamer slides, uncomment next three lines:
make -f MakeBeamer

#sed -i 's/{{find}}/{{replace}}/g' {{filename}}
sed -i ''  -e 's|L0.html\\\#||g' dist/*.tex
sed -i ''  -e 's|L1.html\\\#||g' dist/*.tex
sed -i ''  -e 's|L2.html\\\#||g' dist/*.tex
sed -i ''  -e 's|L3.html\\\#||g' dist/*.tex
#fix internal links:
sed -i ''  -e 's|href|hyperlink|g' dist/*.tex  #caution, this might breake weblinks

cd dist
xelatex beamer.tex


