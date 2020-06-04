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
def generate_document(levels = 1, load_graph = None, graph_index_map = None, write_graph = False):

    # Get requested variable from user
    variable_input = ask_for_var_input()
    
    # Generate knowledge graph for user input
    #     for fast results, levels should be set to 1
    #     for more accurate results, levels should be set to 2
    #     levels should NOT be set to a value higher than 3
    if levels > 3:
        print('''Warning, levels is set to {}. This value is higher
                 than recommended and may result in slow processing times and
                 too much deviation from the intended meaning. Therefore, value is
                 being reset to optimum: levels == 2.'''.format(levels))
        levels = 2
    concept_graph = kg.create_graph(variable_input, levels, graph = load_graph, \
                                   write_graph = write_graph)
    kg.print_svo_index_map()
    
    # Generate inference properties for knowledge graph.
    [concept_graph, index_map] = kg.graph_inference(concept_graph, graph_index_map)
    
    # Generate a visualization of the core graph nodes
    kg_viz.create_graph(concept_graph, index_map, variable_input)
    
    display_svo_categorizations(concept_graph, index_map, variable_input)
    
    display_related_terms(concept_graph, index_map, variable_input)
    
    display_wm_indicators(concept_graph, index_map, variable_input)
    
    display_svo_variables(concept_graph, index_map, variable_input)
    
    return [concept_graph, index_map]
        
def display_svo_categorizations(graph, index_map, user_input):
    
    det_category = graph[index_map[user_input.lower()]]['detSVOCategory']
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
        
def display_related_terms(graph, index_map, user_input):
    if 'modified_terms' in graph[index_map[user_input.lower()]].keys():
        modified_terms = graph[index_map[user_input.lower()]]['modified_terms']
        if modified_terms != []:
            print('I found {} types of {}.'.format(len(modified_terms),user_input))
            if len(modified_terms) > 5:
                print('Here are the first five ...')
            else:
                print('Here they are ...')
            for modterm in modified_terms[:5]:
                print('\t{}'.format(modterm))
    if 'term_aspects' in graph[index_map[user_input.lower()]].keys():
        term_aspects = graph[index_map[user_input.lower()]]['term_aspects']
        if term_aspects != []:
            print('I found {} more complex aspects of {}.'.format(len(term_aspects),user_input))
            if len(term_aspects) > 5:
                print('Here are the first five ...')
            else:
                print('Here they are ...')
            for terms in term_aspects[:5]:
                print('\t{}'.format(terms))

def display_wm_indicators(graph, index_map, user_input):
    if 'hasWMIndicator' in graph[index_map[user_input.lower()]]:
        indicators = graph[index_map[user_input.lower()]]['hasWMIndicator']
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
        
def display_svo_variables(graph, index_map, user_input):
    svo_index_map = kg.get_svo_index_map()
    
    if 'hasSVOVar' in graph[index_map[user_input.lower()]]:
        variables = graph[index_map[user_input.lower()]]['hasSVOVar']
        all_vars = pd.DataFrame(columns = ['varlabel', 'varrank'])
        for key, val in variables.items():
            all_vars.loc[len(all_vars)] = [svo_index_map[key]['preflabel'], val]
        all_vars = all_vars.sort_values(by = 'varrank', ascending = False)
        print('I found {} SVO variable related to this search.'.format(len(all_vars)))
        if len(all_vars) > 10:
            print('Here are the first ten results ...')
        else:
            print('Here they are ...')
        
        for index, row in all_vars.head(10).iterrows():
            print('\t{}\t{}'.format(row['varlabel'], row['varrank']))