from z3 import *
import networkx as nx
from support_functions import json_parser, paths_formatter
from itertools import combinations
from time import time as tm

from routing_multi_depot_model import routing
# from routing_md_3index import routing
from assignment_model_2 import assignment
from scheduling_model_2 import schedule
from path_changer_2 import changer
from route_checker import routes_checking

def Compositional(problem):

    print('COMPOSITIONAL ALGORITHM')
    print('instance',problem)

    starting_time = tm()

    # first of all, let's parse the json file with the plant layout and the jobs info
    jobs, nodes, edges, Autonomy, ATRs, charging_coefficient = json_parser('test_cases/%s.json' % problem)

    # now let's build the graph out of nodes and edges
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_weighted_edges_from([
        (i[0], i[1], edges[i][0]) for i in edges
    ])

    # i am flattening the jobs and their task to calculate distances between any two interest point
    tasks = {j + '_' + i: jobs[j]['tasks'][i]['location'] for j in jobs for i in jobs[j]['tasks']}
    combination = {i: (tasks[i[0]], tasks[i[1]]) for i in combinations(tasks, 2)}

    # here I compute the shortest paths between any two customers
    shortest_paths = {
        (i[0], i[1]): nx.shortest_path(graph, combination[i][0], combination[i][1], weight='weight')
        for i in combination
    }
    shortest_paths.update({
        (i[1], i[0]): nx.shortest_path(graph, combination[i][1], combination[i][0], weight='weight')
        for i in combination
        # if k_shortest_paths(graph,combination[i][0],combination[i][1],K,weight='weight') != []
    })

    ############# LET'S INITIALIZE A BUNCH OF STUFF #############

    # decision upon the whole problem
    instance = unknown

    # initialize status of the routing problem
    routing_feasibility = unknown

    # initialize the list of used sets of routes
    previous_routes = []

    # lets's set a limit on the number of routes
    routes_bound = 200

    while routing_feasibility != unsat and instance == unknown and len(previous_routes) < routes_bound:

        #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
        print('length of previous routes', len(previous_routes))

        # let's solve the routing problem
        routing_feasibility,current_routes, routes_solution = routing(
                                                edges,jobs,tasks,Autonomy,shortest_paths,previous_routes
                                                    )

        # for i in current_routes:
        #     print(i)

        previous_routes.append(routes_solution)

        ########### TEST #############
        # routing_feasibility = unsat

        #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
        print('routing', routing_feasibility)

        if routing_feasibility == unsat:
            break

        # let's set the assigment problem feasibility to unknown before running the problem
        assignment_feasibility = unknown

        # initialize the list of used assignments
        previous_assignments = []

        while assignment_feasibility != unsat and instance == unknown:

            #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
            # print('length of previous ass', len(previous_assignments))

            ##### THIS WILL BE REMOVED AFTER I AM DONE FIXING STUFF ######
            current_paths = shortest_paths

            # shortest_paths_solution,paths_combo = paths_formatter(current_routes,current_paths,tasks)

            assignment_feasibility, locations, current_assignment = assignment(
                ATRs, current_routes, charging_coefficient, previous_assignments
            )

            # for i in locations:
            #     print(i)

            previous_assignments.append(current_assignment)

            ########### TEST #############
            # assignment_feasibility = unsat

            #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
            print(' assignment',assignment_feasibility)

            if assignment_feasibility == unsat:
                break

            schedule_feasibility, node_sequence, edge_sequence = schedule(locations, edges)

            ########### TEST #############
            # schedule_feasibility = unsat

            #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
            print('     schedule', schedule_feasibility)

            if schedule_feasibility == sat:
                instance = schedule_feasibility

            # let's format the current paths so that I can use them as a previous solutions for the
            # path changing problem
            shortest_paths_solution, paths_combo = paths_formatter(current_routes, current_paths, tasks)

            # initialize status of used paths for the current set of routes
            previous_paths = [shortest_paths_solution]

            # initialize status of the assignment problem
            paths_changing_feasibility = unknown

            # let's set a limit on the number of paths to try otherwise we'll get stuck in this loop
            bound = 15
            counter = 0
            while paths_changing_feasibility != unsat and instance == unknown and counter < bound:

                #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
                print('iteration', counter)

                paths_changing_feasibility, paths_changing_solution = changer(
                    graph, paths_combo, previous_paths
                )

                #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
                print('         paths_changer', paths_changing_feasibility)

                previous_paths.append(paths_changing_solution)

                # just an intermediate step to convert the paths_changing solution into a format readable by the route_checker
                buffer = {
                    route: {
                        pair: [sol[2] for sol in paths_changing_solution if sol[0] == route and sol[1] == pair]
                        for pair in paths_combo[route]
                    }
                    for route in paths_combo
                }

                # here I get the new paths in a format I can use
                # to check feasibility against time windows and operating range
                new_paths = {}
                for route in buffer:
                    new_paths.update({route: {}})
                    for pair in buffer[route]:
                        sequence = list(buffer[route][pair])
                        path = [pair[0]]
                        for _ in range(len(sequence)):
                            for i in sequence:
                                if i[0] == path[-1]:
                                    path.append(i[1])
                        # print(route,pair,path)
                        new_paths[route].update({pair: path})
                current_paths = new_paths

                routes_checking_feasibility, buffer_routes = routes_checking(
                    edges, jobs, tasks, Autonomy, current_paths, current_routes
                )

                ########### TEST #############
                # routes_checking_feasibility = unsat

                #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
                print('         routes check', routes_checking_feasibility)

                if routes_checking_feasibility == sat:

                    current_routes = buffer_routes

                    assignment_feasibility_2, locations_2, _ = assignment(
                        ATRs, current_routes, charging_coefficient
                    )

                    ########### TEST #############
                    # assignment_feasibility_2 = unsat

                    #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
                    print('             assignment check', assignment_feasibility_2)

                    if assignment_feasibility_2 == sat:
                        schedule_feasibility, node_sequence, edge_sequence = schedule(locations_2, edges)

                        #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
                        print('                 schedule check',schedule_feasibility)

                        if schedule_feasibility == sat:
                            instance = schedule_feasibility

                if bound < 666:
                    counter += 1
    #### the following parts must be commented on if you have set up a limit on
    # the number of iterations of the routing problem and OFF if you relax that
    #########################################
    # and len(previous_routes) < routes_bound:
    # elif routing_feasibility == unsat and len(previous_routes) == routes_bound:
    #     instance = unknown
    #########################################
    if routing_feasibility == unsat and len(previous_routes) < routes_bound:
        instance = routing_feasibility
    elif routing_feasibility == unsat and len(previous_routes) == routes_bound:
        instance = unknown

    running_time = round(tm()-starting_time,2)

    optimum = 'None'
    # just some output to check while running the instances in batches

    print('  feasibility', instance)
    print('  running time', running_time)
    if instance == sat:
        optimum = sum([i[1] for i in current_routes])
        print('     travelling distance: ',optimum)

        # print('##########################################')
        # for i in current_routes:
        #     print(i)
        # print('##########################################')
        # for i in locations:
        #     print(i)
        # print('##########################################')
        # for i in node_sequence:
        #     print(i)

    return instance,optimum,running_time,len(previous_routes)
