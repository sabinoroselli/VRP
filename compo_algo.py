import networkx as nx
from time import time as tm
from itertools import combinations
from funzioni_di_supporto import json_parser, k_shortest_paths # make_graph, ATRs_requirement
from z3 import *

from path_finding_model import path_finder
from routing_model import routing
from assignment_model import assignment
from scheduling_model import schedule

def the_algorithm(problem):
    # first of all, let's parse the json file with the plant layout and the jobs info
    jobs,nodes,edges,Autonomy,ATRs,charging_coefficient = json_parser('test_cases/%s.json' % problem)

    # now let's build the graph out of nodes and edges
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_weighted_edges_from([
        (i[0], i[1], edges[i][0]) for i in edges
    ])

    # i am flattening the jobs and their task to calculate distances between any two interest point
    tasks = {j + '_' + i: jobs[j]['tasks'][i]['location'] for j in jobs for i in jobs[j]['tasks'] }
    combination = {i:(tasks[i[0]],tasks[i[1]]) for i in combinations(tasks, 2)}
    # print(combination)
    # now i want to find all paths from any two points of interest

    # print('generating all paths...')
    start_generation = tm()
    # I AM GENERATING K PATHS FOR EACH PAIR OF POINTS
    K = 10
    Paths = {
        (i[0],i[1]):k_shortest_paths(graph,combination[i][0],combination[i][1],K,weight='weight')
        for i in combination
        # if k_shortest_paths(graph,combination[i][0],combination[i][1],K) != []
    }
    Paths.update({
            (i[1],i[0]):k_shortest_paths(graph,combination[i][1],combination[i][0],K,weight='weight')
            for i in combination
            # if k_shortest_paths(graph,combination[i][0],combination[i][1],K,weight='weight') != []
    })
    generation_time = round(tm() - start_generation,2)
    # print('generation completed: ', Sum([len(i) for i in Paths.values()]),
    #                     ' values computed in ', generation_time, ' seconds')
    # for i in Paths:
    #     print(i,Paths[i])
    # HERE BEGINS THE BEST ALGORITHM FOR AGV SCHEDULING THAT THE HUMAN RACE HAS EVER POSSESSED

    start = tm()

    used_paths = []
    PR = []
    instance = unknown
    optimum = 'None'
    count1 = 1
    while instance == unknown and count1 < 10:
        RF = unknown
        print('first loop', count1)
        count1 += 1
        PF, path = path_finder(Paths,edges,used_paths)
        print('pf',PF)
        if PF == unsat:
            instance = PF
        else:
            used_paths.append(path)
            # print('used paths',len(used_paths))
            # just formatting the paths such that they can be inputed into the next model
            current_path = {
                i: Paths[i][j[1]] for i, j in zip(Paths, path)
            }
            # for i in current_path:
            #     print(i,current_path[i])
            count2 = 1
            while RF != unsat and instance == unknown and count2 < 10:
                print('second loop', count2)
                count2 += 1
                RF, routes_plus, current_solution = routing(edges, jobs, Autonomy, current_path, PR)
                print('rf',RF)
                # for i in routes_plus:
                #     print(i)
                if RF == unsat:
                    if PR == []:
                        instance = unsat
                    else:
                        PR = []

                else:
                    PR.append(current_solution)
                    # print('previous routes',len(PR))
                    AF,locations = assignment(ATRs,routes_plus,charging_coefficient,jobs,current_path)
                    print('af', AF)
                    # for i in locations:
                    #     print(i,locations[i])
                    if AF == sat:
                        SF,nodes_schedule,edges_schedule = schedule(locations,edges)
                        print('sf', SF)
                        # print('NODES')
                        # for i in nodes_schedule:
                        #     print(i)
                        # print('EDGES')
                        # for i in edges_schedule:
                        #     print(i)
                        if SF == sat:
                            instance = SF
                            optimum = sum([i[1] for i in routes_plus])


                            # nodes_schedule = sorted(nodes_schedule,key= take_second)
                            # edges_schedule = sorted(edges_schedule,key= take_second)
                            #
                            # print_support(nodes_schedule)
                            # print_support(edges_schedule)
    print('DECOMPOSITION ALGORITHM')
    print('instance: ',problem)
    print(instance)
    solving_time = round(tm()-start,2)
    print('solving time: ',solving_time)

    if instance == sat:
        print('travelling distance: ', optimum)
    return instance, optimum, generation_time, solving_time































