import stanza
import pandas as pd
#stanza.download('en')
nlp = stanza.Pipeline('en')
# usage:
# doc = nlp(sentence)
# doc.sentences : iterator
# doc.sentences[0].words : iterator

# extract noun groups in a paragraph
def parse_noun_groups(text):
    sentence_no = 1
    noun_groups = {}
    if text != '':
        doc = nlp(text)
        for sentence in doc.sentences:
            noun_groups[sentence_no] = find_noun_adj_groups(sentence)
            sentence_no += 1
        
    return noun_groups

# extract noun groups on a page
def parse_page_noun_groups(text):
    paragraph_no = 1
    noun_groups = {}
    for paragraph in text:
        noun_groups[paragraph_no] = parse_noun_groups(paragraph)
        paragraph_no += 1
        
    return noun_groups

# count noun groups on a page
#def page_count_noun_groups(parsed_page)
# Function to find noun groups as defined in Justetson, 1995 + single nouns 
# - not restricted to 2x occurences
def find_noun_adj_groups(sentence):
                
    # group start marks the beginning of a mix of NOUN-ADJECTIVE-ADPOSITION cluster
    group_start = False
    # groups stores all of the noun groups found in a sentence
    groups = {}
    # string to store the current word grouping
    current_word = ''
    # list to store the current POS sequence
    pos_sequence = []
    lemma_sequence = []
    
    # loop through sentence words backwards (start group at noun only)
    for word in reversed(sentence.words):
        
        # only define the start of the group if you hit a root noun
        if (word.upos == 'NOUN') and not group_start:
            group_start = True
            current_word = word.text
            pos_sequence = ['NOUN']
            lemma_sequence = [word.lemma]
        # finding a noun adds it to the group (append in front, since moving in reverse)
        elif (word.upos == 'NOUN') and group_start:
            current_word = word.text + ' ' + current_word
            pos_sequence = ['NOUN'] + pos_sequence
            lemma_sequence = [word.lemma] + lemma_sequence
        # finding an adjective adds it to the group
        elif (word.upos == 'ADJ') and group_start and (pos_sequence[0] == 'NOUN'):
            current_word = word.text + ' ' + current_word
            pos_sequence = ['ADJECTIVE'] + pos_sequence
            lemma_sequence = [word.lemma] + lemma_sequence
        # finding an adposition (preposition or postposition) adds it to the group
        elif (word.upos == 'ADP') and group_start:
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
                groups = add_word_cluster(current_word, pos_sequence, lemma_sequence, groups)
                pos_sequence = []    
                current_word = ''
    # add the last word cluster
    if current_word != '':
        groups = add_word_cluster(current_word, pos_sequence, lemma_sequence, groups)        
    return groups    


def add_word_cluster(current_word, pos_sequence, lemma_sequence, groups):

    # is this a valid grouping to add to the word groups?
    # if it starts with an adposition then it should be dropped
    while (pos_sequence[0] == 'ADPOSITION'):
        current_word = current_word.split(' ',1)[1]
        pos_sequence = pos_sequence[1:]
        lemma_sequence = lemma_sequence[1:]
    
    if current_word != '':
        groups[current_word] = {'pos_seq':pos_sequence, 'lemma_seq':lemma_sequence}
    
    decomp = decompose_noun_group(current_word, pos_sequence, lemma_sequence)
    if decomp != {}:
        groups[current_word]['components'] = decomp
    return groups

# Function to find noun group components of a noun group
def decompose_noun_group(ngroup, pos, lemma):
    groups = {}
    adp_loc = find_sequence(pos, ['ADPOSITION'])
    adpnadp_loc = find_sequence(pos, ['ADPOSITION','NOUN','ADPOSITION'])
    #print(ngroup, adp_loc, adpnadp_loc)
    # if an adposition is found, then break up and parse at each adposition, but only
    # when adpositions are more than 2 distance apart
    # this is intended to drop patterns such as in regards to, but maybe it would
    # drop some important nouns and we need to add it back? not sure ...
    start_i = 0
    if not (adp_loc == []):
        for adp in adp_loc:
            if not start_i in adpnadp_loc and not start_i in adp_loc and (start_i < adp):
                w = ' '.join(ngroup.split()[start_i:adp])
                groups[w]={'pos_seq':pos[start_i:adp], 'lemma_seq':lemma[start_i:adp]}
                start_i = adp + 1
            if adp in adpnadp_loc:
                start_i = adp + 3
            else:
                start_i = adp + 1
        if start_i < len(ngroup.split()):
            w = ' '.join(ngroup.split()[start_i:])
            groups[w]={'pos_seq':pos[start_i:], 'lemma_seq':lemma[start_i:]}
    return groups

