import numpy as np
import pandas as pd

import stanza
#stanza.download('en')
nlp = stanza.Pipeline('en')

class ParsedDoc:
    """Record noun groups and related elements in a Document.

    A class to hold information about the noun groups in a document of text --
    in this particular case, a Wikipedia page. Noun groups are groups of 
    nouns, adjectives and adpositions; noun groups are the common language of
    technical concepts in the sciences and engineering. This parsed document can
    be used to generate knowledge graphs of scientific concepts and how they
    relate to each other.

    Attributes:
        paragraphs:       A dictionary with keys being the paragraph numbers
                          and values being instances of the ParsedParagraph class
        num_paragraphs:   An integer count of the number of paragraphs in the 
                          document.
        title:            The title of the Wikipedia page for the parsed text.
        term_def_index:   A dictionary with keys being single or multiword phrases
                          and values being the integer number of the paragraph
                          in which its definition sentence occurs. A definition is
                          a sentence that contains the verbs "to be", "to define", or
                          "to refer to" with the term being the corresponding subject
                          of the existence verb.
        noun_group_count: A Pandas DataFrame object containing the columns
                          noun_group, count, type that contain the following information:
                          - noun_group: unique noun group occurring in the document
                          - count: number of occurrences in the document
                          - type: single, adjectival, or multiple meaning
                              + single: one or more nouns (no other parts of speech present)
                              + adjectival: a single modified by one or more leading adjectives
                              + multiple: two or more singles or adjectivals combined
                                          with adpositions
        
    """
    
    def __init__(self, text = None, title = ''):
        """
        Intialize ParsedDoc with the text and title of the Wikipedia page, if present.
        The text is parsed into paragraphs with self.add_paragraph().
        """
        self.paragraphs = {}
        self.num_paragraphs = 0
        self.title = title
        self.term_def_index = {}
        self.noun_group_count = None
        
        if not text is None:
            if isinstance(text, str):
                text = [text]
                
            for paragraph in text:
                self.add_paragraph(paragraph)
            
            self.num_paragraphs = max(self.paragraphs.keys())
            self.count_noun_groups()
    
    def add_paragraph(self, paragraph = ''):
        "Add a ParsedParagraph element to the paragraphs dict attribute."
        if paragraph != '':
            self.num_paragraphs += 1
            self.paragraphs[self.num_paragraphs] = ParsedParagraph(paragraph)
            
    def find_is_nsubj(self, term, first_only = True):
        """Find the "is" statement(s) with the subject "term" (case-independent)

        Args:
            term: An string containing the exact term to search for (case not important).
            first_only: A Boolean indicating where only the first definition should be 
                        found (first_only = True, default) or if all is statements in 
                        the document should be identified (first_only = False). Setting
                        to False greatly increases the processing time for long documents.
        Returns:
            A dict with the following format
            
            { pno1 : [sno11, sno12, ...],
              ...
              pnox : [snox1, snox2, ...] }
              
            where

            pno1, pnox : the paragraph where the is statement for the term was found
            sno1, snox : a list of sentences within the corresponding paragraph where the 
                         is statement was found
            
            If an is statement for the desired term is not found, None is returned.
            
            To save processing times for future runs of the function, any indexes found
            in this pass are saved to the dict attribute term_def_index. This index is
            searched first upon any call to the function, before any further analysis takes
            place.
            
        """
        
        term_index = None
        term_lower = term.lower()
        done       = False
        
        for pno in self.paragraphs.keys():
            if not done:
                sno = self.paragraphs[pno].find_is_nsubj(term_lower, first_only)
                if not sno is None:
                    if term_index is None:
                        term_index = {}
                    if not term_lower in self.term_def_index.keys():
                        self.term_def_index[term_lower] = [pno]
                    if not pno in self.term_def_index[term_lower]:
                        self.term_def_index[term_lower].append(pno)
                    term_index[pno] = sno        
                    if first_only:
                        done = True           
        return term_index
        
    def count_noun_groups(self):
        """Count all of the noun groups on a page, and sort them in descending order

        Update the self.noun_group_count Pandas dataframe with the following columns:
            noun_group : string, unique noun group occurring in the document containing the desired
                         term
            count      : integer, number of occurrences in the document
            type       : string - 'single', 'adjectival', or 'multiple' meaning
                            + single     : one or more nouns (no other parts of speech present)
                            + adjectival : a single modified by one or more leading adjectives
                            + multiple   : two or more singles or adjectivals combined
                                           with adpositions
        """
        
        noun_group_count = pd.DataFrame(columns = ['noun_group', 'count', 'type'])
        for par_no, paragraph in self.paragraphs.items():
            noun_group_count = noun_group_count.append(paragraph.count_noun_groups(), ignore_index = True)
            
        # combine and resort
        self.noun_group_count = pd.DataFrame(columns = ['noun_group', 'count', 'type'])
        for ng in np.unique(noun_group_count['noun_group'].tolist()):
            typ = noun_group_count.loc[noun_group_count['noun_group']==ng, 'type'].iloc[0]
            count = sum(noun_group_count.loc[noun_group_count['noun_group']==ng, 'count'].tolist())
            self.noun_group_count.loc[len(self.noun_group_count)] = [ng, count, typ] 
        self.noun_group_count = self.noun_group_count.sort_values(by=['count', 'noun_group'], \
                                                                  ascending = [False, True])
    
    def get_term_noun_groups(self, term):
        """Get all of the noun groups on a page involving a desired "term" (case insensitive), 
        sorted in descending order by occurence count.

        Use the self.noun_group_count Pandas dataframe and filter for terms according to their type
        as determined in count_noun_groups execution.
        
        Args:
            term: An string containing the exact term to search for (case not important).
            
        Returns:
            A Pandas DataFrame, sorted in descending order by 'count', with the following columns
            
            noun_group : string, unique noun group occurring in the document containing the desired
                         term
            count      : integer, number of occurrences in the document
            type       : string - 'single', 'adjectival', or 'multiple' meaning
                            + single     : one or more nouns (no other parts of speech present)
                            + adjectival : a single modified by one or more leading adjectives
                            + multiple   : two or more singles or adjectivals combined
                                           with adpositions
            modified   : boolean, True if desired term modified with either a noun or an 
                         adjective (head only)
            aspects    : boolean, True if term modified with noun (tail only) and terms 
                         with adpositions
            
            If no noun groups contain the desired term, the returned DataFrame will be empty.            
        """
        
        term_lower = term.lower()
        noun_groups = None
        if self.noun_group_count is None:
            self.count_noun_groups()
            
        noun_groups = self.noun_group_count.copy()
        noun_groups = noun_groups.loc[noun_groups['noun_group'].str.contains(term_lower)]
        noun_groups['modified'] = False
        noun_groups['aspects'] = False
           
        contains_term    = noun_groups['noun_group'].str.contains(term_lower)
        endswith_term    = noun_groups['noun_group'].str.strip().str.endswith(' '+term_lower)
        is_adj_or_simple = noun_groups['type'].isin(['adjectival','simple'])
        is_multiple      = ~is_adj_or_simple
        noun_groups.loc[ endswith_term & is_adj_or_simple, 'modified'] = True
            
        noun_groups.loc[contains_term & ~endswith_term & is_adj_or_simple, \
                        'aspects'] = True
        noun_groups.loc[contains_term & is_multiple, 'aspects'] = True
            
        return noun_groups
        
