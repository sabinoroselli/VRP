# VRP

This project allows to generate and solve instances of the Conflict-Free, Electric Vehicle Routing Problem (CF-EVRP) by means of the monolithic model MonoMod written for the SMT solver Z3, and an SMT-based compositional algorithm ComSat, that breaks down the problem into sub-problems and iteratively solves them to find a solution to the original CF-EVRP.

The monolithic model is coded using the Python API for Z3 and is available in the file MonoMod.py

The execution of a single instance (or a batch of instances) can be done in sequence, or in parallel by calling either MonoMod or ComSat from the file interface.py. 

The running time, optimal value, and other parameters regarding the instance are then saved in the file data_storage.txt

Instances can be made by specifying parameters such as number of nodes, vehicles, etc, through the file instance_maker.py. Based on the choice of the number of nodes (15,25 and 35) there are three possible tree structure, hard coded in the file edges_for_graphs.py 

Some instances are available in the folder test_cases for demonstration. when instances are generated they are automatically saved in the folder test_cases.

The folder "paths_containers" containes json files storing the shortest path from each node to each other node, depending on the number of nodes and the connectivity of the graph.

The files paths_changer.py, assignment_model.py, route_checker.py, contain the Z3 code to model the Paths Changing, Assignment, and Routes Verification sub-problems, respectively. The files starting with "routing" and "scheduling" contain different version of the implementation of the Routing and Capacity verification problems, respectively. The differences among "routing" versions are based on the solver used (either Gurobi or Z3), the model formulation (either 2 or 3 indexes) and whether they include the tighening constraint to break symmetry among different solutions (either _2 or ""). 
Differences among "scheduling" version depend on whether they are supporting the generation of an Unsat Core to guide the paths search (_UC), or not (_basic). 
Moreover, it is possible to solve an instance of the CF-EVRP by calling ComSat_Slim instead of ComSat. ComSat_Slim.py will call E_Routing_Gurobi.py, which contains the implementation of the E-Routing Problem; specific versions of the "route_checker" and "scheduling_model" (_slim) have been implemented to be called when using E_Routing_Gurobi.py instead of a "routing" model and assignment_model.py. 

The files 

Finally, the file support_functions.py contains functions for parsing the instances, measure distance between nodes, and print data.
  
 
