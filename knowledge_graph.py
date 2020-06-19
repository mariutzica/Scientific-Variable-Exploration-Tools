"""Module contianing the SciVarKG class that holds information about Scientific
Variables, their components, and other annotations.

This module contains tools for constructing a knowledge graph of scientific
variable terminology, including components of scientific variables. It also
contains grounding information for to SVO variables as well as the WM indicators
for all entities.

  Typical usage example:

  graph = kg.SciVarKG(graphfile = 'resources/world_modelers_indicators_kg.json')
  graph.add_concept('thermal conductivity', depth = 2)
  graph.write_graph()

  For more examples on usage, see Module Usage and Testing notebook, section 5.
"""

import wiktiwordnetapi as wwnapi
import parse_tools as pt
import pandas as pd
import svoapi
import wikipediaapi as wapi
import numpy as np
import json
from os import path

class SciVarKG:
    """Hold Scientific Variables technical terminology knowledge graph.

    A class to hold information technical terminology related to scientific
    variables. It holds definition information for a term, as well as its likely
    high/top level categorization, as well as matched rank alignments to
    existing SVO entities and WM indicators. The information stored in this
    knowledge graph can be used for semantic search and to help generate new
    variables.

    Class Attributes:
        category_names: A list of the 'reserved words' for high level
                        categories. These terms should not be further broken
                        down as they are considered 'terminal' nodes.
        variable_links: A dict containing the first, second and third order link
                        names.
                        A first order link is one that is a direct linguistic
                        component of the technical term.
                        A second order links is one that points to a technical
                        term that is used to define the root technical term.
                        A third order link is one that points to a technical
                        term that is considered closely related to the root
                        technical term.
        wwn:            A WiktiWordNet object. Used to look up technical terms
                        in WiktiWordNet.

    Instance Attributes:
        index_map     : A dict "synonyms" bank for graph. It is the mapping from
                        any term to its key in the knowledge graph.
        svo_index_map : A dict containing the hash values indices determined
                        with the hash() function and the corresponding SVO
                        entity information including namespace, URI, and label.
        graph         : A dict that contains the scientific variable terminology
                        knowledge graph.
                        There is one key for each technical term.
                        For each key, there is an associated dictionary of
                        property value pairs.
                        The general format is:
                            { 'technical term' : { 'property' : value } }
                        The available properties are:
                            - 'components': a list containing the technical
                            terms that make up this term
                            - 'hasAttribute'   : list of attributes associated
                                                 with this technical term
                            - 'isAttributeOf'  : list of technical terms
                                                 modified by this attribute
                            - 'isTypeOf'       : list of more general technical
                                                 terms, derived by stripping
                                                 leading adjectives
                            - 'isRelatedTo'    : list of titles of related (but
                                                 not matched) Wikipedia page
                            - 'pos_seq'        : list of the part of speech
                                                 sequence of the words making up
                                                 the technical term;
                                                 valid values are 'NOUN',
                                                 'ADJECTIVE', 'ADPOSITION'
                            - 'lemma_seq'      : list of root (lemma) words of
                                                 the sequence of words making up
                                                 the technical term
                            - 'hasSVOEntity'   : dict of svohash : match rank
                                                 pairs of non-variable,
                                                 non-match SVO entities aligned
                                                 with this technical term; match
                                                 rank ranges from 0 to 1
                                                 svohash is indexed by
                                                 svo_index_map
                            - 'hasSVOMatch'    : dict of svohash : match rank
                                                 pairs of exact match SVO
                                                 entities aligned with this
                                                 technical term; match rank
                                                 ranges from 0 to 1
                                                 svohash is indexed by
                                                 svo_index_map
                            - 'hasSVOVar'      : dict of svohash : match rank
                                                 pairs of non-match SVO
                                                 variables aligned with this
                                                 technical term; match rank
                                                 ranges from 0 to 1
                                                 svohash is indexed by
                                                 svo_index_map
                            - 'hasWMIndicator' : dict of WM indicator name :
                                                 match rank pairs of WM
                                                 indicators aligned with this
                                                 term; match rank ranges from 0
                                                 to 1
                            - 'modified_terms' : list of strings found in
                                                 Wikipedia article that modify
                                                 the technical term with leading
                                                 adjectives or nouns
                            - 'term_aspects'   : list of strings found in the
                                                 Wikipedia article that modify
                                                 the technical term with
                                                 trailing nouns or with noun
                                                 groups linked together
                                                 with adpositions
                            - 'detSVOCategory' : string, determined top level
                                                 SVO category
                            - 'hasWWNCategory' : high level category determined
                                                 from WiktiWordNet
                            - 'isDefinedBy'    : list of technical terms that
                                                 are used in the Wikipedia
                                                 definition of the term
                            - 'isWWNDefinedBy' : list of technical terms that
                                                 are used in the Wiktionary
                                                 definition of the term

    """

    category_names = [ 'process', 'property', 'phenomenon', 'role', 'attribute',
                       'matter', 'body', 'domain', 'operator', 'variable',
                       'part', 'trajectory', 'form', 'condition', 'state',
                       'abstraction', 'equation', 'expression']
    variable_links = { 'first_order'  : [ 'hasComponents', 'hasAttribute',
                                          'isTypeOf'],
                       'second_order' : ['isDefinedBy', 'isWWNDefinedBy'],
                       'third_order'  : ['isRelatedTo', 'isCloselyRelatedTo'] }

    wwn            = wwnapi.wiktiwordnet()

    def __init__(self, graphfile = None, \
                svoindexfile = None, indexmapfile = None):
        """
        Intialize SciVarKG by loading from file, if provided.

        Args:
            graphfile:    A string with the path + name of json file containing
                          the knowledge graph.
            svoindexfile: A string with the path + name of text file containing
                          the svo index mapping.
        """

        if graphfile is None:
            self.graph = {}
        else:
            self.load_graph(graphfile)

        self.load_index_map(indexmapfile)
        self.load_svo_index_map(svoindexfile)

    def load_graph(self, filename):
        """
        Load knowledge graph from file.

        Currently whatever information is already present in graph is replaced
        with the information loaded from file.

        Args:
            filename:     A string with the path + name of json file containing
                          the knowledge graph.
        """

        try:
            with open(filename) as f:
                self.graph = json.load(f)
        except:
            print('Warning: could not load graph {} ...'.format(filename))
            self.graph = {}

    def write_graph(self, filename = 'resources/scivar_kg.json'):
        """
        Write knowledge graph to file.

        Args:
            filename:   A string with the name of the file to write to; if
                        not provided, it defaults to writing to resources/
                        scivar_kg.json.
        """

        graph_str = json.dumps(self.graph, indent = 4, sort_keys=True)

        try:
            with open(filename,"w") as f:
                f.write(graph_str)
        except:
            print('Warning: could not write graph {} ...'.format(filename))
            print('Call write_graph with no arguments to write to the default')
            print('file: resources/scivar_kg.json')


    def load_svo_index_map(self, svomapfilename = None):
        """
        Load the SVO index map from file.

        To save space in the knowledge graph, SVO information is provided as
        a hashed value. The annotation information for each hashed value,
        including the SVO entity URI information and entity label, are
        stored in svo_index_map.

        Args:
            svomapfilename: A string with the name of the file containing the
                            SVO index map.
        """

        self.svo_index_map = {}
        hash_map = {}
        if not svomapfilename is None:
            if path.exists(svomapfilename):
                with open(svomapfilename, 'r') as f:
                    hashval = None
                    for line in f:
                        category = line.split(',')[0]
                        val = line.split(',')[1].strip('\n\r')
                        if category == 'hash':
                            if not hashval is None:
                                newhash = hash( element['namespace'] + \
                                               '#' + element['entity'] )
                                self.svo_index_map[newhash] = element
                                hash_map[hashval] = newhash
                            element = {}
                            hashval = val
                        else:
                            element[category] = val
                    if not hashval is None:
                        newhash = hash( element['namespace'] + \
                                        '#' + element['entity'] )
                        self.svo_index_map[newhash] = element
                        hash_map[hashval] = newhash
                    self.update_svo_hash(hash_map)
            else:
                print('ERROR: Could not read SVO index map from {}.'\
                      .format(filename))

    def update_svo_hash(self, hash_map):
        """
        Reset SVO hash values with new kernel. Discard unmapped SVO hashes.

        Args:
            hash_map: A dictionary mapping old hash values to new hash values.
        """
        
        terms = self.graph.keys()
        i = 1
        entity = False
        var = False
        match = False
        for term in terms:
            keys = self.graph[term].keys()
            for rel in ['hasSVOVar', 'hasSVOEntity']:
                if rel in keys:
                    svovar = self.graph[term][rel]
                    reindex = {}
                    j = 1
                    for svo_i, svo_rank in svovar.items():
                        try:
                            reindex[hash_map[svo_i]] = svo_rank
                        except:
                            #print('Could not map SVO hash: {}.'.format(svo_i))
                            pass
                    self.graph[term][rel] = reindex
            if 'hasSVOMatch' in keys:
                svomatch = self.graph[term]['hasSVOMatch']
                reindex = {}
                for svo_cat, lst in svomatch.items():
                    reindex[svo_cat] = [ hash_map[str(x)] for x in lst ]
                self.graph[term]['hasSVOMatch'] = reindex
                    
            
    def add_svo_index_map(self, svo):
        """
        Add SVO hash to svo_index_map.

        Args:
            svo : The SVO entity to add to the index map.
        """

        svo_namespace = svo['entity'].split('/')[-1].split('#')[0]
        svo_entity    = svo['entity'].split('#')[-1]
        svo_hash      = hash(svo_namespace + svo_entity)
        svo_label     = svo['entitypreflabel']
        svo_class     = svo['entityclass']
        if not svo_hash in self.svo_index_map.keys():
            self.svo_index_map[svo_hash] = { 'namespace' : svo_namespace,
                                             'entity'    : svo_entity,
                                             'preflabel' : svo_label,
                                             'class'     : svo_class }
        elif self.svo_index_map[svo_hash]['entity'] != svo_entity:
            print( 'Ooops! Overlapping hash: {}, {}'\
                   .format(svo_entity, self.svo_index_map[svo_hash]) )

    def write_svo_index_map(self, svomapfilename = \
                                                'resources/scivar_svo_index_map.txt'):
        """
        Write the SVO index map to file.

        To save space in the knowledge graph, SVO information is provided as
        a hashed value. The annotation information for each hashed value,
        including the SVO entity URI information and entity label, are
        stored in svo_index_map. This can be saved to file and reloaded for
        future use.

        Args:
            svomapfilename: A string with the name of the file containing the
                            SVO index map.
        """


        try:
            with open(svomapfilename, 'w') as f:
                for hashval, attr in self.svo_index_map.items():
                    f.write('hash,{}\n'.format(hashval))
                    for key, val in attr.items():
                        f.write('{},{}\n'.format(key,val))
        except:
            print('ERROR: Could not write SVO index map to {}.'\
                      .format(svomapfilename))
            print('Call write_svo_index_map with no arguments to write to the')
            print('default file: resources/scivar_svo_index_map.txt')

    def load_index_map(self, indexmapfile = None):
        """
        Initialize index map with all synonyms.

        The index_map serves as the lookup table for synonyms.
        """

        self.index_map = {}

        if indexmapfile is None:
            for key in self.graph.keys():
                self.index_map[key] = key
        else:
            with open(indexmapfile) as f:
                self.index_map = json.load(f)

        self.update_synonyms()

    def update_synonyms(self):
        """
        Update index map to ensure it agrees with graph information.

        The index_map serves as the lookup table for synonyms.

        Algorithm:
            First create the index map. Each key points to itself.
            If the key has any synonyms, these point to that key.
            At the moment, the synonym only points to one key (the first
            one that is encountered when searching the graph).
            If the synonym nodes are present, they are first merged
            with the existing graph and then they are removed. Merged
            information is limited to that pointed to by links in
            transfer_links_dict and transfer_links_list.
        """

        transfer_links_dict = [ 'hasSVOVar', 'hasSVOEntity', 'hasSVOMatch',
                                'hasWMIndicator']
        transfer_links_list = [ 'isDefinedBy','isWWNDefinedBy',
                                'hasWWNCategory', 'hasWWNDefinition']
        link = 'hasSynonym'

        rem_nodes = []
        for name, attr in self.graph.items():
            if link in attr.keys():
                synonym = attr[link][0].lower()
                if synonym in self.graph.keys():
                    rem_nodes.append(name)
                    self.index_map[name] = synonym
                elif not name in self.index_map.keys():
                    self.index_map[name] = name

        new_graph = {}
        for key, val in self.graph.items():
            if not key in rem_nodes:
                new_graph[key] = val

        for key, val in self.graph.items():
            new_index = self.index_map[key]
            if key in rem_nodes:
                for key_t, val_t in val.items():
                    if key_t in transfer_links_list:
                        for v in val_t:
                            if key_t in new_graph[new_index].keys() and \
                                not v in new_graph[new_index][key_t]:
                                new_graph[new_index][key_t].append(v)
                            else:
                                new_graph[new_index][key_t] = [v]
                    elif key_t in transfer_links_dict:
                        for k, v in val_t.items():
                            if (key_t != 'hasSVOMatch'):
                                if key_t in new_graph[new_index].keys() and \
                                    k in new_graph[new_index][key_t].keys():
                                    new_graph[new_index][key_t][k] = \
                                        max(new_graph[new_index][key_t][k], v)
                                elif key_t in new_graph[new_index].keys() and \
                                    not k in new_graph[new_index][key_t].keys():
                                    new_graph[new_index][key_t][k] = v
                                elif not key_t in new_graph[new_index].keys():
                                    new_graph[new_index][key_t] = {k : v}
                            else:
                                if key_t in new_graph[new_index].keys() and \
                                    k in new_graph[new_index][key_t].keys() and \
                                    not v in new_graph[new_index][key_t][k]:
                                    new_graph[new_index][key_t][k].append(v)
                                elif key_t in new_graph[new_index].keys() and \
                                    not k in new_graph[new_index][key_t].keys():
                                    new_graph[new_index][key_t][k] = [v]
        self.graph = new_graph

    def add_index_map(self, index, synonym):
        """
        Add synonym index to index map.

        Args:
            filename:   A string with the name of the file to write to; if
                        not provided, it defaults to writing to resources/
                        scivar_kg.json.
        """

        index_keys = list(self.index_map.keys())
        graph_keys = list(self.graph.keys())
        if not synonym in index_keys and index in graph_keys:
            self.index_map[synonym] = index

    def write_index_map(self, filename = 'resources/scivar_index_map.json'):
        """
        Write index map to file.

        Args:
            filename:   A string with the name of the file to write to; if
                        not provided, it defaults to writing to resources/
                        index_map.json.
        """

        graph_str = json.dumps(self.index_map, indent = 4, sort_keys=True)

        try:
            with open(filename,"w") as f:
                f.write(graph_str)
        except:
            print('Warning: could not write index map to {}.'.format(filename))
            print('Call write_index_map() to write to the default')
            print('file: resources/index_map.json')

    def add_concept(self, var, depth = 1):
        """
        Add a concept "node" to the graph.

        Args:
            var:   A string containing the variable to add.
            depth: An integer indicating the "depth" to which the node
                   should be expanded. A value greater than 3 is not allowed
                   because it would both deviate too much from the original
                   variable and it would be very time expensive.
        """

        if depth > 3:
            print('Warning, depth is too large, resetting to 3 ...')
            depth = 3

        self.create_concept_levels(var, depth)

    def get_children(self, node_name):
        """
        Get the children of a node by name.

        The children of a node are those that are connected to the desired node
        by the relationships: 'components', 'isDefinedBy', 'isWWNDefinedBy'

        Args:
            node_name:   A string label of the desired node.
        """

        children = []

        if node_name in self.index_map.keys():
            name_index = self.index_map[node_name]
            if 'isDefinedBy' in self.graph[name_index].keys():
                children.extend(self.graph[name_index]['isDefinedBy'])
            if 'isWWNDefinedBy' in self.graph[name_index].keys():
                children.extend(self.graph[name_index]['isWWNDefinedBy'])

        return children

    def create_concept_levels(self, variable = '', depth = 0):
        """
        Expand a concept "node" to 'depth' amount (eg. performing depth
        iterations).

        Args:
            variable:   A string containing the variable to add.
            depth:      An integer indicating the "depth" to which the node
                        should be expanded. A value greater than 3 is not
                        allowed because it would both deviate too much from the
                        original variable and it would be very time expensive.
        """

        if (depth > 0) and (variable != ''):

            parsed_variable = pt.ParsedParagraph(variable)
            noun_groups = parsed_variable.get_noun_groups()

            for pno, ng in noun_groups.items():
                for ng_name, attr in ng.items():
                    noung = ng_name.lower()
                    self.add_term_node(noung, attr)

                    new_nodes = self.get_children(noung)
                    for n in new_nodes:
                        self.create_concept_levels(n, depth-1)

    def add_term_node(self, name, attr):
        """
        Add a node to the graph.

        Algorithm:
            The following components are added for the node:
            - annotate with SVO class, variables, and WWN category
            - break up into 'components' at ADPOSITION barriers (from attr)
            - break up the name and components into attributes, noun groups and
              individual nouns
            - this is a recursive function so that it repeats until it gets to
              the "end" where a node can no longer be broken down

        Args:
            name:   A string containing the node name to add.
            attr:   A dict containing key-value pairs as parsed and
                    generated by parse_tools when parsing a document.
        """

        existing_nodes = list(self.index_map.keys())
        lemma = ' '.join(attr['lemma_seq']).lower()
        name_lower = name.lower()

        if not name_lower in existing_nodes:

            self.graph[name_lower] = { 'pos_seq'   : attr['pos_seq'],
                                       'lemma_seq' : attr['lemma_seq'],
                                       'type'      : attr['type']       }
            self.add_index_map(name_lower, name_lower)

        if not name_lower in self.category_names and\
            not lemma in self.category_names:
            self.add_components(name_lower, attr)
            self.add_type_attr(name_lower, attr)
            self.add_noun_components(name_lower, attr)

            self.add_wwn_info(name_lower)
            self.add_svo_info(name_lower)
            self.expand_node(name_lower)


    def add_components(self, word, attr):
        """
        Add word components/component_of relationships.

        Args:
            word:       A string the label of the current node.
            attr:       A dict with the attr value pairs of the corresponding
                        word as parsed with parse_tools.
        """

        word_index = self.index_map[word]

        if 'components' in attr.keys():
            components_list = list(attr['components'].keys())
            if not 'hasComponents' in self.graph[word].keys():
                self.graph[word_index]['hasComponents'] = components_list
            else:
                self.graph[word_index]['hasComponents'].extend(components_list)

            for comp_word in attr['components'].keys():
                comp_lower = comp_word.lower()
                comp_attr = attr['components'][comp_lower]
                comp_attr['component_of'] = word
                self.add_term_node( comp_lower, comp_attr )

        if 'component_of' in attr.keys():
            comp_of = attr['component_of'].lower()
            if not 'isComponentOf' in self.graph[word_index].keys():
                self.graph[word_index]['isComponentOf'] = comp_of
            elif not comp_of in graph[word_index]['isComponentOf']:
                self.graph[word_index]['isComponentOf'].append(comp_of)

    def add_type_attr(self, word, attr):
        """
        Decompose word node into attributes and a root noun type.

        Args:
            word:       A string the label of the current node.
            attr:       A dict with the attr value pairs of the corresponding
                        word as parsed with parse_tools.
        """

        word_index = self.index_map[word]

        if 'has_type' in attr.keys():
            for node_type, nt_attr in attr['has_type'].items():
                self.add_term_node(node_type, nt_attr)

                if not 'isTypeOf' in self.graph[word_index].keys():
                    self.graph[word_index]['isTypeOf'] = [node_type]
                elif not node_type in self.graph[word_index]['isTypeOf']:
                    self.graph[word_index]['isTypeOf'].append(node_type)
                
                if not 'hasType' in self.graph[node_type].keys():
                    self.graph[node_type]['hasType'] = [word]
                elif not word in self.graph[node_type]['hasType']:
                    self.graph[node_type]['hasType'].append(word)

        if 'has_attribute' in attr.keys():
            for node_attr, na_attr in attr['has_attribute'].items():
                self.add_term_node(node_attr, na_attr)

                if not 'hasAttribute' in self.graph[word_index].keys():
                    self.graph[word_index]['hasAttribute'] = [node_attr]
                elif not node_attr in self.graph[word_index]['hasAttribute']:
                    self.graph[word_index]['hasAttribute'].append(node_attr)

                if not 'isAttributeOf' in self.graph[node_attr].keys():
                    self.graph[node_attr]['isAttributeOf'] = [word]
                elif not word in self.graph[node_attr]['isAttributeOf']:
                    self.graph[node_attr]['isAttributeOf'].append(word)

    def add_noun_components(self, name, attr):
        """
        Decompose noungrp word node into component nouns.

        Args:
            name : A string the label of the current node.
            attr : A dict with the attr value pairs of the corresponding
                   word as parsed with parse_tools.
        """

        name_index = self.index_map[name]

        if attr['type'] == 'noungrp':
            lemma_seq = attr['lemma_seq']
            i = 0
            for comp_name in name.split():
                attr2 = {'pos_seq':['NOUN'], 'lemma_seq':[lemma_seq[i]], 
                         'type': 'noun' }
                self.add_term_node(comp_name, attr2)
                if not 'hasComponents' in self.graph[name_index].keys():
                    self.graph[name_index]['hasComponents'] = [comp_name]
                elif not comp_name in self.graph[name_index]['hasComponents']:
                    self.graph[name_index]['hasComponents'].append(comp_name)

                comp_index = self.index_map[comp_name]
                if not 'isComponentOf' in self.graph[comp_index].keys():
                    self.graph[comp_index]['isComponentOf'] = [name]
                elif not name in self.graph[comp_index]['isComponentOf']:
                    self.graph[comp_index]['isComponentOf'].append(name)
                i += 1

    def add_wwn_info(self, name):
        """
        Pull categories and definition of a term from WiktiWordNet.

        Args:
            name:       A string the label of the current node.
        """

        name_index = self.index_map[name]

        lemma = ' '.join(self.graph[name]['lemma_seq']).lower()
        categories = self.wwn.get_category(name)
        if (categories == {}) and (lemma != ''):
            categories = self.wwn.get_category(lemma)

        for category in categories.keys():
            if not 'hasWWNCategory' in self.graph[name_index].keys():
                self.graph[name_index]['hasWWNCategory'] = [category]
            elif not category in self.graph[name_index]['hasWWNCategory']:
                self.graph[name_index]['hasWWNCategory'].append(category)

            definition = categories[category]
            if not 'hasWWNDefinition' in self.graph[name_index].keys():
                self.graph[name_index]['hasWWNDefinition'] = [definition]
            elif not definition in self.graph[name_index]['hasWWNDefinition']:
                self.graph[name_index]['hasWWNDefinition'].append(definition)

    def add_svo_info(self, name):
        """
        Pull entities and variables from SVO, divide into exact match, non-exact
        variable match, and non-exact, non-variable entity match.

        Args:
            name : A string the label of the current node.
        """

        name_index = self.index_map[name]

        if (len(name.split()) == 1):
            lemma = self.graph[name_index]['lemma_seq'][0]
            results = svoapi.rank_search([name, lemma])

            exact_match    = results.loc[results['rank']==1]
            variable_match = results.loc[(results['entityclass']=='Variable') & \
                                         (results['rank']!=1)]
            other_match    = results.loc[(results['entityclass']!='Variable') & \
                                         (results['rank']!=1)]

            entity_match = np.unique(exact_match['entity'].tolist())
            for entity in entity_match:
                exact_match_entity = exact_match[exact_match['entity']==entity]
                exact_match_label = list(np.unique( \
                                    exact_match_entity['entitylabel'].tolist()))
                if len(exact_match_label) < len(exact_match_entity):
                    print('Exact match label found twice: {}', entity)
                self.add_svo_index_map(exact_match_entity.iloc[0])

                svo_namespace = entity.split('/')[-1].split('#')[0]
                svo_entity = entity.split('#')[-1]
                svo_hash = hash(svo_namespace+svo_entity)
                if not svo_hash in self.svo_index_map.keys():
                    print('Hash error: {}, {}'.format(name_index, entity))
                svo_class = exact_match_entity['entityclass'].iloc[0]
                if not 'hasSVOMatch' in self.graph[name_index].keys():
                    self.graph[name_index]['hasSVOMatch'] = \
                                                { svo_class : [svo_hash] }
                elif not svo_class in self.graph[name_index]['hasSVOMatch']:
                    self.graph[name_index]['hasSVOMatch'][svo_class] = \
                                                [svo_hash]
                elif not svo_hash in \
                    self.graph[name_index]['hasSVOMatch'][svo_class]:
                    self.graph[name_index]['hasSVOMatch'][svo_class]\
                        .append(svo_hash)

            entity_match = np.unique(variable_match['entity'].tolist())
            for entity in entity_match:
                var_match_entity = variable_match[\
                                            variable_match['entity']==entity]
                var_match_label = list(np.unique(var_match_entity['entitylabel']\
                                        .tolist()))
                self.add_svo_index_map(var_match_entity.iloc[0])

                svo_namespace = entity.split('/')[-1].split('#')[0]
                svo_entity = entity.split('#')[-1]
                svo_hash = hash(svo_namespace+svo_entity)
                if not svo_hash in self.svo_index_map.keys():
                    print('Hash error: {}, {}'.format(name_index, entity))
                rank = max(var_match_entity['rank'].tolist())
                if not 'hasSVOVar' in self.graph[name_index].keys():
                    self.graph[name_index]['hasSVOVar'] = { svo_hash : rank }
                elif not svo_hash in self.graph[name_index]['hasSVOVar'].keys():
                    self.graph[name_index]['hasSVOVar'][svo_hash] = rank
                else:
                    self.graph[name_index]['hasSVOVar'][svo_hash] = max(rank, \
                        self.graph[name_index]['hasSVOVar'][svo_hash])

            entity_match = np.unique(other_match['entity'].tolist())
            for entity in entity_match:
                other_match_entity = other_match[other_match['entity']==entity]
                other_match_label = list(np.unique( \
                                other_match_entity['entitylabel'].tolist()))
                self.add_svo_index_map(other_match_entity.iloc[0])

                svo_namespace = entity.split('/')[-1].split('#')[0]
                svo_entity = entity.split('#')[-1]
                svo_hash = hash(svo_namespace+svo_entity)
                if not svo_hash in self.svo_index_map.keys():
                    print('Hash error: {}, {}'.format(name_index, entity))
                rank = max(other_match_entity['rank'].tolist())
                if not 'hasSVOEntity' in self.graph[name_index].keys():
                    self.graph[name_index]['hasSVOEntity'] = { svo_hash : rank }
                elif not svo_hash in \
                                self.graph[name_index]['hasSVOEntity'].keys():
                    self.graph[name_index]['hasSVOEntity'][svo_hash] = rank
                else:
                    self.graph[name_index]['hasSVOEntity'][svo_hash] = \
                        max(rank, \
                            self.graph[name_index]['hasSVOEntity'][svo_hash])

    def expand_node(self, word):
        """
        Expand a node by grabbing its Wikipedia and WWN definitions.

        Args:
            word: A string the label of the current node.
        """

        if not word in self.category_names:
            self.add_wikipedia_def(word, long=True)
            self.add_wwn_def(word)


    def add_wikipedia_def(self, name, long = False):
        """
        Get term's Wikipedia definition.

        Args:
            name: A string the label of the current node.
            long: A Boolean value indicating whether the whole Wikipedia page
                  should be parsed or just the definition paragraph. Default
                  is False.
        """

        [text, disambig, title, redirecttitle] = wapi.get_wikipedia_text(name)
        lemma = ' '.join(self.graph[name]['lemma_seq']).lower()

        title_lower = title.lower().replace('\s+','')
        redirect_lower = redirecttitle.lower().replace('\s+','')

        if not disambig:

            use_name = name
            syn = '('+name+')' in title_lower or\
                  '('+lemma+')' in title_lower or\
                  '('+name+')' in redirect_lower or\
                  '('+lemma+')' in redirect_lower

            if (name == redirect_lower) or \
                (lemma== title_lower) or \
                (lemma == redirect_lower) or syn:
                use_name = title_lower

            self.add_related(use_name, title_lower, name)

            use_name_index = self.index_map[use_name]
            if not 'isDefinedBy' in self.graph[use_name_index].keys():
                text_parsed = pt.ParsedDoc(text)
                p = text_parsed.find_is_nsubj(use_name)
                name_found = ''
                pno = -1
                if not p is None:
                    pno = list(p.keys())[0]
                    name_found = use_name
                    sno = p[pno][0]

                if (pno != -1) and (name_found == use_name):
                    def_noun_groups = text_parsed.paragraphs[pno].get_noun_groups()
                    self.add_definition(name, name_found, def_noun_groups)
                    if long:
                        noun_groups_index = text_parsed.get_term_noun_groups(name_found)
                        self.add_dimensions(name, name_found, noun_groups_index)

    def add_related(self, name, title, name_orig):
        """
        Add related and synonm terms based on Wikipedia search results.

        Args:
            name      : A string the label of the current node.
            title     : The title of the top Wikipedia page from search.
            name_orig : The original search term.
        """

        if name != title:
            src = self.index_map[name]
            dest = title
            if not 'isRelatedTo' in self.graph[src].keys():
                self.graph[src]['isRelatedTo'] = [dest]
            elif not dest in self.graph[src]['isRelatedTo']:
                self.graph[src]['isRelatedTo'].append(dest)

        if name != name_orig:
            src = self.index_map[name_orig]
            dest = name
            if not 'hasSynonym' in self.graph[src].keys():
                self.graph[src]['hasSynonym'] = [dest]
            elif not dest in self.graph[src]['hasSynonym']:
                self.graph[src]['hasSynonym'].append(dest)
            self.add_index_map(src, dest)

    def add_definition(self, name, name_found, nodes_par):
        """
        Add technical terms from Wikipedia definition.

        First sentence terms are added as isDefinedBy while second and later
        sentence terms are added as isCloselyRelatedTo.

        Args:
            name       : A string the label of the current node.
            name_found : The title of the top Wikipedia page from search.
            nodes_par  : A dict of the parsed noun groups in the definition
                         paragraph on Wikipedia.
        """

        name_index = self.index_map[name]
        max_i = min(len(nodes_par.keys()), 3)
        for i in range(1,max_i):
            nodes = nodes_par[i]
            if i == 1:
                edge_label = 'isDefinedBy'
            else:
                edge_label = 'isCloselyRelatedTo'
            for (node_name, attr) in nodes.items():
                if node_name.lower() != name_found:
                    if not edge_label in self.graph[name_index].keys():
                        self.graph[name_index][edge_label] = [node_name.lower()]
                    elif not node_name.lower() in \
                        self.graph[name_index][edge_label]:
                        self.graph[name_index][edge_label]\
                            .append(node_name.lower())

    def add_dimensions(self, name, name_found, noun_groups_index):
        """
        Add variations on the desired term from parsing the whole Wikipedia
        page.

        Args:
            name              : A string the label of the current node.
            name_found        : The title of the top Wikipedia page from search.
            noun_groups_index : A Pandas DataFrame containing the columns
                                'noun_group', 'modified', and 'aspects' as
                                described in parse_tools.
        """

        name_index = self.index_map[name]
        modified = noun_groups_index.loc[noun_groups_index['modified'],\
                                        'noun_group'].tolist()
        aspects = noun_groups_index.loc[noun_groups_index['aspects'],\
                                        'noun_group'].tolist()
        self.graph[name_index]['modified_terms'] = \
                                        [x for x in modified if x != name_found]
        self.graph[name_index]['term_aspects'] = \
                                        [x for x in aspects if x != name_found]

    def add_wwn_def(self, name):
        """
        Add Wiktionary definition terms from WiktiWordNet as isWWNDefinedBy.

        Args:
            name              : A string the label of the current node.
        """

        name_index = self.index_map[name]
        if 'hasWWNDefinition' in self.graph[name_index].keys():
            for definition in self.graph[name_index]['hasWWNDefinition']:
                def_parsed = pt.ParsedParagraph(definition)
                def_noun_groups = def_parsed.get_noun_groups(1)
                for ng, attr in def_noun_groups.items():
                    if ng.lower() != name:
                        if not 'isWWNDefinedBy' in self.graph[name_index].keys():
                            self.graph[name_index]['isWWNDefinedBy'] = \
                                                                [ng.lower()]
                        elif not ng.lower() in \
                            self.graph[name_index]['isWWNDefinedBy']:
                            self.graph[name_index]['isWWNDefinedBy']\
                                .append(ng.lower())

    def graph_inference(self):
        """
        Create inference links and new rank values for SVO Variable/Entity and WM
        indicator alignments. Assign most likely SVO category to each term.
        """

        self.graph_define_svo_category()
        self.graph_add_var_entity_links()

    def graph_define_svo_category(self):
        """
        Determine the most likely SVO category for all terms (detSVOCategory).
        """

        for term, attr in self.graph.items():
            if attr['type'] == 'adj':
                self.graph[term]['detSVOCategory'] = 'Attribute'
            elif attr['type'] == 'noun':
                if 'hasSVOMatch' in attr.keys() or \
                    'hasWWNCategory' in attr.keys():
                    if 'hasSVOMatch' in attr.keys():
                        classes = list(attr['hasSVOMatch'].keys())
                    else:
                        classes = attr['hasWWNCategory']
                    if 'Phenomenon' in classes or 'Matter' in classes or \
                        'Role' in classes or 'Form' in classes:
                        self.graph[term]['detSVOCategory'] = 'Phenomenon'
                    elif 'Property' in classes:
                        self.graph[term]['detSVOCategory'] = 'Property'
                    elif 'Attribute' in classes:
                        self.graph[term]['detSVOCategory'] = 'Attribute'
                    elif 'Process' in classes:
                        self.graph[term]['detSVOCategory'] = 'Process'
                    else:
                        self.graph[term]['detSVOCategory'] = classes[0]
                else:
                    self.graph[term]['detSVOCategory'] = 'Phenomenon'
            else:
                self.graph[term]['detSVOCategory'] = 'Phenomenon'


        for term, attr in self.graph.items():
            if attr['type'] == 'noungrp':
                self.graph[term]['detSVOCategory'] = 'Phenomenon'
                categories = {}
                for component in attr['hasComponents']:
                    if component in self.index_map.keys():
                        comp_index = self.index_map[component]
                        if (len(comp_index.split()) == 1):
                            cat = self.graph[comp_index]['detSVOCategory']
                            if not cat in categories.keys():
                                categories[cat] = 1
                            else:
                                categories[cat] += 1
                category = []
                count = 0
                for cat in categories.keys():
                    if categories[cat] > count:
                        category = [cat]
                        count = categories[cat]
                    elif categories[cat] == count:
                        category.append(cat)
                if 'Phenomenon' in category and 'Property' in category:
                    self.graph[term]['detSVOCategory'] = 'Variable'
                elif 'Phenomenon' in category or (category == []):
                    self.graph[term]['detSVOCategory'] = 'Phenomenon'
                elif 'Property' in category:
                    self.graph[term]['detSVOCategory'] = 'Property'
                elif 'Attribute' in category:
                    self.graph[term]['detSVOCategory'] = 'Attribute'
                elif 'Process' in category:
                    self.graph[term]['detSVOCategory'] = 'Process'
                else:
                    self.graph[term]['detSVOCategory'] = category[0]

        for term, attr in self.graph.items():
            if attr['type'] == 'modnoun':
                attr['detSVOCategory'] = 'Phenomenon'
                if attr['isTypeOf'][0] in self.index_map.keys():
                    typ = self.index_map[attr['isTypeOf'][0]]
                    category = self.graph[typ]['detSVOCategory']
                    if 'Attribute' in category:
                        self.graph[term]['detSVOCategory'] = 'Attribute'
                    elif 'Variable' in category:
                        self.graph[term]['detSVOCategory'] = 'Variable'
                    else:
                        self.graph[term]['detSVOCategory'] = \
                                                        'Specialized' + category

        for term, attr in self.graph.items():
            if (attr['type'] == 'adp') and ' of ' in term:
                attr['detSVOCategory'] = 'Phenomenon'

                categories = {}
                components = attr['hasComponents']
                for comp in components:
                    comp_index = self.index_map[comp]
                    cat = self.graph[comp_index]['detSVOCategory']
                    if not cat in categories.keys():
                        categories[cat] = 1
                    else:
                        categories[cat] += 1

                if ('Phenomenon' in categories.keys() or \
                    'SpecializedPhenomenon' in categories.keys()) \
                    and ('Property' in categories.keys() or \
                    'SpecializedProperty' in categories.keys()):
                    self.graph[term]['detSVOCategory'] = 'Variable'
                elif 'SpecializedPhenomenon' in categories.keys():
                    self.graph[term]['detSVOCategory'] = 'SpecializedPhenomenon'
                elif 'Phenomenon' in categories.keys():
                    self.graph[term]['detSVOCategory'] = 'Phenomenon'
                elif 'SpecializedProperty' in categories.keys():
                    self.graph[term]['detSVOCategory'] = 'SpecializedProperty'
                elif 'Property' in categories.keys():
                    self.graph[term]['detSVOCategory'] = 'Property'
                elif 'SpecializedAttribute' in categories.keys():
                    self.graph[term]['detSVOCategory'] = 'SpecializedAttribute'
                elif 'Attribute' in categories.keys():
                    self.graph[term]['detSVOCategory'] = 'Attribute'
                elif 'SpecializedProcess' in categories.keys():
                    self.graph[term]['detSVOCategory'] = 'SpecializedProcess'
                elif 'Process' in categories.keys():
                    self.graph[term]['detSVOCategory'] = 'Process'

    def graph_add_var_entity_links(self):
        """Propagate SVO variable and WM indicator links "upward" in knowledge
        graph."""

        terms = list(self.graph.keys())
        all_links = self.variable_links['first_order'] + \
                    self.variable_links['second_order']
        matched_link = ['hasSVOVar', 'hasSVOEntity', 'hasWMIndicator']

        for link in all_links:
            factor = 1
            if link in self.variable_links['second_order']:
                factor = 0.83
            for term in terms:
                if link in self.graph[term].keys():
                    linked_terms = self.graph[term][link]
                    num_linked_terms = len(linked_terms)
                    for typ_link in matched_link:
                        new_val = {}
                        if not typ_link in self.graph[term].keys():
                            self.graph[term][typ_link] = {}
                        for lterm in linked_terms:
                            if lterm in self.index_map.keys() and \
                                typ_link in self.graph[self.index_map[lterm]].keys():
                                entity = self.graph[self.index_map[lterm]][typ_link]
                                for key, val in entity.items():
                                    if not key in new_val.keys():
                                        new_val[key] = 0
                                    new_val[key] += factor * val/num_linked_terms
                        for key, val in new_val.items():
                            if val > 0.05:
                                if key in self.graph[term][typ_link].keys():
                                    self.graph[term][typ_link][key] = \
                                    max(val, self.graph[term][typ_link][key])
                                else:
                                    self.graph[term][typ_link][key] = val
