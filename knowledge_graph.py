import wiktiwordnetapi as wwnapi
import parse_tools as pt
import pandas as pd
import svo_api as svoapi
import wikipediaapi as wapi
import numpy as np
import json

# Categories and classes from SVO and wiktiwordnet; these are considered very general terms
# and should not be further broken down. Consider adding more terms to this exclusion list...
category_names = ['process', 'property', 'phenomenon', 'role', 'attribute', 'matter',
                     'body', 'domain', 'operator', 'variable', 'part', 'trajectory', 'form',
                 'condition', 'state']

variable_links = {'first_order':['hasComponentNounConcept', 'hasAttribute', 'isTypeOf',
                                 'components','hasSynonym'], 
                  'second_order':['isDefinedBy', 'isWWNDefinedBy'],
                  'third_order':['isRelatedTo', 'isClsRel']} 
svo_index_map = {}

#########################################################
#                                                       #
# Entry function, this calls all procedures to generate #
# graph for an input.                                   #
#                                                       #
#########################################################

# initialize a graph with the desired variables
# Takes as input:
#     var    == a desired variable description, preferably short
#               DEFAULT = '' (empty string)            
#     levels == the number of levels to which to expand graph
#               DEFAULT = 2
#
# assumption (for now) - a word has only one key, one sense, so it is
#                        only added to the graph once
def create_graph(var = '', levels = 1, graph = None, write_graph = False):
    
    # initialize graph
    if graph is None:
        graph = {}
    else:
        graph = load_graph(graph)
    graph = create_graph_levels(graph, var, levels)
    if write_graph:
        write_graph(graph)
    return graph

def load_graph(filename):
    try:
        with open(filename) as f:
            graph = json.load(f)
    except:
        print('Warning: could not load graph {} ...'.format(filename))
        graph = {}
    return graph

def write_graph(graph, filename=''):
    if filename == '':
        filename = "output/concept_graph.json"
    try:
        graph_str = json.dumps(graph, indent = 4, sort_keys=True)
        with open(filename,"w") as f:
            f.write(graph_str)
    except:
        print('Warning: could not write graph {} ...'.format(filename))
        
def create_graph_levels(graph, variable, levels):
    # parse the input to get noun groups and
    # their components
    if levels > 0:
        #print(variable)
        input_noun_groups = pt.parse_noun_groups(variable)
        #print(input_noun_groups)
        # loop through each sentence (should only be one) in input
        for sentence, word_attr in input_noun_groups.items():
            # loop through each noun group in sentence
            for word, attr in word_attr.items():
                # add word to the dictionary (annotate inside)
                #print('Working on ... {}'.format(word))
                [graph, new_nodes, added] = add_term_node(graph, word, attr)
                if not added and word in graph.keys():
                    new_nodes = graph[word]['add_components']

                # if the node also has components, add those to the graph as well
                if 'components' in attr.keys():
                    graph[word.lower()]['components'] = list(attr['components'].keys())
                    for comp_word in attr['components'].keys():
                        #print('Working on ... {}'.format(comp_word))
                        attr['components'][comp_word]['component_of'] = word.lower()
                        [graph, new_nodes, added] = add_term_node(graph, comp_word, attr['components'][comp_word], new_nodes)
                        if not added and comp_word.lower() in graph.keys():
                            new_nodes = new_nodes + graph[comp_word.lower()]['add_components']
                #print('Completed {}, now working on components added'.format(word))
                #print(new_nodes)
                for n in new_nodes:
                    graph = create_graph_levels(graph, n, levels-1)
    return graph

