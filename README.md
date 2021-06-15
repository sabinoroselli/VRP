# VRP

This project allows to generate and solve instances of the conflict-free, electric vehicle routing problem (CF-EVRP) by means of a monolithic model written for the SMT solver Z3, and an SMT-based compositional algorithm, that breaks down the problem into sub-problems and iteratively solves them to find a solution to the original CF-EVRP.

The monolithic model is coded using the Python API for Z3 and is available in the file MonoMod.py

The execution of a single instance (or a batch of instances) can be done in sequence, or in parallel by calling either MonoMod or ComSat from the file interface.py. 

The running time, optimal value, and other parameters regarding the instance are then saved in the file data_storage.txt

Instances can be made by specifying parameters such as number of nodes, vehicles, etc, through the file instance_maker.py. Based on the choice of the number of nodes (15,25 and 35) there are three possible tree structure, hard coded in the file edges_for_graphs.py 

Some instances are available in the folder test_cases for demonstration. when instances are generated they are automatically saved in the folder test_cases.

The folder "paths_containers" containes json files storing the shortest path from each node to each other node, depending on the number of nodes and the connectivity of the graph.

The files paths_changer.py, routing_multi_depot_model.py, assignment_model.py, route_checker.py, and scheduling_model.py contain the Z3 code to model the sub-problems. They are called by ComSat to solve an instance of the CF-EVRP. 

The file "routing_md_3index.py" contains an alternative formulation of the routing problem using 3 indexes for the decision variables instead of 2.

Finally, the file support_functions.py contains functions for parsing the instances, measure distance between nodes, and print data.
  
 
