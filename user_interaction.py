from IPython.display import display, HTML
import knowledge_graph as kg
import knowledge_graph_visualizer as kg_viz
import pandas as pd

# get user input
def ask_for_var_input():
    return input(('What is the scientific variable you would like to describe?\n'
                  'Please keep your description relatively brief. Examples include:\n' 
                  'crop yield, soil moisture, food availability, drought.\n\n>>>  '))

# parse user input and generate a report on the desired variable
def generate_document(depth = 2, \
                      graphfile = 'resources/scivar_kg.json', \
                      svoindexfile = 'resources/scivar_svo_index_map.txt', \
                      indexmapfile = 'resources/scivar_index_map.json', \
                      #graphfile = 'resources/world_modelers_indicators_kg.json', \
                      #svoindexfile = 'resources/svo_index_map.txt', \
                      write_graph = True):

    # Get requested variable from user
    variable_input = ask_for_var_input()
    
    # Generate knowledge graph for user input
    #     for fast results, levels should be set to 1
    #     for more accurate results, levels should be set to 2
    #     levels should NOT be set to a value higher than 3
    if depth > 3:
        print('''Warning, depth is set to {}. This value is higher
                 than recommended and may result in slow processing times and
                 too much deviation from the intended meaning. Therefore, value is
                 being reset to optimum: levels == 2.'''.format(depth))
        depth = 3
    concept_graph = kg.SciVarKG(graphfile = graphfile, svoindexfile = svoindexfile)
    
    concept_graph.add_concept(variable_input, depth)
    
    # Generate inference properties for knowledge graph.
    concept_graph.graph_inference()
    
    if write_graph:
        concept_graph.write_graph()
        concept_graph.write_svo_index_map()
        concept_graph.write_index_map()

    # Generate a visualization of the core graph nodes
    vizgraph = kg_viz.VisualGraph(concept_graph, variable_input)
    vizgraph.display_graph()
    
    display_svo_categorizations(concept_graph, variable_input)
    
    display_related_terms(concept_graph, variable_input)
    
    display_wm_indicators(concept_graph, variable_input)
    
    display_svo_variables(concept_graph, variable_input)
    
    return concept_graph
        
def display_svo_categorizations(graph, user_input):
    
    use_index = graph.index_map[user_input.lower()]
    det_category = graph.graph[use_index]['detSVOCategory']
    print('The terms you entered were classified as a {}.'.format(det_category))
    if det_category == 'Variable':
        print('This is minimally sufficient to classify as a variable.')
    elif det_category == 'Property':
        print('You will need to specify the Phenomenon observed (object of observation)')
        print('in order to completely define your variable.')
    elif det_category == 'Process':
        print('You will need to specify the Phenomenon observed (object of observation)')
        print('as well as a Property in order to completely define your variable.')
    elif det_category == 'Phenomenon':
        print('You will need to specify the Property (or characteristic) of the Phenomenon')
        print('in order to completely define your variable.')
    else:
        print('You will need to identify a clear Phenomenon and Property to ')
        print('completely identify your variable.')
        
def display_related_terms(graph, user_input):
    use_index = graph.index_map[user_input.lower()]
    if 'modified_terms' in graph.graph[use_index].keys():
        modified_terms = graph.graph[use_index]['modified_terms']
        if modified_terms != []:
            print('I found {} types of {}.'.format(len(modified_terms),user_input))
            if len(modified_terms) > 5:
                print('Here are the first five ...')
            else:
                print('Here they are ...')
            for modterm in modified_terms[:5]:
                print('\t{}'.format(modterm))
    if 'term_aspects' in graph.graph[use_index].keys():
        term_aspects = graph.graph[use_index]['term_aspects']
        if term_aspects != []:
            print('I found {} more complex aspects of {}.'.format(len(term_aspects),user_input))
            if len(term_aspects) > 5:
                print('Here are the first five ...')
            else:
                print('Here they are ...')
            for terms in term_aspects[:5]:
                print('\t{}'.format(terms))

def display_wm_indicators(graph, user_input):
    use_index = graph.index_map[user_input.lower()]
    if 'hasWMIndicator' in graph.graph[use_index]:
        indicators = graph.graph[use_index]['hasWMIndicator']
        all_vars = pd.DataFrame(columns = ['indicatorlabel', 'varrank'])
        for key, val in indicators.items():
            all_vars.loc[len(all_vars)] = [key, val]
        all_vars = all_vars.sort_values(by = 'varrank', ascending = False)
        print('I found {} World Modelers indicators related to this search.'.format(len(all_vars)))
        if len(all_vars) > 10:
            print('Here are the first ten results ...')
        else:
            print('Here they are ...')
        
        for index, row in all_vars.head(10).iterrows():
            print('\t{}\t{}'.format(row['indicatorlabel'], row['varrank']))
        
def display_svo_variables(graph, user_input):
    use_index = graph.index_map[user_input.lower()]
    if 'hasSVOVar' in graph.graph[use_index]:
        variables = graph.graph[use_index]['hasSVOVar']
        all_vars = pd.DataFrame(columns = ['varlabel', 'varrank'])
        for key, val in variables.items():
            all_vars.loc[len(all_vars)] = [graph.svo_index_map[key]['preflabel'], val]
        all_vars = all_vars.sort_values(by = 'varrank', ascending = False)
        print('I found {} SVO variable related to this search.'.format(len(all_vars)))
        if len(all_vars) > 10:
            print('Here are the first ten results ...')
        else:
            print('Here they are ...')
        
        for index, row in all_vars.head(10).iterrows():
            print('\t{}\t{}'.format(row['varlabel'], row['varrank']))