# add a node to the graph by name
#     - annotate it with SVO class, variables, and WWN category
#     - break up into 'components' at ADPOSITION barriers (from attr)
#     - break up the name and components into attributes, noun groups and
#       individual nouns
#     - this is a recursive function so that it repeats until it gets to the "end"
#       where a node can no longer be broken down
def add_term_node(graph, name, attr, added=None):    

    # list of current graph entries
    existing_nodes = list(graph.keys())
    # lemma version of current node
    lemma = ' '.join(attr['lemma_seq'])
    
    if added is None:
        added = []
    was_added = False
    # add current name to the graph if it's not already there and
    # if it's not one of the core categories
    if not name.lower() in existing_nodes and \
        not name.lower() in category_names and\
        not lemma.lower() in category_names:

        was_added = True
        #print('Adding term to graph:', name.lower())
        # add node to the graph
        graph[name.lower()] = { 'pos_seq': attr['pos_seq'],
                                'lemma_seq': attr['lemma_seq']}
                
        # if X in Y['components'], then Y in X['component_of']
        if 'component_of' in attr.keys():
            if not 'component_of' in graph[name.lower()].keys():
                graph[name.lower()]['component_of'] = [attr['component_of'].lower()]
            elif not attr['component_of'].lower() in graph[name.lower()]['component_of']:
                graph[name.lower()]['component_of'].append(attr['component_of'].lower())

        #print('at node type attr')
        # splitting up into type + attribute, noun components
        [graph, added] = add_node_type_attr(graph, name.lower(), added)

        #print('at wwn info')
        # looking up its definition and category in WiktiWordNet
        graph = add_wwn_info(graph, name.lower())

        #print('at svo info')
        # looking up its class and related variables in SVO
        graph = add_svo_info(graph, name.lower())
        
        #print('at expand node')
        [graph, new_nodes] = expand_node(graph, name.lower())
        added = added + new_nodes
        
        graph[name.lower()]['add_components'] = added
    
    #print('Finished add term node. Added is: ', added)
    return [graph, added, was_added]

# decompose word node into attributes and a root type
def add_node_type_attr(graph, word, added=None):
    
    #print('Entering add node type attr with: ', word)
    # get attributes of current word from graph
    pos_seq = graph[word]['pos_seq']
    lemma_seq = graph[word]['lemma_seq']
    
    if added is None:
        added = []
    # separate out the node_type from attributes and its lemma sequence
    [node_type, lemma, typ] = pt.extract_type(word, pos_seq, lemma_seq)

    # if the node was broken down, then add its components
    if (typ == 'modnoun') and (node_type != word):
        # generate attributes for the noun part and add to graph
        attr = {'pos_seq':['NOUN']*len(node_type.split()), 'lemma_seq': lemma.split()}
        [graph, added, was_added] = add_term_node(graph, node_type, attr, added)
        
        if not 'isTypeOf' in graph[word].keys():
            graph[word]['isTypeOf'] = [node_type]
        elif not node_type in graph[word]['isTypeOf']:
            graph[word]['isTypeOf'].append(node_type)
        
        if was_added:
            #print('Found the new type ', node_type, 'for word ', word)
            if not 'hasType' in graph[node_type].keys():
                graph[node_type]['hasType'] = [word]
            elif not word in graph[node_type]['hasType']:
                graph[node_type]['hasType'].append(word)
                #[graph, _] = expand_node(graph, node_type)
        
        # add the attributes individually
        attrs = word.split(' '+node_type)[0]
        lemma_num = 0
        for attr in attrs.split():
            
            attr2 = {'pos_seq':['ADJECTIVE'], 'lemma_seq': [lemma_seq[lemma_num]]}
            [graph, added, was_added] = add_term_node(graph, attr, attr2, added)
        
            if not 'hasAttribute' in graph[word].keys():
                graph[word]['hasAttribute'] = [attr]
            elif not attr in graph[word]['hasAttribute']:
                graph[word]['hasAttribute'].append(attr)
                

            if was_added:
                #print('Found the new attribute ', attr, 'for word ', word)
                if not 'isAttributeOf' in graph[attr].keys():
                    graph[attr]['isAttributeOf'] = [word]
                elif not word in graph[attr]['isAttributeOf']:
                    graph[attr]['isAttributeOf'].append(word)
                
            lemma_num += 1
    elif typ in ['noungrp','modnoun','modnoungrp']:
    # for noun part, also break it down into its noun components
        [graph, added] = add_noun_components(graph, word, pos_seq, lemma_seq, added)
    #print('Finished add node type attr with added: ', added)
    return [graph, added]

