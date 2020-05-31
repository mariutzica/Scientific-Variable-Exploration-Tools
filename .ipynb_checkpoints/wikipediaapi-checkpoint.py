import requests
from lxml import html

def get_top_wikipedia_entry(term):
    
    S = requests.Session()
    URL = "https://en.wikipedia.org/w/api.php"
    TITLE = ' '.join(term.split())
    PARAMS = {
            'action': "query",
            'srsearch': TITLE,
            'format': "json",
            'list':"search",
            'srwhat':"text",
            'srsort':"relevance",
            'srlimit': 5,
            'srprop': 'redirecttitle|sectiontitle',
        }

    R = S.get(url=URL, params=PARAMS)
    DATA = R.json()

    #top_result_title = ''
    #top_result_pageid = -1

    #for result in DATA['query']['search']:
    #    if 'redirecttitle' in result.keys():
    #        print(result['redirecttitle'])
                           
    result = {}
    num_results = len(DATA['query']['search'])
    if num_results > 0:
        result_titles = [result['title'].lower() for result in DATA['query']['search']]
        redirect_titles = [result['redirecttitle'].lower() \
                           if 'redirecttitle' in result.keys() else '' \
                           for result in DATA['query']['search'] ]
        section_titles = [result['sectiontitle'].lower().replace('_',' ') \
                          if 'sectiontitle' in result.keys() else '' \
                          for result in DATA['query']['search'] ]

        #print(result_titles)
        #print(redirect_titles)
        #print(section_titles)
        #print(term)
        result_index = 0
        if term.lower() in result_titles:
            result_index = result_titles.index(term.lower())
            #print('result')
        elif term.lower() in redirect_titles:
            result_index = redirect_titles.index(term.lower())
            #print('redirect')
        elif term.lower() in section_titles:
            result_index = section_titles.index(term.lower())
            #print('section')

        
        #top_result = DATA['query']['search'][desired_result]
        #top_result_title = DATA['query']['search'][result_index]['title']
        #top_result_pageid = DATA['query']['search'][result_index]['pageid']
        result = DATA['query']['search'][result_index]
        
    return result
        
def parse_wikipedia_page(pageid):
    S = requests.Session()
    URL = "https://en.wikipedia.org/w/api.php"
    PARAMS = {
            'action': "parse",
            'pageid': pageid,
            'format': "json"
        }

    pos = []
    defs = []
    nyms = []
    f = open('pageid_error.log','w')
    result = ''
    try:
        R = S.get(url=URL, params=PARAMS)
        DATA = R.json()
        tree = html.fromstring(DATA['parse']['text']['*'])
        
        # determine whether this is a disambiguation page
        try:
            disambig = tree.xpath('*[@id="disambigbox"]//text()')
        except:
            f.write(pageid + ' disambig error')
            
        # get information from the page. For now, only paragraph information is extracted.
        # mw-parser-output is the div that contains all of the human-readable content of the
        # Wikipedia page
        if not disambig:
            all_elem = tree.xpath('//div[@class="mw-parser-output"]//p//text()')
            result = ''.join(all_elem)
        
        # code for extracting the 'see also' box from the top
        #try:
        #    seealso = tree.xpath('(//div[contains(@class, "hatnote") and contains(@class, "navigation-not-searchable")])[1]//text()')
            #print(seealso)
        #    seealso = ''.join(seealso)
        #except:
        #    print('Error header parse.')
        
        else:
            all_elem = tree.xpath('//div[@class="mw-parser-output"]//li//text()')
            result = '\n'.join(all_elem)
    except:
        f.write(pageid + ' text parse error')
    f.close()

    result = result.split('\n')
    
    # code for extracting the 'see also' box from the top
    #i = 0
    #seealso = seealso.split('\n')
    #start_part = True
    #while start_part and i<len(result):
    #    if result[i] != seealso[0]:
    #        i = i + 1
    #    else:
    #        start_part = False
    #j = 0
    #while (j<len(seealso)) and (seealso[j] == result[i]):
    #    #print('Removed: ',seealso[i:i+len(result[0])])
    #    j = j + 1
    #    result = result[:i] + result[i+1:]
    #seealso = '\n'.join(seealso)    
            
    return [result, disambig]

# read text from top Wikipedia result, return cleaned text
def get_wikipedia_text(state):
    
    title = ''
    redirecttitle = ''
    term = state.strip('"')
    disambig = False
    text_clean = []
    
    # get information about the top matching result to our query
    wikipedia_top_result = get_top_wikipedia_entry(state)
    #print(wikipedia_top_result.keys())
    if len(wikipedia_top_result) > 0:
        if 'pageid' in wikipedia_top_result.keys():
            
            # use the page id to get the text on the page
            pageid = wikipedia_top_result['pageid']
            [page_text, disambig_text] = parse_wikipedia_page(pageid)
            
            # get the tile of the page and any redirect
            if 'title' in wikipedia_top_result.keys():
                title = wikipedia_top_result['title'].lower()
            if 'redirecttitle' in wikipedia_top_result.keys():
                redirecttitle = wikipedia_top_result['redirecttitle'].lower()
            #print(pageid)
            #page_text = page_text.lower()
            
            # simple text cleaning: remove empty lines and strip whitespace from ends.
            # each line contains a different paragraph
            text_clean = [x.strip() for x in page_text if x!='']
            # translate disambiguation flag
            disambig = False if disambig_text == [] else True
    
    return [text_clean, disambig, title, redirecttitle]