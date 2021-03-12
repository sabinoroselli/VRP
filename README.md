# VRP

This project allows to generate and solve instances of the conflict-free, electric vehicle routing problem (CF-EVRP) by means of a monolithic model written for the SMT solver Z3, and an SMT-based compositional algorithm, that breaks down the problem into sub-problems and iteratively solves them to find a solution to the original CF-EVRP.

The monolithic model is coded using the Python API for Z3 and is available in the file monolithic_model.py

The execution of a batch of instances can be done in sequence, by running the file interface.py, or in parallel by running the file parallel_execution.py. both file allow to specify what instances must be solved.

The running time, optimal value, and other parameters regarding the instance are then saved in the file data_storage.txt

Instances can be made by specifying parameters such as number of nodes, vehicles, etc, through the file instance_maker.py. based on the choice of the number of nodes (15,25 and 35) there are three possible tree structure, hard coded in the file edges_for_graphs.py 

Some instances are available in the folder test_cases for demonstration. when instances are generated they are automatically saved in the folder test_cases.

The file all_pahts contains graph search algorithms to find paths between nodes. Such paths are then used in the algorithm as input for the routing problem.

The files path_finding_model.py, routing_model.py, assignment_model.py, and scheduling_model.py contain the Z3 code to model the subproblems. They are called by the algorithm written in the file compo_algo.py to solve an instance of the CF-EVRP. 

Finally, the file support_functions.py contains functions for parsing the instances, measure distance between nodes, and print data.
  
 