# for a noun grouping, break up into individual nouns
def add_noun_components(graph, name, pos_seq, lemma_seq, added = None):
    if added is None:
        added = []
    
    if ' ' in name:
        i = 0
        for comp_name in name.split():
            if pos_seq[i] == 'NOUN':
                attr = {'pos_seq':[pos_seq[i]], 'lemma_seq':[lemma_seq[i]]}
                [graph, added, was_added] = add_term_node(graph, comp_name, attr, added)
                if not 'hasComponentNounConcept' in graph[name].keys():
                    graph[name]['hasComponentNounConcept'] = [comp_name]
                elif not comp_name in graph[name]['hasComponentNounConcept']:
                    graph[name]['hasComponentNounConcept'].append(comp_name)


                if was_added:
                    if not 'isComponentOf' in graph[comp_name].keys():
                        graph[comp_name]['isComponentOf'] = [name]                    
                    elif not name in graph[comp_name]['isComponentOf']:
                        graph[comp_name]['isComponentOf'].append(name)
            i += 1
    return [graph, added]

# pull categories and definition from WiktiWordNet
def add_wwn_info(graph, name):
    #print('Entering add wwn info with word: ',name)
    lemma = ' '.join(graph[name]['lemma_seq'])
    categories = wwnapi.get_category(name.lower())
    if (categories == {}) and (lemma != ''):
        categories = wwnapi.get_category(lemma.lower())
    
    for category in categories.keys():
        if not 'hasWWNCategory' in graph[name].keys():
            graph[name]['hasWWNCategory'] = [category]
        elif not category in graph[name]['hasWWNCategory']:
            graph[name]['hasWWNCategory'].append(category)
        
        definition = categories[category]
        if not 'hasWWNDefinition' in graph[name].keys():
            graph[name]['hasWWNDefinition'] = [definition]
        elif not definition in graph[name]['hasWWNDefinition']:
            graph[name]['hasWWNDefinition'].append(definition)
    #print('Finishing add wwn info with added: ',added)    
    return graph

def add_svo_index_map(svo):
    svo_namespace = svo['entity'].split('/')[-1].split('#')[0]
    svo_entity = svo['entity'].split('#')[-1]
    svo_hash = hash(svo_namespace + svo_entity)    
    svo_label = svo['entitypreflabel']
    svo_class = svo['entityclass']
    if not svo_hash in svo_index_map.keys():
        svo_index_map[svo_hash] = {'namespace': svo_namespace, 'entity':svo_entity, 
                                   'preflabel': svo_label, 'class':svo_class}
    elif svo_index_map[svo_hash]['entity'] != svo_entity:
            print('Ooops! Overlapping hash: {}, {}'.format(svo_entity, svo_index_map[svo_hash]))

def print_svo_index_map():
    with open('svo_index_map.txt','w') as f:
        for hashi, val in svo_index_map.items():
            f.write('hash,{}\n'.format(hashi))
            for svotag, val2 in val.items():
                f.write('{},{}\n'.format(svotag, val2))

def get_svo_index_map():
    return svo_index_map