# Finds all start indexes of a sequence of elements in a list
def find_sequence(lst, seq):
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

# This function finds the paragraph that starts with an 'is' sentence ... and that has a matching 
# nsubj
def find_is_paragraph(text, title, use_name):
    pno = 0
    pno_ret = -1
    nsubj = ''
    found = False
    first_found = -1
    name_found = title
    while (pno < len(text))and not found:
        paragraph = text[pno]
        if title.lower() in paragraph.lower():
            if first_found == -1:
                first_found = pno
        if use_name.lower() in paragraph.lower():
            try:
                if paragraph != '':
                    doc = nlp(paragraph)
            except:
                print('Paragraph ', pno, ' generated error in stanza.')
                print(paragraph)
                pno += 1
                continue
            if not found:
                sentence = doc.sentences[0].text
                nsubj_words = find_nsubj(sentence)
                for vb in nsubj_words.keys():
                    for subj in nsubj_words[vb]['nsubj']:
                        if not found:
                            subject = nsubj_words[vb]['nsubj'][subj]
                            if (subject.lower() == use_name.lower()):
                                found = True
                                pno_ret = pno
                                nsubj = nsubj_words[vb]
                                name_found = use_name

        pno += 1
    if pno_ret == -1:
        pno_ret = first_found
    
    return [pno_ret, nsubj, name_found]    

# Find all nsubj, obj of a sentence that correspond to the verbs 'to be', 'to refer to', or 'to describe'
def find_nsubj(sentence):
    
    # use Stanza to assign part of speech and determine roles of each word in the sentence.
    doc = nlp(sentence)
    s = doc.sentences[0]
    nsubj_words = []
    obj_words = []
    obl_words = []
    vb_groupings = {}
    compound_words = []
    conj_words = []
    
    analysis = {'be_fragment':False}
       
    # loop through the words to find nsubj, obj, verb, conj, and compound
    # (there are also adjectives to take care of, and these will be extracted later)
    for word in s.words:
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
        elif (word.deprel[:4] == 'conj') and (s.words[word.head - 1].deprel[:5] == 'nsubj'):
            nsubj_words.append(word.id)
        elif (word.deprel[:4] == 'conj') and (s.words[word.head - 1].deprel[:3] == 'obj'):
            obj_words.append(word.id)
        elif (word.deprel[:4] == 'conj') and (s.words[word.head - 1].deprel == 'root') \
            and (s.words[word.head - 1].xpos[:2] == 'NN'):
            obj_words.append(word.id)
        elif (word.deprel[:4] == 'conj') and (s.words[word.head - 1].deprel[:3] == 'obl'):
            obl_words.append(word.id)
        elif word.deprel[:8] == 'compound':
            compound_words.append(word.id)
    
    # nsubj and verb are children of the object
    for vbid in vb_groupings.keys():
        vbhead = s.words[int(vbid) - 1].head
        if str(vbhead) in obj_words:
            vb_groupings[str(vbid)]['obj'][str(vbhead)] = s.words[int(vbhead) - 1].text
            for nsid in nsubj_words:
                nshead = s.words[int(nsid) - 1].head
                if nshead == vbhead:
                    vb_groupings[str(vbid)]['nsubj'][nsid] = s.words[int(nsid) - 1].text
    # nsubj and obj are children of verb
    for nsid in nsubj_words:
        nshead = s.words[int(nsid) - 1].head
        if str(nshead) in vb_groupings.keys():
            vb_groupings[str(nshead)]['nsubj'][nsid] = s.words[int(nsid) - 1].text
    for oblid in obl_words:
        oblhead = s.words[int(oblid) - 1].head
        if str(oblhead) in vb_groupings.keys():
            vb_groupings[str(oblhead)]['obl'][oblid] = s.words[int(oblid) - 1].text
    # conj
    # of obj
    for objid in obj_words:
        if s.words[int(objid) - 1].deprel[:4] == 'conj':
            objhead = s.words[int(objid) - 1].head
            for vb in vb_groupings.keys():
                if 'obj' in vb_groupings[vb] and str(objhead) in vb_groupings[vb]['obj'].keys():
                    vb_groupings[vb]['obj'][str(objid)] = s.words[int(objid) - 1].text
    # of obl
    for oblid in obl_words:
        if s.words[int(oblid) - 1].deprel[:4] == 'conj':
            oblhead = s.words[int(oblid) - 1].head
            for vb in vb_groupings.keys():
                if str(oblhead) in vb_groupings[vb]['obl'].keys():
                    vb_groupings[vb]['obl'][str(oblid)] = s.words[int(oblid) - 1].text
    # of nsubj
    for nsid in nsubj_words:
        if s.words[int(nsid) - 1].deprel[:4] == 'conj':
            nshead = s.words[int(nsid) - 1].head
            for vb in vb_groupings.keys():
                if str(nshead) in vb_groupings[vb]['nsubj'].keys():
                    vb_groupings[vb]['nsubj'][str(nsid)] = s.words[int(nsid) - 1].text
    
    # compound loop
    skip_comp = []
    for compid in compound_words:
        temp_compid = compid
        if not temp_compid in skip_comp:
            comphead = s.words[int(temp_compid) - 1].head
            comp_text = ''
            while str(comphead) in compound_words:
                skip_comp.append(temp_compid)
                comp_text = (comp_text + ' ' + s.words[int(temp_compid) - 1].text).strip()
                temp_compid = str(comphead)
                comphead = s.words[int(temp_compid) - 1].head
            comp_text = (comp_text + ' ' + s.words[int(temp_compid) - 1].text).strip()
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
    
    #print(vb_groupings)
    # drop verbs that are missing nsubj or obj/obl
    vb_copy = {}
    for vbid in vb_groupings.keys():
        if (vb_groupings[vbid]['nsubj'] != {}) and ((vb_groupings[vbid]['obj'] != {}) or (vb_groupings[vbid]['obl'] != {})):
            vb_copy[vbid] = vb_groupings[vbid]
            if (vb_groupings[vbid]['obl'] == {}):
                del vb_copy[vbid]['obl']
            if (vb_groupings[vbid]['obj'] == {}):
                del vb_copy[vbid]['obj']
    return vb_copy

