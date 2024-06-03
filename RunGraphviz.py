print('generating graphviz diagram with graphviz for python')
from graphviz import Digraph, Graph
import yaml
import numpy as np
import doorstop
import textwrap
np.random.seed(0)
tree=doorstop.core.build()

dot = Digraph(comment='The Requirements', format='png')
dot.body.extend([ 'rankdir = LR\n','ratio = .65\n','size = "75,50"\n','rank = min\n', 'dpi = "25"\n'])
dot.node_attr.update(color='lightblue2', style='filled',fontsize="55")

show_orphans=True
use_id=True
use_short_names=True
colors=['black','blue','chocolate','crimson', 'orchid', 'green','darkgreen','khaki','violet','purple','orange','lightblue2',]
n_colors = len(colors)

# Adding additional colors for levels as its potentially treating each csv as a different level so
# there are currently 8 levels its potentially trying to add into there at the moment.
level_colors = ['yellow','gray88','lightblue','green','violet','crimson','blue','khaki',]

for doc_n, document in  enumerate(tree.documents):

    # Skips level 4:
    if doc_n >3:
        continue
    for i,item in enumerate(document.items):
        content=""
        if use_id:
            content=item.uid.value+"\n"
        if use_short_names:
            content=content+str(item.data["header"])
        else:
            content=content+item.uid.value+"\n"+textwrap.fill(item.text,35)
        #skip items that have no back links, unless they are the first level
        if  show_orphans:
            dot.node(item.uid.value,content,color=level_colors[doc_n])#item.text)
        elif (len(item.links) >0) | (doc_n ==0):
            dot.node(item.uid.value,content,color=level_colors[doc_n])#item.text)
        else:
            print("skipping: "+item.uid.value)
            continue
        for link in item.links:
            width=str(np.random.rand()*5+5)
            if link.value[:6] ==item.uid.value[:6]:
                style='dashed'
            else:
                style='solid'
            dot.edge(link.value,item.uid.value,
                     color=colors[i % n_colors],
                     style=style,
                      penwidth=width)#, constraint='false')

#subgraph style:
attribs=dict(nodesep="0.01",ranksep=".02",ratio=".7")
g = Digraph(comment='The Requirements', format='png',
                engine="twopi",
        graph_attr=attribs,
                )
#g.body.extend([ 'ratio=.55','ranksep=.02']) #,
#g.body.extend([ 'rankdir=LR','ratio=.65','size="75,50"','rank=min', "dpi = 125",'nodesep=.02',]) #,
#g.node_attr.update(color='lightblue2', style='filled',fontsize="55")

for doc_n, document in  enumerate(tree.documents):
    print(level_colors[doc_n])
    # Skips level 4:
    if doc_n >3:
        continue
    nodes=[]
    edges=[]
    for i,item in enumerate(document.items):
        content=""
        if use_id:
            content=item.uid.value+"\n"
        if use_short_names:
            content=content+str(item.data["header"])
        else:
            content=content+item.uid.value+"\n"+textwrap.fill(item.text,35)
        #skip items that have no back links, unless they are the first level
        if  show_orphans:
            nodes.append(item.uid.value)#item.text)
        elif (len(item.links) >0) | (doc_n ==0):
            nodes.append(item.uid.value)#item.text)
        else:
            print("skipping: "+item.uid.value)
            continue
        for link in item.links:
            width=str(np.random.rand()*5+5)
            if link.value[:6] ==item.uid.value[:6]:
                style='dashed'
            else:
                style='solid'
            edges.append((link.value,item.uid.value))
          
    print(edges)
    with g.subgraph(name="cluster"+str(i)) as c:
            #c.attr(style='filled', color='lightgrey')
            #c.node_attr.update(color=level_colors[doc_n])
            #for n in nodes:
        #c.node(str(n))
            c.attr(color='blue')
            c.node_attr['style'] = 'filled'
            c.node_attr['nodesep'] = '.1'
            c.node_attr['color'] = level_colors[doc_n]
            #c.node_attr['fontsize'] ='18pt'
            
            c.edges(edges)
            for i,item in enumerate(document.items):
                c.node(item.uid.value,label=item.uid.value
                +"\n"+item.data["header"],
                           bgcolor=level_colors[doc_n],
                           fontsize="24",
                           #sep="+1"
                           #margin="0.4"
                           )
        #c.attr(label='process #1')
#g.body.extend(['ratio=.6','size="75,50"','ranksep=".25"', "dpi = 160"]) #,

g.attr(overlap='prism1000')
g.body.append('fontsize=18')
g.render("dist/latex/subgraphs")
            
dot.body.append('fontsize=20')
dot.render('dist/latex/Digraph_gv')#save("dot.svg")

print('graphviz rendered')