# pull classes and variables from SVO
def add_svo_info(graph, name):
    
    if (len(name.split()) == 1):
        #print('Search for SVO class and variables...')
        lemma = ' '.join(graph[name.lower()]['lemma_seq'])
        results = svoapi.rank_search([name.lower(), lemma.lower()])
    
        exact_match = results.loc[results['rank']==1]
        variable_match = results.loc[(results['entityclass']=='Variable') & (results['rank']!=1)]
        other_match = results.loc[(results['entityclass']!='Variable') & (results['rank']!=1)]

        entity_match = np.unique(exact_match['entity'].tolist())
        for entity in entity_match:
            exact_match_entity = exact_match[exact_match['entity']==entity]
            exact_match_label = list(np.unique(exact_match_entity['entitylabel'].tolist()))
            if len(exact_match_label) < len(exact_match_entity):
                print('Exact match label found twice: {}', entity)
            add_svo_index_map(exact_match_entity.iloc[0])
            
            svo_namespace = entity.split('/')[-1].split('#')[0]
            svo_entity = entity.split('#')[-1]
            svo_hash = hash(svo_namespace+svo_entity)
            svo_class = exact_match_entity['entityclass'].iloc[0]
            if not 'hasSVOMatch' in graph[name.lower()].keys():
                graph[name.lower()]['hasSVOMatch'] = {svo_class: [svo_hash]}
            elif not svo_class in graph[name.lower()]['hasSVOMatch']:
                graph[name.lower()]['hasSVOMatch'][svo_class] = [svo_hash]
            elif not svo_hash in graph[name.lower()]['hasSVOMatch'][svo_class]:
                graph[name.lower()]['hasSVOMatch'][svo_class].append(svo_hash)
                
        entity_match = np.unique(variable_match['entity'].tolist())
        for entity in entity_match:
            var_match_entity = variable_match[variable_match['entity']==entity]
            var_match_label = list(np.unique(var_match_entity['entitylabel'].tolist()))
            add_svo_index_map(var_match_entity.iloc[0])
            
            svo_namespace = entity.split('/')[-1].split('#')[0]
            svo_entity = entity.split('#')[-1]
            svo_hash = hash(svo_namespace+svo_entity)
            rank = min(sum(var_match_entity['rank'].tolist()),.9)
            if not 'hasSVOVar' in graph[name.lower()].keys():
                graph[name.lower()]['hasSVOVar'] = {svo_hash: rank}
            elif not svo_hash in graph[name.lower()]['hasSVOVar'].keys():
                graph[name.lower()]['hasSVOVar'][svo_hash] = rank
                
        entity_match = np.unique(other_match['entity'].tolist())
        for entity in entity_match:
            other_match_entity = other_match[other_match['entity']==entity]
            other_match_label = list(np.unique(other_match_entity['entitylabel'].tolist()))
            add_svo_index_map(other_match_entity.iloc[0])
            
            svo_namespace = entity.split('/')[-1].split('#')[0]
            svo_entity = entity.split('#')[-1]
            svo_hash = hash(svo_namespace+svo_entity)
            rank = min(sum(other_match_entity['rank'].tolist()),.9)
            if not 'hasSVOEntity' in graph[name.lower()].keys():
                graph[name.lower()]['hasSVOEntity'] = {svo_hash: rank}
            elif not svo_hash in graph[name.lower()]['hasSVOEntity'].keys():
                graph[name.lower()]['hasSVOEntity'][svo_hash] = rank
        
    return graph

# expand an individual node by grabbing its definitions
def expand_node(graph, word):
    
    #print('Entering expand node with: ', word)
    if not word in category_names:
        # a given node can be expanded by: looking up its related terms in Wikipedia
        [graph, added_nodes] = add_wikipedia_def(graph, word, long=True)

        # or parsing its WWN defintion
        [graph, added_nodes] = add_wwn_def(graph, word, added_nodes)

        # or ...
    
        #print('Finishing expand node for ', word, ' and added: ', added_nodes)    
    return [graph, added_nodes]

