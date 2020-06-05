import requests
from lxml import html

# return the id and title of the top wikipedia page related to a term
# output is in the form of a dictionary; 
# the keys 'pageid', 'title', 'redirecttitle', and 'sectiontitle' provide the
# values returned by the wikipedia api
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
    
    # select the desired result based on the title or the redirecttitle or sectiontitle of the page
    # exact match returns one of these, no match returns the top (0th) entry
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

        result_index = 0
        if term.lower() in result_titles:
            result_index = result_titles.index(term.lower())
        elif term.lower() in redirect_titles:
            result_index = redirect_titles.index(term.lower())
        elif term.lower() in section_titles:
            result_index = section_titles.index(term.lower())

        result = DATA['query']['search'][result_index]
        
    return result

# parse the bulk text from the wikipedia page desired 
# (identified by id returned by get_top_wikipedia_entry)
# returns
# - result: a list of the lines of text on the page
# - disambig: Boolean indicating if the page is a disambugation page
def parse_wikipedia_page(pageid):
    S = requests.Session()
    URL = "https://en.wikipedia.org/w/api.php"
    PARAMS = {
            'action': "parse",
            'pageid': pageid,
            'format': "json"
        }

    f = open('output/pageid_error.log','w')
    result = ''
    disambig = False
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
                
        else:
            all_elem = tree.xpath('//div[@class="mw-parser-output"]//li//text()')
            result = '\n'.join(all_elem)
    except:
        f.write(str(pageid) + ' text parse error')
    f.close()

    result = result.split('\n')
                
    return [result, disambig]

# read text from top Wikipedia result, return cleaned text
# this function is a pretty wrapper around the parse_wikipedia_page and
# get_wikipedia_text functions
# it returns the following:
#  - text_clean : a list of paragraphs on the page
#  - disambig : boolean indicating if the page is a disambiguation page
#  - title, redirecttitle: the title and redirect of the page
#  - currently not using section title
def get_wikipedia_text(term):
    
    title = ''
    redirecttitle = ''
    term = term.strip('"')
    disambig = False
    text_clean = []
    
    # get information about the top matching result to our query
    wikipedia_top_result = get_top_wikipedia_entry(term)
    if 'pageid' in wikipedia_top_result.keys():
            
        # use the page id to get the text on the page
        pageid = wikipedia_top_result['pageid']
        [page_text, disambig_text] = parse_wikipedia_page(pageid)
            
        # get the tile of the page and any redirect
        if 'title' in wikipedia_top_result.keys():
            title = wikipedia_top_result['title'].lower()
        if 'redirecttitle' in wikipedia_top_result.keys():
            redirecttitle = wikipedia_top_result['redirecttitle'].lower()
            
        # simple text cleaning: remove empty lines and strip whitespace from ends.
        # each line contains a different paragraph
        text_clean = [x.strip() for x in page_text if x!='']
        # translate disambiguation flag
        disambig = False if disambig_text == [] else True
    
    return [text_clean, disambig, title, redirecttitle]