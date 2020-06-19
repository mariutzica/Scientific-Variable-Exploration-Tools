import pydot
from IPython.display import Image, display
import pandas as pd

class VisualGraph:
    
    
    # Words commonly used in the English language
    #frequent_words = pd.read_csv('resources/word_frequency_dispersion.csv')
    #frequent_words = frequent_words.loc[frequent_words['Rank']<=1000,'Word'].tolist()

    relationships = { 'first_degree'  : [ 'isTypeOf', 'hasAttribute', 'hasComponents', 
                                          'hasWWNCategory', 'detSVOCategory' ],
                      'second_degree' : [ 'isRelatedTo', 'isDefinedBy', 'isCloselyRelatedTo' ] }
    plot_rel = ['isTypeOf', 'hasAttribute', 'hasComponents',
                'isRelatedTo', 'isDefinedBy', 'detSVOCategory']
    category_names = ['process', 'property', 'phenomenon', 'role', 'attribute', 'matter',
                             'body', 'domain', 'operator', 'variable', 'part', 'trajectory', 'form',
                             'condition', 'state', 'specializedproperty', 'specializedphenomenon',
                             'specializedprocess']
    
    def __init__(self, graph, root, branches = 2):
        self.viz_graph = pydot.Dot(graph_type="digraph")
        self.existing_nodes = []
        self.graph = graph
        self.create_graph(root, branches)
                     
    def create_graph(self, root, branches = 2):
        
        if branches > 3:
            print('Warning, too many branches! Lowering the value to 3 ...')
            branches = 3

        if not root in self.graph.index_map.keys():
            print('Error, ', root, ' not in provided graph.')
        else:
            self.add_node(root, branches)
            self.add_edges()

    def add_node(self, name, depth):  
        def set_node_color(index_map, name, category_names):
            fillcolor = "white"
            if not name.lower() in index_map.keys():
                fillcolor = "#6cc6e8" #(stub color)
            if name.lower() in category_names:
                fillcolor = "#81eaac"

            return fillcolor

        name_lower = name.lower()
        if (depth > 0):
            fillcolor = set_node_color(self.graph.index_map, \
                                       name_lower, self.category_names)
            if fillcolor == "white":
                name = self.graph.index_map[name_lower]
            if not name_lower in self.existing_nodes:
                node = pydot.Node(name_lower, style = "filled", fillcolor = fillcolor)
                self.viz_graph.add_node(node)        
                self.existing_nodes.append(name_lower)
                if name_lower in self.graph.graph.keys():
                    for key, val in self.graph.graph[name_lower].items():
                        if key in self.plot_rel:
                            d = depth
                            if key in self.relationships['second_degree']: 
                                d = depth-1
                            if isinstance(val, list):
                                for rel_name in val:
                                    self.add_node(rel_name, d)
                            else:
                                self.add_node(val, d)

    def add_edges(self):    

        src_nodes = [x for x in self.existing_nodes]
        for src in src_nodes:
            if src in self.graph.index_map.keys():
                for edge, dest_nodes in self.graph.graph[self.graph.index_map[src]].items():
                    if edge in self.plot_rel:
                        e = edge.replace('hasComponents','hasComponent')
                        if isinstance(dest_nodes, list):
                            for dest in dest_nodes:
                                if dest.lower() in self.existing_nodes:
                                    edge_in = pydot.Edge(src, dest.lower(), label=e)
                                    self.viz_graph.add_edge(edge_in)
                        else:
                            if dest_nodes.lower() in self.existing_nodes:
                                edge_in = pydot.Edge(src, dest_nodes.lower(), label=e)
                                self.viz_graph.add_edge(edge_in)
    
    def display_graph(self):
        im = Image(self.viz_graph.create_png())
        display(im)