class ParsedParagraph:
    """Record noun groups and related elements in a Paragraph.

    A class to hold information about the noun groups in a paragraph of text. 
    Noun groups are groups of nouns, adjectives and adpositions; noun groups are 
    the common language of technical concepts in the sciences and engineering. 
    This parsed paragraph can be used in the generation of ParsedDocument objects
    or as a standalone object.

    Attributes:
        sentences:        A dictionary with keys being the sentence numbers
                          and values being instances of the ParsedSentence class
        num_sentences:    An integer count of the number of sentences in the 
                          paragraph.
        term_def_index:   A dictionary with keys being single or multiword phrases
                          and values being the integer number of the sentence
                          in which its definition occurs. A definition is
                          a sentence that contains the verbs "to be", "to define", or
                          "to refer to" with the term being the corresponding subject
                          of the existence verb.
        noun_group_count: A Pandas DataFrame object containing the columns
                          noun_group, count, type that contain the following information:
                          - noun_group: unique noun group occurring in the paragraph
                          - count: number of occurrences in the paragraph
                          - type: single, adjectival, or multiple meaning
                              + single: one or more nouns (no other parts of speech present)
                              + adjectival: a single modified by one or more leading adjectives
                              + multiple: two or more singles or adjectivals combined
                                          with adpositions
        
    """
    
    def __init__(self, text = None):
        """
        Intialize ParsedParagraph with the text provided, if present.
        The text is parsed into sentences with self.add_sentence().
        """
        self.sentences = {}
        self.num_sentences = 0
        self.term_def_index = {}
        self.noun_group_count = None
        if not text is None and (text != ''):
            parsed_paragraph = nlp(text)
            for sentence in parsed_paragraph.sentences:
                self.add_sentence(sentence)
            self.num_sentences = max(self.sentences.keys())
            
    def add_sentence(self, sentence = None):
        "Add a ParsedSentence element to the sentences dict attribute."
        if not sentence is None:
            self.num_sentences += 1
            self.sentences[self.num_sentences] = ParsedSentence(sentence)
            
    def find_is_nsubj(self, term, first_only = True):
        """Finds the "is" statement(s) with the subject "term" (case-independent)

        Args:
            term: An string containing the exact term to search for (case not important).
            first_only: A Boolean indicating where only the first definition should be 
                        found (first_only = True, default) or if all is statements in 
                        the paragraph should be identified (first_only = False). Setting
                        to False increases the processing time significantly if the
                        paragraph contains many sentences.
        Returns:
            A list containing all of the keys of the "is: sentences found with the 
            desired term as the subject.
              
            [sno1, sno2, ...]
            
            If an is statement for the desired term is not found, None is returned.
            
            To save processing times for future runs of the function, any indexes found
            in this pass are saved to the dict attribute term_def_index. This index is
            searched first upon any call to the function, before any further analysis takes
            place.
            
        """
        
        term_index = None
        term_lower = term.lower()
        done       = False
        
        for sno in self.sentences.keys():
            if not done:
                found = self.sentences[sno].find_is_nsubj(term_lower)
                if found:
                    if not term_lower in self.term_def_index.keys():
                        self.term_def_index[term_lower] = [sno]
                    if not sno in self.term_def_index[term_lower]:
                        self.term_def_index[term_lower].append(sno)
                    term_index = self.term_def_index[term_lower]        
                    if first_only:
                        done = True           
        return term_index
    
    def count_noun_groups(self):
        """Count all of the noun groups on a page, and sort them in descending order

        Update the self.noun_group_count Pandas dataframe with the following columns:
            noun_group : string, unique noun group occurring in the document containing the desired
                         term
            count      : integer, number of occurrences in the document
            type       : string - 'single', 'adjectival', or 'multiple' meaning
                            + single     : one or more nouns (no other parts of speech present)
                            + adjectival : a single modified by one or more leading adjectives
                            + multiple   : two or more singles or adjectivals combined
                                           with adpositions
        """
        noun_group_count = pd.DataFrame(columns = ['noun_group', 'count', 'type'])
        for sent_no, sentence in self.sentences.items():
            noun_group_count = noun_group_count.append(sentence.count_noun_groups(), ignore_index = True)
            
        # combine and resort
        self.noun_group_count = pd.DataFrame(columns = ['noun_group', 'count', 'type'])
        for ng in np.unique(noun_group_count['noun_group'].tolist()):
            typ = noun_group_count.loc[noun_group_count['noun_group']==ng, 'type'].iloc[0]
            count = sum(noun_group_count.loc[noun_group_count['noun_group']==ng, 'count'].tolist())
            self.noun_group_count.loc[len(self.noun_group_count)] = [ng, count, typ] 
        self.noun_group_count = self.noun_group_count.sort_values(by=['count', 'noun_group'], \
                                                                  ascending = [False, True])
        
        return self.noun_group_count.copy()
            
