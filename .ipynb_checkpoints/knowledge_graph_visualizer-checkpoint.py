import pydot
from IPython.display import Image, display
import pandas as pd

# Words commonly used in the English language
frequent_words = pd.read_csv('resources/word_frequency_dispersion.csv')
frequent_words = frequent_words.loc[frequent_words['Rank']<=1000,'Word'].tolist()

rel_first = ['isTypeOf', 'hasAttribute', 'hasComponentNounConcept', 'hasWWNCategory',
             'hasSynonym','detSVOCategory']
rel_second = ['isRelatedTo','isDefinedBy', 'components','isClsRel']
rel_keys = ['isTypeOf', 'hasAttribute', 'hasComponentNounConcept',
            'isRelatedTo', 'hasSynonym', 'isDefinedBy',
           'detSVOCategory', 'components']
        
# create the pydot graph
def create_graph(graph, root, branches = 2):
    G = pydot.Dot(graph_type="digraph")
    if branches > 3:
        print('Warning, too many branches! Lowering the value to 3 ...')
        branches = 3
        
    if not root in graph.keys():
        print('Error, ', root, ' not in provided graph.')
    else:
        [G, nodes] = add_node(G, graph, root, branches)
        G = add_edges(G, graph, nodes)
    
    display_graph(G)

# add a node to the graph by name
def add_node(G, graph, name, depth, existing_nodes = None):    

    if existing_nodes is None:
        existing_nodes = []
    if (depth > 0) and \
        not name.lower() in existing_nodes:
        fillcolor = set_node_color(graph, name)
        #fill color will be changed according to type
        node = pydot.Node(name.lower(), style = "filled", fillcolor = fillcolor)
        G.add_node(node)        
        existing_nodes.append(name.lower())
        if name.lower() in graph.keys():
            for key, val in graph[name.lower()].items():
                if key in rel_keys:
                    d = depth
                    if key in rel_second: 
                        d = depth-1
                    if isinstance(val, list):
                        for rel_name in val:
                            [G, existing_nodes] = add_node(G, graph, rel_name, d, existing_nodes)
                    else:
                        [G, existing_nodes] = add_node(G, graph, val, d, existing_nodes)
                    
    return [G, existing_nodes]

def set_node_color(graph, name):
    category_names = ['process', 'property', 'phenomenon', 'role', 'attribute', 'matter',
                     'body', 'domain', 'operator', 'variable', 'part', 'trajectory', 'form',
                 'condition', 'state', 'specializedproperty', 'specializedphenomenon',
                 'specializedprocess']
    fillcolor = "white"
    if not name.lower() in graph.keys():
        fillcolor = "#6cc6e8" #(stub color)
    if name.lower() in category_names:
        fillcolor = "#81eaac"

    return fillcolor

# add a node to the graph by name
def add_edges(G, graph, existing_nodes):    

    src_nodes = [x for x in existing_nodes]
    for src in src_nodes:
        if src in graph.keys():
            for edge, dest_nodes in graph[src].items():
                if edge in rel_keys:
                    e = edge.replace('components','hasComponent')
                    if isinstance(dest_nodes, list):
                        for dest in dest_nodes:
                            if dest.lower() in existing_nodes:
                                edge_in = pydot.Edge(src, dest.lower(), label=e)
                                G.add_edge(edge_in)
                    else:
                        if dest_nodes.lower() in existing_nodes:
                            edge_in = pydot.Edge(src, dest_nodes.lower(), label=e)
                            G.add_edge(edge_in)
    
    return G
    
def display_graph(G):
    im = Image(G.create_png())
    display(im)