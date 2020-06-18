from SPARQLWrapper import SPARQLWrapper
from SPARQLWrapper import JSON as sqjson
import pandas as pd
import numpy as np

from Levenshtein import distance as levenshtein_distance

# search for a term in all labels of an entity
# cl: can search either All classes or a specific top level class
# subcl: set to True to find subclasses as well
# return a Pandas dataframe containing the columns: term, entity, entitylabel, entityclass
def search_label(term, cl = 'All', subcl = False):
    
    # search ontology for term, filter by class
    valid_classes = ['Variable', 'Phenomenon', 'Property', 'Process', 'Abstraction',
                     'Operator', 'Attribute', 'Part', 'Role', 'Trajectory']
    eclassstr = "#" + "|#".join(valid_classes)
    
    if (cl != 'All') and cl in valid_classes:
        eclassstr = '#' + cl
    elif (cl != 'All'):
        print('Class', cl, 'not a valid class. Searching all classes instead ...')
        
    if subcl:
        eclassstr = eclasstr.replace('#','')
        
    # set query
    # valid terms is any term bounded by start/end of string, ~, _, -, or space (for altLabel)
    # free query for term, filter results for exact matches (not partial words, e.g. rice does not return price, etc)
    data = pd.DataFrame(columns = ['term','entity','entitylabel','entityclass'])
    for t in term.replace('_',' ').split():
        sparql = SPARQLWrapper("http://35.194.43.13:3030/ds/query")
        sparql.setQuery("""
                        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                        PREFIX svu: <http://www.geoscienceontology.org/svo/svu#>
                        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

                        SELECT DISTINCT ?entity ?preflabel ?entitylabel ?entityclass
                        WHERE {{
                               ?entity rdf:type ?entityclass .
                               BIND (STR(?entityclass) as ?classstr) .
                               FILTER regex(?classstr,"({})$","i") .
                               ?entity rdfs:label ?elabel  .
                               BIND (STR(?elabel) as ?entitylabel) .
                               FILTER regex(?entitylabel,"(?=.*(^|~|_|-| ){}($|~|_|-| ))","i") .
                               ?entity skos:prefLabel ?plabel  .
                               BIND (STR(?plabel) as ?preflabel) .
                               }}
                        ORDER BY ?entity ?entitylabel ?entityclass
                        """.format(eclassstr, t))
        sparql.setReturnFormat(sqjson)

        results = []
        try:
            results = sparql.query().convert()
        except Exception as e:
            print(e)
    
        if results != []:
            for result in results["results"]["bindings"]:
                e = result["entity"]["value"]
                epl = result["preflabel"]["value"]
                el = result["entitylabel"]["value"]
                ec = result["entityclass"]["value"].split('#')[1]
                data = data.append({'term':t,'entity':e,'entitypreflabel':epl, 'entitylabel':el,'entityclass':ec}, \
                                   ignore_index = True)
            #print('Successfully finished query.')
    
    return data

# search for all entities linked to a given entity
# cl: can search either All classes or a specific top level class
# subcl: set to True to find subclasses as well
# entitites is passed as a dataframe, result from search_label
# return a Pandas dataframe containing the columns: term, entity, entitylabel, entityclass,
#                                                   linkedentity, linkedentitylabel, linkedentityclass
# linkedentity (and label, class) will be one of the entities passed in
# entity (and label, class) will be the entities linked to that entity
# term will be the term associated with the linked entity (from the original search)
def search_entity_links(entities, cl = 'All', subcl = False):
    
    # search ontology for term, can filter by class
    valid_classes = ['Variable', 'Phenomenon', 'Property', 'Process', 'Abstraction',
                    'Operator', 'Attribute', 'Part', 'Role', 'Trajectory']
    lclassstr = "#" + "|#".join(valid_classes)
    
    if (cl != 'All') and cl in valid_classes:
        lclassstr = '#' + cl
    elif (cl != 'All'):
        print('Class', cl, 'not a valid class. Searching all classes instead ...')
        
    if subcl:
        lclassstr = lclasstr.replace('#','')
        
    # set query
    # free query for term, filter results for exact matches
    data = pd.DataFrame(columns = ['term','entity','entitylabel','entityclass',
                                   'linkedentity','linkedentitylabel','linkedentityclass'])
    for i in entities.index:
        entity = entities.loc[i,'entity']
        sparql = SPARQLWrapper("http://35.194.43.13:3030/ds/query")
        sparql.setQuery("""
                        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                        PREFIX svu: <http://www.geoscienceontology.org/svo/svu#>
                        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

                        SELECT DISTINCT ?linkedentity ?preflabel ?linkedlabel ?linkedclass
                        WHERE {{
                               ?linkedentity ?rel <{}>.
                               ?linkedentity rdf:type ?linkedclass .
                               BIND (STR(?linkedclass) as ?lclassstr) .
                               FILTER regex(?lclassstr,"({})$","i") .
                               ?linkedentity rdfs:label ?llabel .
                               ?linkedentity skos:prefLabel ?plabel .
                               BIND (STR(?plabel) as ?preflabel).
                               BIND (STR(?llabel) as ?linkedlabel).
                                }}
                        ORDER BY ?entity ?entitylabel ?linkedclass
                        """.format(entity, lclassstr))
        sparql.setReturnFormat(sqjson)

        results = []
        try:
            results = sparql.query().convert()
        except Exception as e:
            print(e)
    
        if results != []:
            term = entities.loc[i,'term']
            for result in results["results"]["bindings"]:
                el = entities.loc[i,'entitylabel']
                epl = entities.loc[i,'entitypreflabel']
                ec = entities.loc[i,'entityclass']
                le = result["linkedentity"]["value"]
                lepl = result["preflabel"]["value"]
                lel = result["linkedlabel"]["value"]
                lec = result["linkedclass"]["value"].split('#')[1]
                data = data.append({'term':term,'entity':le,'entitylabel':lel,'entitypreflabel':lepl,'entityclass':lec,
                                   'linkedentity':entity,'linkedentitylabel':el,'linkedentitypreflabel':epl,
                                    'linkedentityclass':ec}, \
                                   ignore_index = True)
            #print('Successfully finished query.')
    
    return data

