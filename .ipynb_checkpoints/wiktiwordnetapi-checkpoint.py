import json

class wiktiwordnet:
    
    # data will contain the information from WiktiWordnet
    #
    # data is a structured dictionary indexed as:
    #
    # data[term][pos][[definition]]
    #
    # where term is the unique word, pos is the associated part of speech, 
    #      and [definition] is a list of string definitions associated with that
    #      term and part of speech
    
    def __init__(self, ext = 'resources/'):
        
        data = {}
        filename = ext + 'wiktiwordnet.json'
            
        try:
            with open(filename) as f:
                data = json.load(f)
        except:
            print('Error when trying to open WiktiWordNet file {}. Skipped!'\
                  .format(filename))
                        
        self.data = data
        
        
    # check WWN to see if a term has been categorized as a Domain
    # returns two elements:
    #
    # - found: True if term was found in the Domain category; False otherwise
    # - definition: the first definition of the term found under the Domain category
    def check_domain(self, term):
        
        found = False
        definition = ''
        
        if 'Domain' in self.data.keys():
            if term in self.data['Domain'].keys():
                if 'Noun' in self.data['Domain'][term].keys():
                    found = True
                    definition = self.data['Domain'][term]['Noun'][0]

        return [found, definition]

    # get all WWN categories for a term
    # returns a dictionary of {category:definition} pairs
    # 
    # assumptions:
    # - first definition is the only one returned
    # - only terms with part-of-speech == Noun are considered
    def get_category(self, term):
        
        category = {}
        
        for cat in self.data.keys():
            if term in self.data[cat].keys():
                if 'Noun' in self.data[cat][term].keys():
                    definition = self.data[cat][term]['Noun'][0]
                    category[cat] = definition

        return category