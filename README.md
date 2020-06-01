This repository contains modules for enabling Scientific Variable exploration and grounding to SVO and WM variables.

Usage:

For pretty printed output, use user_interaction document generator:

import user_interaction as ui
graph = ui.generate_document(levels = 1, load_graph = None, write_graph = False)
 - levels determines the depth to which the graph is expanded
    - the value '1' should be used for quick, rough runs
    - the value '2' should be used for higher accuracy
    - values higher than 3 are not allowed
    
 - load_graph - takes in a filename to load an existing graph into memory
 - write_graph - write resulting graph to file
 
For programmatic interaction, use knowledge_graph module:
graph = create_graph(var = '', levels = 1, graph = None, write_graph = False)
 - var is the variable text
 - levels determines the depth to which the graph is expanded
 - graph - takes in a filename to load an existing graph into memory
 - write_graph - write resulting graph to file
 
Please consult the iPython notebook for examples.