def extract_type(node_name, pos_seq, lemma_seq):
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
            lemma = ' '.join(lemma_seq[i:])
    return [node_type, lemma, typ]

def count_noun_groups(parsed_page, term):
    noun_group_count = {}
    for par_no, paragraph in parsed_page.items():
        for sent_no, sentence in paragraph.items():
            for noun_group, attr in sentence.items():
                if all(x.isalnum() or x.isspace() for x in noun_group):
                    if noun_group.lower() in noun_group_count.keys():
                        noun_group_count[noun_group.lower()]['count'] += 1
                    else:
                        noun_group_count[noun_group.lower()] = {}
                        noun_group_count[noun_group.lower()]['count'] = 1
                        noun_group_count[noun_group.lower()]['pos_seq'] = \
                            'multiple' if 'ADPOSITION' in attr['pos_seq'] else \
                            'adjectival' if 'ADJECTIVE' in attr['pos_seq'] else \
                            'simple'
                    if 'components' in attr.keys():
                        for noun_group_comp, attr_comp in attr['components'].items():
                            if all(x.isalnum() or x.isspace() for x in noun_group):
                                if noun_group_comp.lower() in noun_group_count.keys():
                                    noun_group_count[noun_group_comp.lower()]['count'] += 1
                                else:
                                    noun_group_count[noun_group_comp.lower()] = {}
                                    noun_group_count[noun_group_comp.lower()]['count'] = 1
                                    noun_group_count[noun_group_comp.lower()]['pos_seq'] = \
                                        'multiple' if 'ADPOSITION' in attr_comp['pos_seq'] else \
                                        'adjectival' if 'ADJECTIVE' in attr_comp['pos_seq'] else \
                                        'simple'

    noun_groups = pd.DataFrame(columns = ['noun_group', 'count', 'type'])
    for group in noun_group_count.keys():
        noun_groups.loc[len(noun_groups)] = [group, noun_group_count[group]['count'], \
                                             noun_group_count[group]['pos_seq']]

    noun_groups = noun_groups.sort_values(by=['count', 'noun_group'], ascending = [False, True])
    
    noun_groups['modified'] = False
    noun_groups.loc[noun_groups['noun_group'].str.endswith(' '+term) & \
                    noun_groups['type'].isin(['adjectival','simple']),'modified'] = True
    noun_groups['aspects'] = False
    noun_groups.loc[noun_groups['noun_group'].str.contains(term) & \
                    ~noun_groups['noun_group'].str.endswith(' '+term) & \
                    (noun_groups['type']=='adjectival'),'aspects'] = True
    noun_groups.loc[noun_groups['noun_group'].str.contains(term) & \
                    (noun_groups['type']=='multiple'),'aspects'] = True
    return noun_groups