def add_wikipedia_def(graph, name, added = None, long = False):
    #print('Entering add wikip def with word: ',name)
    
    # initialize added if not passed
    if added is None:
        added = []
        
    # grab Wikipedia page information
    #print('Entering Wikipedia search')
    [text, disambig, title, redirecttitle] = wapi.get_wikipedia_text(name)
    lemma = ' '.join(graph[name.lower()]['lemma_seq'])
    #print('Wikipedia search finished')
    
    # only parse definition if not a disambiguation page
    if not disambig:
        
        # set name to use to the name passed
        use_name = name.lower()
        syn = '('+name.lower()+')' in title.lower().replace('\s+','') or\
              '('+lemma.lower()+')' in title.lower().replace('\s+','') or\
              '('+name.lower()+')' in redirecttitle.lower().replace('\s+','') or\
              '('+lemma.lower()+')' in redirecttitle.lower().replace('\s+','')
        #if syn:
        #    print('syn is True: {}, {}', use_name, title.lower())
        # if either the lemma or name are equal to the redirect title or title, reset use_name to title
        if (name.lower() == redirecttitle.lower()) or (lemma.lower() == title.lower()) or \
            (lemma.lower() == redirecttitle.lower()) or syn:
            use_name = title.lower()
        
        # if Wikipedia page found is not a good match (e.g., not a synonym/redirect), then add it
        # to the attributes as related, but do not create a new node for it (this is a stub)
        graph = add_related(graph, use_name, title, name.lower())
        #print('Parsing Wikipedia page ...')
        # find is paragraph based on use_name; default to title if not found and title is different
        [pno, nsubj, name_found] = pt.find_is_paragraph(text, title, use_name)
        #print('Finished parsing Wikipedia page. The name found was: ', name_found, 'and the paragraph was par no')
        #print(pno,' starting with ...', text[pno][0])
        # if name_found is use_name
        if (pno != -1) and (name_found.lower() == use_name.lower()):
            #if name_found.lower() != name.lower():
            #    def_noun_groups = pt.parse_noun_groups(name_found.lower())
            #    if name_found.lower() in def_noun_groups[1].keys():
            #        attr = def_noun_groups[1][name_found.lower()]
            #        [graph, added] = add_term_node(graph, name_found.lower(), attr, added)
            #    else:
            #        name_found = name.lower()
            # parse the first paragraph or all of the text based on "long" setting
            if not long:
                def_noun_groups = pt.parse_noun_groups(text[pno])
            else:
                #print('Parsing whole wikipedia page ... name: {}, name found: {}'\
                #      .format(name.lower(), name_found.lower()))
                parsed_page = pt.parse_page_noun_groups(text)
                def_noun_groups = parsed_page[pno+1]
            #print(def_noun_groups)
        
            [graph, added] = add_definition(graph, name.lower(), name_found, def_noun_groups, added)
            
            if long:
                noun_groups_index = pt.count_noun_groups(parsed_page, name_found.lower())
                graph = add_dimensions(graph, name.lower(), name_found.lower(), noun_groups_index)
                #print('Printed modifed names: {} to {}'\
                #      .format(name_found.lower(), name.lower()))
    #print('Finishing add wikip def with added: ',added)        
    return [graph, added]

# add related/synonym Wikipedia concepts
def add_related(graph, name, title, name_orig):
    
    # name is related to, but not a synonym for the page
    # no new node added
    if (name.lower() != title.lower()):
        src = name.lower()
        dest = title.lower()
        if not 'isRelatedTo' in graph[src].keys():
            graph[src]['isRelatedTo'] = [dest]
        elif not dest in graph[src]['isRelatedTo']:
            graph[src]['isRelatedTo'].append(dest)
    # name is a synonym, do not add a new node
    if (name.lower() != name_orig.lower()):
        src = name_orig.lower()
        dest = name.lower()
        if not 'hasSynonym' in graph[src].keys():
            graph[src]['hasSynonym'] = [dest]
        elif not dest in graph[src]['hasSynonym']:
            graph[src]['hasSynonym'].append(dest)
    return graph

# Add Wikipedia definition components
def add_definition(graph, name, name_found, nodes_par, added):           
    
    # added contains the names of nodes that were added during this pass
    if added is None:
        added = []
    
    edge_label = 'isDefinedBy'
    
    max_i = min(len(nodes_par.keys()), 3)
    for i in range(1,max_i):
        nodes = nodes_par[i]
        if i == 1:
            edge_label = 'isDefinedBy'
        else:
            edge_label = 'isClsRel'
        for (node_name, attr) in nodes.items():
            if node_name.lower() != name_found.lower():
                #[graph, was_added] = add_term_node(graph, node_name, attr)
                if (i == 1):
                    added.append(node_name)
                if not edge_label in graph[name.lower()].keys():
                    graph[name.lower()][edge_label] = [node_name.lower()]
                elif not node_name.lower() in graph[name.lower()][edge_label]:
                    graph[name.lower()][edge_label].append(node_name.lower())
    return [graph, added]

def add_dimensions(graph, name, name_found, noun_groups_index):
    modified = noun_groups_index.loc[noun_groups_index['modified'],'noun_group'].tolist()
    aspects = noun_groups_index.loc[noun_groups_index['aspects'],'noun_group'].tolist()
    graph[name]['modified_terms'] = [x for x in modified if x != name_found]
    graph[name]['term_aspects'] = [x for x in aspects if x != name_found]
    return graph

