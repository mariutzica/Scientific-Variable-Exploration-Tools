# code for ontology API
from SPARQLWrapper import SPARQLWrapper
from SPARQLWrapper import JSON as sqjson
import pandas as pd
import numpy as np
#from parse_variable import clean_input
#import wikipediaapi as wapi
#import nltk
from Levenshtein import distance as levenshtein_distance

# search for a term in all labels of an entity
def search_label(term, cl = 'All', subcl = False):
    
    # search ontology for term, can filter by class
    valid_classes = ['Variable', 'Phenomenon', 'Property', 'Process', 'Abstraction',
                    'Operator', 'Attribute', 'Part', 'Role', 'Trajectory']
    eclassstr = "#" + "|#".join(valid_classes)
    
    if (cl != 'All') and cl in valid_classes:
        eclassstr = '#' + cl
    elif (cl != 'All') and not cl in valid_classes:
        print('Class', cl, 'not a valid class. Searching all classes instead ...')
        
    if subcl:
        eclassstr = eclasstr.replace('#','')
        
    # set query
    # free query for term, filter results for exact matches
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
def search_entity_links(entities, cl = 'All', subcl = False):
    
    # search ontology for term, can filter by class
    valid_classes = ['Variable', 'Phenomenon', 'Property', 'Process', 'Abstraction',
                    'Operator', 'Attribute', 'Part', 'Role', 'Trajectory']
    lclassstr = "#" + "|#".join(valid_classes)
    
    if (cl != 'All') and cl in valid_classes:
        lclassstr = '#' + cl
    elif (cl != 'All') and not cl in valid_classes:
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
def search(terms, cl = 'All', subcl = False):
    
    first_degree_entities = search_label(terms[0], cl, subcl)
    if terms[1] != terms[0]:
        first_degree_entities = first_degree_entities.append(search_label(terms[1], cl, subcl), \
                                               ignore_index = True, sort = False).fillna('')
    #print('first search done')
    second_degree_entities = search_entity_links(first_degree_entities, cl, subcl)
    #print('Search finished ...')
    
    results = first_degree_entities.append(second_degree_entities, ignore_index = True, sort = False).fillna('')
    
    return results
    
    
def rank_search(terms, cl = 'All', subcl = False):
    
    results = search(terms, cl, subcl)
    results['rank'] = 0
    
    for entity in np.unique(results['entity'].tolist()):
        # all entries that match this entity
        entity_results = results.loc[results['entity'] == entity]
        # all of the labels associated with this entity
        entity_labels  = entity_results['entitylabel'].tolist()  +  \
                         entity_results['entitypreflabel'].tolist()
        # the id 'label'
        label = entity.split('#')[1].replace('%40','@')\
                        .replace('%7E','~').replace('%28','(').replace('%29',')')
        label_atmed = label.count('@medium')
        label_at = label.count('@') - label_atmed
        
        # count how many times a unique term was found associated with 
        # this entity
        # penalties accrue for terms that are not found
        occurences = np.unique(entity_results['term'].tolist())
        num_occurences1 = 0
        num_occurences2 = 0
        penalty1 = 0
        penalty2 = 0
        for word in terms[0].split():
            if word in occurences:
                num_occurences1 += 1
            else:
                penalty1 += 1
        for word in terms[1].split():
            if word in occurences:
                num_occurences2 += 1
            else:
                penalty2 += 1
                
        # calculate the distance between the labels associated with the entity
        # and the search terms (third penalty)
        string_distance = 100
        for l in entity_labels:
            dist1 = levenshtein_distance(l, terms[0])
            dist2 = levenshtein_distance(l, terms[1])
            string_distance = min(string_distance, min(dist1, dist2))
        
        # calculated the number of entities included in the id (complete var repr)
        len_id = (len(label.replace('@','_').replace('~','_').replace('\(','')\
                        .replace('\)','').replace('-or-','_').replace('-and-','_')\
                        .split('_')) - 2*label_at - label_atmed)
        
        
        results.loc[results['entity']==entity, 'rank'] = \
                    max((num_occurences1-penalty1*.25)/len_id, (num_occurences2 - penalty2*.25)/len_id, 0)\
                        *max(1-.05*string_distance,0.7)
    
    # indirect links are penalized
    results.loc[results['linkedentity']!='', 'rank'] = \
                results.loc[results['linkedentity']!='', 'rank'] * 0.5
    
    results = results.sort_values(by = ['rank', 'entitylabel', 'linkedentitylabel'], \
                                  ascending = [False, True, True])
    #compact_results = pd.DataFrame(columns = results.columns.values)
    #for entity in np.unique(results['entity'].tolist()):
    #    compact_results.loc[len(compact_results)] = results.loc[results]
        
    return results

# search for all entities linked to a given entity
def search_term_class(term):
    
    # search ontology for term, can filter by class
    valid_classes = ['Variable', 'Phenomenon', 'Property', 'Process', 'Abstraction',
                    'Operator', 'Attribute', 'Part', 'Role', 'Trajectory']
    classstr = "|".join(valid_classes)
    num_terms = 0
    # set query
    # free query for term, filter results for exact matches
    data = []
    sparql = SPARQLWrapper("http://35.194.43.13:3030/ds/query")
    sparql.setQuery("""
                        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                        PREFIX svu: <http://www.geoscienceontology.org/svo/svu#>
                        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

                        SELECT DISTINCT ?entity ?classstr
                        WHERE {{
                               ?entity rdf:type ?class.
                               ?class rdfs:label ?classlabel .
                               BIND (STR(?classlabel) as ?classstr) .
                               FILTER regex(?classstr,"^(?:{})$","i") . 
                               ?entity rdfs:label ?label .
                               BIND (STR(?label) as ?strlabel).
                               FILTER regex(?strlabel,"^{}$","i") .
                               }}
                        ORDER BY ?class
                        """.format(classstr, term.replace(' ','_')))
    sparql.setReturnFormat(sqjson)

    results = []
    try:
        results = sparql.query().convert()
    except Exception as e:
        print(e)
   
    data = []
    if results != []:
        for result in results["results"]["bindings"]:
            cl = result['classstr']["value"]
            if not cl in data:
                data.append(cl)
            #print('Successfully finished query.')
    
    return data