class ParsedSentence:
    """Record noun groups and related elements in a Sentence.

    A class to hold information about the noun groups in a sentence. 
    Noun groups are groups of nouns, adjectives and adpositions; noun groups are 
    the common language of technical concepts in the sciences and engineering. 
    This parsed sentence can be used in the generation of ParsedParagraph objects
    or as a standalone object.

    Attributes:
        noun_groups:      A NounGroup object holding information about the noun groups 
                          and their associated components.
        nsubj:            The subject of the sentence if it is an existence sentence
                          containing one of the verbs "to be", "to refer to", "to define"
                          Value is set to None by default and set to '' (empty string) if 
                          search was performed and no is statement was found in the sentence.
        text:             The raw text of the sentence.
        words:            A list of words and their part of speech information as generated
                          by the Stanford Stanza tool.
        noun_group_count: A Pandas DataFrame object containing the columns
                          noun_group, count, type that contain the following information:
                          - noun_group: unique noun group occurring in the sentence
                          - count: number of occurrences in the sentence
                          - type: single, adjectival, or multiple meaning
                              + single: one or more nouns (no other parts of speech present)
                              + adjectival: a single modified by one or more leading adjectives
                              + multiple: two or more singles or adjectivals combined
                                          with adpositions
        
    """
    
    def __init__(self, sentence = None):
        """
        Intialize ParsedSentence with the sentence object provided, if present.
        The sentence is in the form of a sentence object as returned by the 
        Stanza text parser.
        """
        self.noun_groups = None
        self.nsubj = None
        self.text = ''
        self.words = []
        self.noun_group_count = None
        
        if not sentence is None:
            self.text  = sentence.text
            self.words = sentence.words
            self.noun_groups = NounGroup(sentence.words)
                        
    def find_is_nsubj(self, term):
        """Find if there is an "is" statment with subject "term" in the ParsedSentence.
        
        To determine if an is statement about "term" is present, the algorithm first finds 
        all nsubj of a sentence that correspond to the verbs "to be", "to refer to" or 
        "to describe". Parsed tags are obtained with the Stanford Stanza tool.
        
        Args:
            term: An string containing the exact term to search for (case not important).
            
        Returns:
            A Boolean value with False indicating that an is statement about the desired
            term was not found and True indicating that such a statement was found.
            
            To save processing times for future runs of the function, the subject of the
            sentence, if it is an is statement is saved to nsubj. If no valid is statement
            is found, nsubj is set to an empty string (''). nsubj is
            referenced first upon any call to the function, before any further analysis takes
            place.
            
        """
        
        term_lower = term.lower()
        found      = False
        if self.nsubj == term_lower:
            found = True
        elif self.nsubj is None and term_lower in self.text.lower():
            self.nsubj = ''
            # use Stanza to assign part of speech and determine roles of each word in the sentence.
            nsubj_words = []
            obj_words = []
            obl_words = []
            vb_groupings = {}
            compound_words = []
            conj_words = []

            # loop through the words to find nsubj, obj, verb, conj, and compound
            # (there are also adjectives to take care of, and these will be extracted later)
            words = self.words
            for word in words:
                head_word = words[word.head - 1]
                if word.deprel[:5] == 'nsubj':
                    nsubj_words.append(word.id)
                elif word.deprel[:3] == 'obj':
                    obj_words.append(word.id)
                elif (word.deprel == 'root') and (word.xpos[:2] == 'NN'):
                    obj_words.append(word.id)
                elif word.deprel[:3] == 'obl':
                    obl_words.append(word.id)
                elif (word.xpos[:2] == 'VB') and word.lemma in ['be', 'describe', 'define', 'refer']:
                    vb_groupings[word.id] = {'verb': word.lemma, 'nsubj':{}, 'obj':{}, 'obl':{}}
                elif (word.deprel[:4] == 'conj') and (head_word.deprel[:5] == 'nsubj'):
                    nsubj_words.append(word.id)
                elif (word.deprel[:4] == 'conj') and (head_word.deprel[:3] == 'obj'):
                    obj_words.append(word.id)
                elif (word.deprel[:4] == 'conj') and (head_word.deprel == 'root') \
                    and (head_word.xpos[:2] == 'NN'):
                    obj_words.append(word.id)
                elif (word.deprel[:4] == 'conj') and (head_word.deprel[:3] == 'obl'):
                    obl_words.append(word.id)
                elif word.deprel[:8] == 'compound':
                    compound_words.append(word.id)

            # nsubj and verb are children of the object
            # only executes if be verb was found ...
            for vbid in vb_groupings.keys():
                vbhead = words[int(vbid) - 1].head
                if str(vbhead) in obj_words:
                    vb_groupings[str(vbid)]['obj'][str(vbhead)] = words[int(vbhead) - 1].text
                    for nsid in nsubj_words:
                        nshead = words[int(nsid) - 1].head
                        if nshead == vbhead:
                            vb_groupings[str(vbid)]['nsubj'][nsid] = words[int(nsid) - 1].text
            # nsubj and obj are children of verb
            for nsid in nsubj_words:
                nshead = words[int(nsid) - 1].head
                if str(nshead) in vb_groupings.keys():
                    vb_groupings[str(nshead)]['nsubj'][nsid] = words[int(nsid) - 1].text
            for oblid in obl_words:
                oblhead = words[int(oblid) - 1].head
                if str(oblhead) in vb_groupings.keys():
                    vb_groupings[str(oblhead)]['obl'][oblid] = words[int(oblid) - 1].text
            # conj
            # of obj
            for objid in obj_words:
                word = words[int(objid) - 1]
                if word.deprel[:4] == 'conj':
                    objhead = word.head
                    for vb in vb_groupings.keys():
                        if 'obj' in vb_groupings[vb] and str(objhead) in vb_groupings[vb]['obj'].keys():
                            vb_groupings[vb]['obj'][str(objid)] = word.text
            # of obl
            for oblid in obl_words:
                word = words[int(oblid) - 1]
                if word.deprel[:4] == 'conj':
                    oblhead = word.head
                    for vb in vb_groupings.keys():
                        if str(oblhead) in vb_groupings[vb]['obl'].keys():
                            vb_groupings[vb]['obl'][str(oblid)] = word.text
            # of nsubj
            for nsid in nsubj_words:
                word = words[int(nsid) - 1]
                if word.deprel[:4] == 'conj':
                    nshead = word.head
                    for vb in vb_groupings.keys():
                        if str(nshead) in vb_groupings[vb]['nsubj'].keys():
                            vb_groupings[vb]['nsubj'][str(nsid)] = word.text

            # compound loop
            skip_comp = []
            for compid in compound_words:
                temp_compid = compid
                if not temp_compid in skip_comp:
                    word = words[int(temp_compid) - 1]
                    comphead = word.head
                    comp_text = ''
                    while str(comphead) in compound_words:
                        skip_comp.append(str(comphead))
                        comp_text = (comp_text + ' ' + word.text).strip()
                        temp_compid = str(comphead)
                        word = words[int(temp_compid) - 1]
                        comphead = word.head
                        # infinite loop?
                        if str(comphead) == temp_compid:
                            print('infinite loop', temp_compid)
                            break
                    comp_text = (comp_text + ' ' + word.text).strip()
                    if str(comphead) in nsubj_words:
                        for vb in vb_groupings.keys():
                            if str(comphead) in vb_groupings[vb]['nsubj'].keys():
                                vb_groupings[vb]['nsubj'][str(comphead)] = \
                                        comp_text + ' ' +vb_groupings[vb]['nsubj'][str(comphead)]
                    if str(comphead) in obj_words:
                        for vb in vb_groupings.keys():
                            if str(comphead) in vb_groupings[vb]['obj'].keys():
                                vb_groupings[vb]['obj'][str(comphead)] = \
                                        comp_text + ' ' +vb_groupings[vb]['obj'][str(comphead)]
                    if str(comphead) in obl_words:
                        for vb in vb_groupings.keys():
                            if str(comphead) in vb_groupings[vb]['obl'].keys():
                                vb_groupings[vb]['obl'][str(comphead)] = \
                                        comp_text + ' ' +vb_groupings[vb]['obl'][str(comphead)]

            # drop verbs that are missing nsubj or obj/obl
            vb_copy = {}
            for vbid, vbgrp in vb_groupings.items():
                if (vbgrp['nsubj'] != {}) and \
                    ((vbgrp['obj'] != {}) or \
                     (vbgrp['obl'] != {})):

                    vb_copy[vbid] = vbgrp

                    if (vbgrp['obl'] == {}):
                        del vb_copy[vbid]['obl']

                    if (vbgrp['obj'] == {}):
                        del vb_copy[vbid]['obj']

            for vb, nsubj_words_vb in vb_copy.items():
                if not found:
                    for subj_id, subj in nsubj_words_vb['nsubj'].items():
                        if not found and (subj.lower() == term.lower()):
                            self.nsubj = term.lower()
                            found = True
        return found
    
    def count_noun_groups(self):
        """Count all of the noun groups on a page, and sort them in descending order

        Update the self.noun_group_count Pandas dataframe with the following columns:
            noun_group : string, unique noun group occurring in the document containing the desired
                         term
            count      : integer, number of occurrences in the document
            type       : string - 'single', 'adjectival', or 'multiple' meaning
                            + single     : one or more nouns (no other parts of speech present)
                            + adjectival : a single modified by one or more leading adjectives
                            + multiple   : two or more singles or adjectivals combined
                                           with adpositions
        """
        
        self.noun_group_count = self.noun_groups.count_noun_groups()
        
        return self.noun_group_count.copy()

