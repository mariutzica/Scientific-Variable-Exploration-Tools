import pandas as pd

ext = 'wiktiwordnet/'
attr = pd.read_csv(ext + 'attributes.csv', usecols = ['term', 'pos', 'definition'])
body = pd.read_csv(ext + 'body.csv', usecols = ['term', 'pos', 'definition'])
domain = pd.read_csv(ext + 'domains.csv', usecols = ['term', 'pos', 'definition'])
matter = pd.read_csv(ext + 'matter.csv', usecols = ['term', 'pos', 'definition'])
meas = pd.read_csv(ext + 'measures.csv', usecols = ['term', 'pos', 'definition'])
phen = pd.read_csv(ext + 'phenomenon.csv', usecols = ['term', 'pos', 'definition'])
proc = pd.read_csv(ext + 'processes.csv', usecols = ['term', 'pos', 'definition'])
prop = pd.read_csv(ext + 'properties.csv', usecols = ['term', 'pos', 'definition'])
role = pd.read_csv(ext + 'roles.csv', usecols = ['term', 'pos', 'definition'])
units = pd.read_csv(ext + 'units.csv', usecols = ['term', 'pos', 'definition'])

def check_domain(term):
    found = False
    definition = ''
    if term in domain['term'].tolist():
        found = True
        definition = domain.loc[domain['term']==term,'definition']
        
    return [found, definition]

def get_category(term):
    category = {}
    if term in domain['term'].tolist():
        definition = domain.loc[domain['term']==term,'definition'].iloc[0]
        category['Domain'] = definition
    if term in matter.loc[matter['pos']=='Noun','term'].tolist():
        definition = matter.loc[matter['term']==term,'definition'].iloc[0]
        category['Matter'] = definition
    if term in proc.loc[proc['pos']=='Noun','term'].tolist():
        definition = proc.loc[proc['term']==term,'definition'].iloc[0]
        category['Process'] = definition
    if term in attr.loc[attr['pos']=='Noun','term'].tolist():
        definition = attr.loc[attr['term']==term,'definition'].iloc[0]
        category['Attribute'] = definition
    if term in prop.loc[prop['pos']=='Noun','term'].tolist():
        definition = prop.loc[prop['term']==term,'definition'].iloc[0]
        category['Property'] = definition
    if term in body.loc[body['pos']=='Noun','term'].tolist():
        definition = body.loc[body['term']==term,'definition'].iloc[0]
        category['Body'] = definition
    if term in role.loc[role['pos']=='Noun','term'].tolist():
        definition = role.loc[role['term']==term,'definition'].iloc[0]
        category['Role'] = definition

    return category