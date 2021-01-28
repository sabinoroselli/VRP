# VRP

This project allows to generate and solve instances of the electric, conflict-free, vehicle routing problem (E-CFVRP) by means of a monolithic model written for the SMT solver Z3. 

The model is coded using the Python API for Z3 and is available in the file monolithic_model.py

The execution of a batch of instances can be done in sequence, by running the file interface.py, or in parallel by running the file parallel_execution.py. both file allow to specify what instances must be solved.

The running time, optimal value, and other parameters regarding the instance are then saved in the file data_storage.txt

Instances can be made by specifying parameters such as number of nodes, vehicles, etc, through the file instance_maker.py. based on the choice of the number of nodes (15,25 and 35) there are three possible tree structure, hard coded in the file edges_for_graphs.py 

Some instances are available in the folder test_cases for demonstration. when instances are generated they are automatically saved in the folder test_cases.

Finally, the file support_functions.py contains functions for parsing the instances, measure distance between nodes, and print data.
  
 