class NounGroup:
    """Record information for a noun group (i.e., adj + noun + adposition groups of words).

    A class to hold information about a noun group. Noun groups are groups of 
    nouns, adjectives and adpositions; noun groups are the common language of
    technical concepts in the sciences and engineering. Noun groups and their
    relationships to other noun groups can be used to generate knowledge graphs 
    of scientific concepts and how they relate to each other.

    Attributes:
        ng:               A dictionary with keys being the noun groups
                          and values being dictionaries holding parsed information about
                          the groups. The general format of the key, value pairs is:
                          
                          { noun_group : 
                                { 'pos_seq'  : [...], 
                                  'lemma_seq': [...], 
                                  'type'     : 'xxx',
                                
                                  *'components': 
                                      { noun_group : 
                                          ... }, *
                                  *'has_type': 
                                      { noun_group : 
                                         { ... }, }, *
                                  *'has_attribute': 
                                      { adjective: 
                                         { ... }, }, *
                                 },                                            
                          }
                          
                          where the mandatory components are
                          
                          - noun_group: a noun group
                          - pos_seq: a list of the part of speech of each word in the noun
                                     group with the options being 'NOUN', 'ADJECTIVE', 
                                     'ADPOSITION'
                          - lemma_seq: a list of the root word for each word in the noun group
                                       known as the word's 'lemma' in Stanza
                          - type: indicates the type of the noun group with the options being
                                      + noun - single word, noun
                                      + noungrp - nouns only, more than one word
                                      + modnoun - noungrp modified by leading adjective(s)
                                      + modnoungrp - noungrp that has a non-leading adjective
                                                      inside the noungrp
                                      + compound - noun groups (any of the previous) connected 
                                                  with adpositions
                          - adjective: an adjective (single word)
                          
                          and the optional (*) components are
                          
                          - components: a compound noun group (type) can be broken down into atomistic
                                       noun groups separated by adpositions; these noun groups
                                       are the components
                          - has_type:  a mod_noun can be broken down into a set of adjectives
                                       and a root noungrp or noun; the latter is its 'has_type'
                          - has_attribute: the adjectives (attributes) of a mod_noun, stored as
                                       a dictionary
                                       
        noun_group_count: A Pandas DataFrame object containing the columns
                          noun_group, count, type that contain the following information:
                          - noun_group: unique noun groups occurring in the NounGroup
                          - count: number of occurrences in the NounGroup
                          - type: single, adjectival, or multiple meaning
                              + single: one or more nouns (no other parts of speech present)
                              + adjectival: a single modified by one or more leading adjectives
                              + multiple: two or more singles or adjectivals combined
                                          with adpositions
        
    """
    
    def __init__(self, words = None):
        """
        Intialize NounGroup with the words provided, if present.
        The words variable correspond to the list of parsed words generated
        by the Stanza parser for a sentence.
        """
        self.ng = {}
        self.noun_group_count = None
        if not words is None:
            self.parse_noun_groups(words)
    
    def parse_noun_groups(self, words):
        """Extract a word cluster by part of speech sequence in a larger parsed string.
        
        Algorithm:
            Find word clusters in a sentences as defined in Justetson, 1995, with a few
            modifications. Word clusters that are only found once are also considered.
            Valid noun groups satisfy the following:
                - end in a noun
                - contain only nouns, adjectives and adpositions
                - an adjective, if present, must always be followed by a noun
                - single nouns occuring between adpositions are not considered 
                  significant
        
        Args:
            words   : A list of words with their associated part of speech and other linguistic
                      information as determined by Stanza tool.
            
        Populate self.ng with a dictionary of valid noun_groups and their properties.
            
        """
        # group start marks the beginning of a mix of NOUN-ADJECTIVE-ADPOSITION cluster
        group_start = False
        # string to store the current word grouping
        current_word = ''
        # list to store the current POS sequence
        pos_sequence = []
        lemma_sequence = []

        # loop through sentence words backwards (start group at noun only)
        for word in reversed(words):
            is_noun = word.upos == 'NOUN'
            is_adj  = word.upos == 'ADJ'
            is_adp  = word.upos == 'ADP'
            
            # only define the start of the group if you hit a root noun
            if is_noun and not group_start:
                group_start = True
                current_word = word.text
                pos_sequence = ['NOUN']
                lemma_sequence = [word.lemma]
                
            # finding a noun adds it to the group (append in front, since moving in reverse)
            elif is_noun and group_start:
                current_word = word.text + ' ' + current_word
                pos_sequence = ['NOUN'] + pos_sequence
                lemma_sequence = [word.lemma] + lemma_sequence
                
            # finding an adjective adds it to the group
            elif is_adj and group_start and (pos_sequence[0] != 'ADPOSITION'):
                current_word = word.text + ' ' + current_word
                pos_sequence = ['ADJECTIVE'] + pos_sequence
                lemma_sequence = [word.lemma] + lemma_sequence
                
            # finding an adposition (preposition or postposition) adds it to the group
            elif is_adp and group_start:
                current_word = word.text + ' ' + current_word
                pos_sequence = ['ADPOSITION'] + pos_sequence
                lemma_sequence = [word.lemma] + lemma_sequence
                
            # if the previous patterns are not satisfied, then we have reached the end
            # (or rather beginning) of the word group
            else:
                # reset group start flag
                group_start = False
                # is the current word non-empty?
                if current_word != '':
                    # check that the word cluster is valid (e.g., that it doesn't have
                    # an adposition/adjective grouping to start)
                    self.add_word_cluster(current_word, pos_sequence, lemma_sequence)
                    pos_sequence = []    
                    current_word = ''
        # add the last word cluster
        if current_word != '':
            self.add_word_cluster(current_word, pos_sequence, lemma_sequence)
    
    def add_word_cluster(self, current_word, pos_sequence, lemma_sequence):
        """Add a word cluster to the set of noun groups.
        
        Algorithm:
            If the word cluster contains a leading ADPOSITION or ADJECTIVE without a NOUN
            before an ADPOSITION, then these are stripped from the word cluster.
            If there are any remaining terms, they are added to the noun group dict.
        
        Args:
            current_word   : An string containing the extracted word cluster that contains only nouns,
                             adjectives and adpositions.
            pos_sequence   : A list, the part of speech sequence corresponding to the individual
                             words in the ngroup. Valid values are 'NOUN', 'ADJECTIVE', 'ADPOSITION'
            lemma_sequence : A list, the lemma sequence corresponding to the individual
                             words in the ngroup. These correspond to the lemmas ided by Stanza.
            
        Sets the value of self.ng[modified current_word].
            
        """
        
        def extract_type(node_name, pos_seq, lemma_seq):
            """Determine the type of a noun group.
            
            Args:
                node_name : An string containing the extracted noun group that contains only nouns,
                            adjectives and adpositions.
                pos_seq   : A list, the part of speech sequence corresponding to the individual
                            words in the ngroup. Valid values are 'NOUN', 'ADJECTIVE', 'ADPOSITION'
                lemma_seq : A list, the lemma sequence corresponding to the individual
                            words in the ngroup. These correspond to the lemmas ided by Stanza.
                
            Returns:
                A list with three elements: [node_contain, node_attribute, typ]
                node_contain   : a dict of the form 
                                    {node_type: {'pos_seq': pos, 'lemma_seq': lemma, 'type': 'xxx'}}
                                 where
                                 node_type is the "type" of node_name, the root grouping of nouns 
                                 occuring at the end of node_name if node_name has typ 'modnoungrp'
                node_attribute : a dict of the form
                                 {attrX: {'pos_seq': {['ADJECTIVE'], 'lemma_seq': lemma, 'type': 'xxx' }}
                                 where
                                 attrX is one or more adjectives modifying of node_name, if node_name has
                                 typ 'modnoungrp'
                                 an adposition
                typ            : a string indicating the type of the noun group based on its pos_seq:
                                    + compound   - noun groups connected by adpositions
                                    + modnoungrp - noun adj noun grouping
                                    + modnoun    - adj noun grouping
                                    + noungrp    - nouns only, more than one noun
                                    + noun       - single noun
            """
            
            node_type = node_name
            lemma = ' '.join(lemma_seq)
            i  = 0
            if 'ADPOSITION' in pos_seq:
                typ = 'compound'
            elif 'NOUN ADJECTIVE' in ' '.join(pos_seq):
                typ = 'modnoungrp'
            elif 'NOUN' in pos_seq and 'ADJECTIVE' in pos_seq:
                typ = 'modnoun'
            elif 'ADJECTIVE' in pos_seq:
                typ = 'adj'
            elif len(pos_seq) > 1:
                typ = 'noungrp'
            else:
                typ = 'noun'
            #print(node_name, pos_seq)
            if not 'ADPOSITION' in pos_seq and 'NOUN' in pos_seq:
                while (pos_seq[i] != 'NOUN') and i < len(pos_seq):
                    i = i + 1
                if i < len(pos_seq):
                    node_type = ' '.join(node_name.split()[i:])
                    lemma = lemma_seq[i:]
                    pos = pos_seq[i:]
                    node_attr = node_name.split()[:i]
                    lemma_attr = lemma_seq[:i]
            node_contain = {}
            node_attribute = {}
            if node_type != node_name:
                node_contain = {node_type: {'pos_seq': pos, 'lemma_seq': lemma, 
                                            'type': 'noun' if (len(lemma)==1) else 'noungrp'}}
                i = 0
                for attr in node_attr:
                    node_attribute[attr] = {'pos_seq': ['ADJECTIVE'], 'lemma_seq': [lemma_attr[i]],
                                        'type': 'adj'}
                    i+=1
            return [node_contain, node_attribute, typ]
        
        # is this a valid grouping to add to the word groups?
        # if it starts with an adposition then it should be dropped
        start_index = 0
        i = 0
        while (pos_sequence[i] != 'NOUN') and (i < len(pos_sequence)):
            if pos_sequence[i] == 'ADPOSITION':
                start_index = i + 1
            i += 1

        # add noun group to the dictionary if non-empty
        current_word = ' '.join(current_word.split(' ')[start_index:])
        pos_sequence = pos_sequence[start_index:]
        lemma_sequence = lemma_sequence[start_index:]

        if current_word != '':
            self.ng[current_word] = {'pos_seq':pos_sequence, 'lemma_seq':lemma_sequence}

            [node_contain, node_attr, typ] = extract_type(current_word, pos_sequence, lemma_sequence)
            self.ng[current_word]['type'] = typ
            if node_contain != {}:
                self.ng[current_word]['has_type'] = node_contain
            if node_attr != {}:
                self.ng[current_word]['has_attribute'] = node_attr
        # decompose noun group along adposition
        self.decompose_noun_group(current_word, pos_sequence, lemma_sequence)

    def decompose_noun_group(self, ngroup, pos, lemma):
        """Decompose a noun group into its simple (adposition separated) noun group
        
        Algorithm:
            Break up noun group at each adposition in component adpostion. If the division
            of a noun group at both ends by an adposition results in a single word term, 
            it is discarded. This is intended to drop patterns such as in regards to, 
            but it may be worth while to reconsider this design decision and hard code
            ADP NOUN ADP patterns known to occur frequently.
        
        Args:
            ngroup : An string containing the extracted noun group that contains only nouns,
                     adjectives and adpositions.
            pos    : A list, the part of speech sequence corresponding to the individual
                     words in the ngroup. Valid values are 'NOUN', 'ADJECTIVE', 'ADPOSITION'
            lemma  : A list, the lemma sequence corresponding to the individual
                     words in the ngroup. These correspond to the lemmas ided by Stanza.
            
        Sets the value of self.ng[ngroup]['components'].
            
        """
        
        def find_sequence(lst, seq):
            """Find all occurences of a sequence of string elements in a list of elements.
            
            Args:
                lst : The list of strings to search.
                seq : The list of terms, in the desired sequence, to search for inside lst.
                
            Returns:
                A list of indexes in lst, each one indicating the start of the sequence seq
                in lst. There is one index per occurence of seq.
            """
            index_seq = []
            for i in range(len(lst)):
                j = i
                sj = 0
                while (sj < len(seq)) and (j < len(lst)) and (lst[j]==seq[sj]):
                    j = j + 1
                    sj = sj + 1
                if sj == len(seq):
                    index_seq.append(i)
            return index_seq

        def extract_type(node_name, pos_seq, lemma_seq):
            """Determine the type of a noun group.
            
            Args:
                node_name : An string containing the extracted noun group that contains only nouns,
                            adjectives and adpositions.
                pos_seq   : A list, the part of speech sequence corresponding to the individual
                            words in the ngroup. Valid values are 'NOUN', 'ADJECTIVE', 'ADPOSITION'
                lemma_seq : A list, the lemma sequence corresponding to the individual
                            words in the ngroup. These correspond to the lemmas ided by Stanza.
                
            Returns:
                A list with three elements: [node_contain, node_attribute, typ]
                node_contain   : a dict of the form 
                                    {node_type: {'pos_seq': pos, 'lemma_seq': lemma, 'type': 'xxx'}}
                                 where
                                 node_type is the "type" of node_name, the root grouping of nouns 
                                 occuring at the end of node_name if node_name has typ 'modnoungrp'
                node_attribute : a dict of the form
                                 {attrX: {'pos_seq': {['ADJECTIVE'], 'lemma_seq': lemma, 'type': 'xxx' }}
                                 where
                                 attrX is one or more adjectives modifying of node_name, if node_name has
                                 typ 'modnoungrp'
                                 an adposition
                typ            : a string indicating the type of the noun group based on its pos_seq:
                                    + compound   - noun groups connected by adpositions
                                    + modnoungrp - noun adj noun grouping
                                    + modnoun    - adj noun grouping
                                    + noungrp    - nouns only, more than one noun
                                    + noun       - single noun
            """
            
            node_type = node_name
            lemma = ' '.join(lemma_seq)
            i  = 0
            if 'ADPOSITION' in pos_seq:
                typ = 'compound'
            elif 'NOUN ADJECTIVE' in ' '.join(pos_seq):
                typ = 'modnoungrp'
            elif 'NOUN' in pos_seq and 'ADJECTIVE' in pos_seq:
                typ = 'modnoun'
            elif 'ADJECTIVE' in pos_seq:
                typ = 'adj'
            elif len(pos_seq) > 1:
                typ = 'noungrp'
            else:
                typ = 'noun'
            #print(node_name, pos_seq)
            if not 'ADPOSITION' in pos_seq and 'NOUN' in pos_seq:
                while (pos_seq[i] != 'NOUN') and i < len(pos_seq):
                    i = i + 1
                if i < len(pos_seq):
                    node_type = ' '.join(node_name.split()[i:])
                    lemma = lemma_seq[i:]
                    pos = pos_seq[i:]
                    node_attr = node_name.split()[:i]
                    lemma_attr = lemma_seq[:i]
            node_contain = {}
            node_attribute = {}
            if node_type != node_name:
                node_contain = {node_type: {'pos_seq': pos, 'lemma_seq': lemma, 
                                            'type': 'noun' if (len(lemma)==1) else 'noungrp'}}
                i = 0
                for attr in node_attr:
                    node_attribute[attr] = {'pos_seq': ['ADJECTIVE'], 'lemma_seq': [lemma_attr[i]],
                                        'type': 'adj'}
                    i+=1
            return [node_contain, node_attribute, typ]
    
        adp_loc = find_sequence(pos, ['ADPOSITION'])
        adpnadp_loc = find_sequence(pos, ['ADPOSITION','NOUN','ADPOSITION'])

        
        start_i = 0
        groups = {}
        if not (adp_loc == []):
            for adp in adp_loc:
                if not start_i in adpnadp_loc and not start_i in adp_loc and (start_i < adp):
                    w = ' '.join(ngroup.split()[start_i:adp])
                    ps = pos[start_i:adp]
                    ls = lemma[start_i:adp]
                    [node_contain, node_attr, typ] = extract_type(w, ps, ls)
                    groups[w]={'pos_seq':ps, 'lemma_seq':ls, 'type':typ}
                    if node_contain != {}:
                        groups[w]['has_type'] = node_contain
                    if node_attr != {}:
                        groups[w]['has_attribute'] = node_attr
                    start_i = adp + 1
                if adp in adpnadp_loc:
                    start_i = adp + 3
                else:
                    start_i = adp + 1
            # add the last group
            if start_i < len(ngroup.split()):
                w = ' '.join(ngroup.split()[start_i:])
                ps = pos[start_i:]
                ls = lemma[start_i:]
                typ = extract_type(w, ps, ls)
                [node_contain, node_attr, typ] = extract_type(w, ps, ls)
                groups[w]={'pos_seq':ps, 'lemma_seq':ls, 'type':typ}
                if node_contain != {}:
                    groups[w]['has_type'] = node_contain
                if node_attr != {}:
                    groups[w]['has_attribute'] = node_attr
        if groups != {}:
            self.ng[ngroup]['components'] = groups

    
    def count_noun_groups(self):
        """Count all of the noun groups in a NounGroup set, and sort them in descending order

        Update the self.noun_group_count
        
        Returns:
            A Pandas DataFrame (also stored in self.noun_group_count) with the following columns.
            noun_group : string, unique noun group occurring in the document containing the desired
                         term
            count      : integer, number of occurrences in the document
            type       : string - 'single', 'adjectival', or 'multiple' meaning
                            + single     : one or more nouns (no other parts of speech present)
                            + adjectival : a single modified by one or more leading adjectives
                            + multiple   : two or more singles or adjectivals combined
                                           with adpositions
                                           
        Note:
            This function needs to be compressed down as it has repeating code elements.
        """
        
        def assign_ng_type(noun_group, noun_group_count):
            name = noun_group.lower()
            if all([(x.isalnum() or x.isspace()) for x in noun_group]):
                if name in noun_group_count.keys():
                    noun_group_count[name]['count'] += 1
                else:
                    noun_group_count[name] = {}
                    noun_group_count[name]['count'] = 1
                    noun_group_count[name]['pos_seq'] = \
                                    'multiple' if 'ADPOSITION' in attr['pos_seq'] else \
                                    'adjectival' if 'ADJECTIVE' in attr['pos_seq'] else \
                                    'simple'
            return noun_group_count
        
        if self.noun_group_count is None:
            noun_group_count = {}
            for noun_group, attr in self.ng.items():
                noun_group_count = assign_ng_type(noun_group, noun_group_count)
                if 'components' in attr.keys():
                    for noun_group_comp, attr_comp in attr['components'].items():
                        noun_group_count = assign_ng_type(noun_group_comp, noun_group_count)

            self.noun_group_count = pd.DataFrame(columns = ['noun_group', 'count', 'type'])
            for group in noun_group_count.keys():
                self.noun_group_count.loc[len(self.noun_group_count)] = \
                                        [group, noun_group_count[group]['count'], \
                                         noun_group_count[group]['pos_seq']]

            self.noun_group_count = self.noun_group_count.sort_values(by=['count', 'noun_group'], \
                                                                      ascending = [False, True])
        
        return self.noun_group_count.copy()