# parse WiktiWordNet definition
def add_wwn_def(graph, name, added = None):
    #print('Entering add wwn info with word: ',name)
    if added is None:
        added = []
        
    if 'hasWWNDefinition' in graph[name.lower()].keys():
        for definition in graph[name.lower()]['hasWWNDefinition']:
            def_noun_groups = pt.parse_noun_groups(definition)
            for ng in def_noun_groups[1].keys():
                attr = def_noun_groups[1][ng]
                #[graph, was_added] = add_term_node(graph, ng, attr)
                #if was_added:
                added.append(ng)
                if ng.lower() != name.lower():
                    if not 'isWWNDefinedBy' in graph[name.lower()].keys():
                        graph[name.lower()]['isWWNDefinedBy'] = [ng.lower()]
                    elif not ng.lower() in graph[name.lower()]['isWWNDefinedBy']:
                        graph[name.lower()]['isWWNDefinedBy'].append(ng.lower())
    #print('Finishing add wwn info with added: ',added)    
    return [graph, added]

def graph_inference(graph):
    graph = graph_define_category(graph)
    graph = graph_add_var_entity_links(graph)
    return graph

def graph_define_category(graph):
    # categorize terms as
    #     - 'sn': single noun x
    #     - 'a':  adjective x
    #     - 'ng': noun group
    #     - 'an': noun or noun group with adjective modifier
    #     - 'adpof': grouping linked with 'of' adposition
    #     - 'adp': grouping NOT linked with 'of' adposition
    
    for term in graph.keys():
        if graph[term]['pos_seq'] == ['ADJECTIVE']:
            graph[term]['termtype'] = 'a'
            graph[term]['detSVOCategory'] = 'Attribute'
        elif graph[term]['pos_seq'] == ['NOUN']:
            graph[term]['termtype'] = 'sn'
            if 'hasSVOMatch' in graph[term].keys() or \
                'hasWWNCategory' in graph[term].keys():
                if 'hasSVOMatch' in graph[term].keys():
                    classes = list(graph[term]['hasSVOMatch'].keys())
                else:
                    classes = graph[term]['hasWWNCategory']
                graph[term]['detSVOCategory'] = 'Phenomenon'
                if 'Phenomenon' in classes or 'Matter' in classes or \
                    'Role' in classes:
                    graph[term]['detSVOCategory'] = 'Phenomenon'
                elif 'Property' in classes:
                    graph[term]['detSVOCategory'] = 'Property'
                elif 'Attribute' in classes:
                    graph[term]['detSVOCategory'] = 'Attribute'
                elif 'Process' in classes:
                    graph[term]['detSVOCategory'] = 'Process'
                else:
                    graph[term]['detSVOCategory'] = classes[0]
            else:
                # default when we don't know ...
                graph[term]['detSVOCategory'] = 'Phenomenon'
        elif 'hasComponentNounConcept' in graph[term].keys():
            graph[term]['termtype'] = 'ng'
        elif 'isTypeOf' in graph[term].keys():
            graph[term]['termtype'] = 'an'
        elif 'components' in graph[term].keys() and ' of ' in term:
            graph[term]['termtype'] = 'adpof'
        else:
            graph[term]['termtype'] = 'adp'
            graph[term]['detSVOCategory'] = 'Phenomenon'
            
    # single nouns and adjectives have been categorized
    # now categorize compound nouns:
    for term in graph.keys():
        if graph[term]['termtype'] == 'ng':
            graph[term]['detSVOCategory'] = 'Phenomenon'
            # gather all of the types and count:
            categories = {}
            for component in graph[term]['hasComponentNounConcept']:
                try:
                    cat = graph[component]['detSVOCategory']
                    if not cat in categories.keys():
                        categories[cat] = 1
                    else:
                        categories[cat] += 1                        
                except:
                    #print('error 1')
                    pass
            category = []
            count = 0
            for cat in categories.keys():
                if categories[cat] > count:
                    category = [cat]
                    count = categories[cat]
                elif categories[cat] == count:
                    category.append(cat)
            if 'Phenomenon' in category and 'Property' in category:
                graph[term]['detSVOCategory'] = 'Variable'
            elif 'Phenomenon' in category or (category == []):
                graph[term]['detSVOCategory'] = 'Phenomenon'
            elif 'Property' in category:
                graph[term]['detSVOCategory'] = 'Property'
            elif 'Attribute' in category:
                graph[term]['detSVOCategory'] = 'Attribute'
            elif 'Process' in category:
                graph[term]['detSVOCategory'] = 'Process'
            else:
                graph[term]['detSVOCategory'] = category[0]

    # now categorize modified compound or singular nouns:
    for term in graph.keys():
        if graph[term]['termtype'] == 'an':
            graph[term]['detSVOCategory'] = 'Phenomenon'
            try:
                typ = graph[term]['isTypeOf'][0]
                category = graph[typ]['detSVOCategory']
                if 'Attribute' in category:
                    graph[term]['detSVOCategory'] = 'Attribute'
                else:
                    graph[term]['detSVOCategory'] = 'Specialized' + category
            except:
                #print('error 2')
                #print(term, graph[term])
                pass
            
    # now categorize compound terms combined with adposition 'of':
    for term in graph.keys():
        if graph[term]['termtype'] == 'adpof':
            graph[term]['detSVOCategory'] = 'Phenomenon'
            
            categories = {}
            try:
                components = graph[term]['components']
                for comp in components:
                    try:
                        cat = graph[comp]['detSVOCategory']
                        if not cat in categories.keys():
                            categories[cat] = 1
                        else:
                            categories[cat] += 1
                    except:
                        #print('error 3')
                        pass
            except:
                #print('error 4')
                pass
            
            if ('Phenomenon' in categories.keys() or 'SpecializedPhenomenon' in categories.keys()) \
                and ('Property' in categories.keys() or 'SpecializedProperty' in categories.keys()):
                graph[term]['detSVOCategory'] = 'Variable'
            elif 'SpecializedPhenomenon' in categories.keys():
                graph[term]['detSVOCategory'] = 'SpecializedPhenomenon'
            elif 'Phenomenon' in categories.keys():
                graph[term]['detSVOCategory'] = 'Phenomenon'
            elif 'SpecializedProperty' in categories.keys():
                graph[term]['detSVOCategory'] = 'SpecializedProperty'
            elif 'Property' in categories.keys():
                graph[term]['detSVOCategory'] = 'Property'
            elif 'SpecializedAttribute' in categories.keys():
                graph[term]['detSVOCategory'] = 'SpecializedAttribute'
            elif 'Attribute' in categories.keys():
                graph[term]['detSVOCategory'] = 'Attribute'
            elif 'SpecializedProcess' in categories.keys():
                graph[term]['detSVOCategory'] = 'SpecializedProcess'
            elif 'Process' in categories.keys():
                graph[term]['detSVOCategory'] = 'Process'
    
    return graph
            