# basic term search
# terms is a list of terms to search that are all synonyms
# cl: can search either All classes or a specific top level class
# subcl: set to True to find subclasses as well
# returns a pandas dataframe of directly labeled entities and linked entities related to the
# search term(s)
def search(terms, cl = 'All', subcl = False):
    
    first_degree_entities = search_label(terms[0], cl, subcl)
    terms_searched = [terms[0]]
    for i in range(1, len(terms)):
        if not terms[i] in terms_searched:
            first_degree_entities = first_degree_entities.append(search_label(terms[i], cl, subcl), \
                                               ignore_index = True, sort = False).fillna('')
            terms_searched.append(terms[i])

    second_degree_entities = search_entity_links(first_degree_entities, cl, subcl)
    
    results = first_degree_entities.append(second_degree_entities, ignore_index = True, sort = False).fillna('')
    
    return results
    
# ranked term search 
# terms is a list of terms to search that are all synonyms
# cl: can search either All classes or a specific top level class
# subcl: set to True to find subclasses as well
# returns a pandas dataframe of directly labeled entities and linked entities related to the
# search term(s) as well as a rank (from 0 to 1) of the match
def rank_search(terms, cl = 'All', subcl = False):
    
    results = search(terms, cl, subcl)
    results['rank'] = 0
    
    for entity in np.unique(results['entity'].tolist()):
        # all entries that match this entity
        entity_results = results.loc[results['entity'] == entity]
        
        # all of the labels associated with this entity
        entity_labels  = entity_results['entitylabel'].tolist()  +  \
                         entity_results['entitypreflabel'].tolist()
       
        # the entity 'label'
        label = entity.split('#')[1].replace('%40','@')\
                        .replace('%7E','~').replace('%28','(').replace('%29',')')
        label_atmed = label.count('@medium')
        label_at = label.count('@') - label_atmed
        label_adp = label.count('_of_')
        
        # count how many times a unique term was found associated with 
        # this entity
        # penalties accrue for terms that are not found
        occurences = np.unique(entity_results['term'].tolist())
        num_occurences = len(list(occurences))
        
        max_term_len = 0
        term_penalty = 100
        for term in terms:
            penalty = 0
            for word in term.split():
                if not word in occurences:
                    penalty += 1
            length = len(term.split())
            max_term_len = max(max_term_len, length)
            term_penalty = min(term_penalty, penalty/length)
        
        num_occurences = min(num_occurences, max_term_len)
        # calculate the distance between the labels associated with the entity
        # and the search terms (second penalty)
        # only the minimum distance used
        string_distance = 100
        for l in entity_labels:
            for term in terms:
                dist = levenshtein_distance(l.replace('_of_', ' ')\
                                            .replace('_',' '), term.strip())
                string_distance = min(string_distance, dist)
        
        # calculated the number of entities included in the id (complete var repr)
        len_id = (len(label.replace('@','_').replace('~','_').replace('\(','')\
                        .replace('\)','').replace('-or-','_').replace('-and-','_')\
                        .replace('-per-','_').replace('-to-','_')\
                        .split('_')) - 2*label_at - label_atmed - label_adp)
        num_occurences = min(num_occurences, len_id)
        
        # rank calculation:
        # string distance rank (no less than 0.7)
        #dist_penalty = min( .005 * string_distance, 0.05 )
        #rank = max(0, (num_occurences - term_penalty * 0.9)/len_id  - dist_penalty)
        rank = max(0.1, (num_occurences - term_penalty * 0.2)/len_id)
        results.loc[results['entity']==entity, 'rank'] = rank
                
    
    # indirect links are penalized
    results.loc[results['linkedentity']!='', 'rank'] = \
                results.loc[results['linkedentity']!='', 'rank'] * 0.7
    
    results = results.sort_values(by = ['rank', 'entitylabel', 'linkedentitylabel'], \
                                  ascending = [False, True, True])
    
    
        
    return results.drop_duplicates(subset=['entity'], keep='first')