def graph_add_var_entity_links(graph):
    
    terms = list(graph.keys())
    for link in variable_links['first_order']:
        for word in terms:
            if link in graph[word].keys():
                linked_terms = graph[word][link]
                for lterm in linked_terms:
                    for typ_link in ['hasSVOVar', 'hasSVOEntity']:
                        try:
                            svovar = graph[lterm][typ_link]
                            if not typ_link in graph[word].keys():
                                graph[word][typ_link] = {}
                            for key, val in svovar.items():
                                if not key in graph[word][typ_link].keys():
                                    graph[word][typ_link][key] = val
                            #print('no error')
                            #print(','.join([link,word,lterm,typ_link]))
                        except:
                            #print('first order error')
                            #print(','.join([link,word,lterm,typ_link]))
                            pass
                                
    for link in variable_links['second_order']:
        for word in terms:
            if link in graph[word].keys():
                linked_terms = graph[word][link]
                for lterm in linked_terms:
                    for typ_link in ['hasSVOVar', 'hasSVOEntity']:
                        try:
                            #print('no error')
                            #print(link,word,lterm,typ_link)
                            svovar = graph[lterm][typ_link]
                            if not typ_link in graph[word].keys():
                                graph[word][typ_link] = {}
                            for key, val in svovar.items():
                                if not key in graph[word][typ_link].keys():
                                    graph[word][typ_link][key] = val*0.7
                                else:
                                    graph[word][typ_link][key] = \
                                        min(.9, graph[word][typ_link][key] + val)
                        except:
                            #print('second order error')
                            #print(link,word,lterm,typ_link)
                            pass
    
    return graph

        


