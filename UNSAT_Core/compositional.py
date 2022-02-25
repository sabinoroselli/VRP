from z3 import *
import networkx as nx
from support_functions import json_parser, paths_formatter
from itertools import combinations
from time import time as tm

from routing_multi_depot_model import routing
from assignment_model import assignment
from scheduling_model_v4 import schedule
from path_changer_v4 import changer
from route_checker_v1 import routes_checking


def Compositional(problem):

    print('COMPOSITIONAL ALGORITHM')
    print('instance:',problem)

    starting_time = tm()

    # -- Parse json file with the plant layout and the jobs info
    jobs, nodes, edges, Autonomy, ATRs, charging_coefficient = json_parser('test_cases/%s.json' % problem)

    # for i in jobs:
    #     print(i,jobs[i])

    # -- Build the graph out of nodes and edges
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_weighted_edges_from([
        (i[0], i[1], edges[i][0]) for i in edges
    ])

    # i am flattening the jobs and their task to calculate distances between any two interest point
    tasks = {j + '_' + i: jobs[j]['tasks'][i]['location'] for j in jobs for i in jobs[j]['tasks']}
    combination = {i: (tasks[i[0]], tasks[i[1]]) for i in combinations(tasks, 2)}

    # -- Compute the shortest paths between any two customers
    shortest_paths = {
        (i[0], i[1]): nx.shortest_path(graph, combination[i][0], combination[i][1], weight='weight')
        for i in combination
    }
    shortest_paths.update({
        (i[1], i[0]): nx.shortest_path(graph, combination[i][1], combination[i][0], weight='weight')
        for i in combination
        # if k_shortest_paths(graph,combination[i][0],combination[i][1],K,weight='weight') != []
    })

    # -- INITIALIZATION
    instance = unknown  # -- Decision upon the whole problem
    routing_feasibility = unknown  # -- Initialize status of routing problem
    previous_routes = []  # -- Initialize list of used sets of routes
    routes_bound = 200  # -- Limit on the number of routes

    # routes_to_check = 1

    # -- Start with routing problem
    while routing_feasibility != unsat and instance == unknown and len(previous_routes) < routes_bound:

        print('Length of \'previous routes\'', len(previous_routes))

        # -- Solving the routing problem
        routing_start = tm()
        routing_feasibility,current_routes, routes_solution = routing(
                                                edges,jobs,tasks,Autonomy,shortest_paths,previous_routes)
        routing_end = tm()

        print('>>  The routing problem is {} and took {}s'
              .format(routing_feasibility, round(routing_end - routing_start,2)))


        previous_routes.append(routes_solution)             # -- Add current routes to previous routes
        # routing_feasibility = unsat                      # -- For testing
        # print('>>  The routing problem has been made',routing_feasibility)

        if routing_feasibility == unsat:
            break  # -- If routing is not feasible, we end the entire loop and the problem is unsolvable

        # -- INITIALIZATION
        assignment_feasibility = unknown        # -- Initialize status of assignment problem
        previous_assignments = []               # -- Initialize list of used sets of routes

        # -- The following list will contain all unsat constraints of all iterations of the capacity verification
        # -- problem AND all iterations of the path changer!!
        capacity_unsat_constraints = []

        # -- Start with assignment problem
        while assignment_feasibility != unsat and instance == unknown:

            #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
            # print('length of previous ass', len(previous_assignments))
            ##### THIS WILL BE REMOVED AFTER I AM DONE FIXING STUFF ######
            current_paths = shortest_paths


            # -- Solving the assignment problem
            assignment_start = tm()
            assignment_feasibility, locations, current_assignment = assignment(
                ATRs, current_routes, charging_coefficient, previous_assignments)
            assignment_end = tm()

            print('>>    The assignment problem is {} and took {}s'
                  .format(assignment_feasibility,round(assignment_end - assignment_start,2)))

            # for item in locations:
            #     print(item)

            previous_assignments.append(current_assignment)         # -- Add current assignment to previous assignment
            # assignment_feasibility = unsat                        # -- For testing
            # print('>>    The assignment problem has been made',assignment_feasibility)

            if assignment_feasibility == unsat:
                break  # -- If assignment is not feasible, we break out of current loop look for new routes

            # -- Format the current paths to use them as a previous solutions for the scheduling and path changing
            shortest_paths_solution, paths_combo, paths_combo_edges = paths_formatter(current_routes, current_paths, tasks)

            # -- If assignment is feasible, we solve the scheduling (capacity verification) problem
            # -- Solving the capacity verification problem
            print('%----- Capacity verification start (in original loop) -----%')
            schedule_start = tm()
            schedule_feasibility, node_sequence, edge_sequence, capacity_unsat_constraints = schedule(
                locations, edges, paths_combo, paths_combo_edges,capacity_unsat_constraints)
            schedule_end = tm()
            print('%----- Capacity verification end (in original loop) -----%')

            print('>>      The capacity verification problem is {} and took {}s'
                  .format(schedule_feasibility,round(schedule_end - schedule_start,2)))

            # -- For testing
            # if len(previous_routes) < routes_to_check:
            #     schedule_feasibility = unsat
            # schedule_feasibility = unsat                # -- For testing
            # print('>>      The capacity verification problem has been made',schedule_feasibility)

            if schedule_feasibility == sat:
                instance = schedule_feasibility         # -- If a feasible schedule is found, that is the solution



            # -- Initialize status of used paths for the current set of routes
            previous_paths = [shortest_paths_solution]

            # -- Initialize status of the assignment problem
            paths_changing_feasibility = unknown

            # -- Set a limit on the number of paths to try otherwise we'll get stuck in this loop, but can't be too
            # -- small otherwise you might just leave out a reasonable solution
            bound = 500
            counter = 1
            # -- ONLY START WITH PATH CHANGING PROBLEM WHEN INSTANCE IS UNKNOWN!
            while paths_changing_feasibility != unsat and instance == unknown and counter < bound:

                print('Paths changing problem .. Attempt {}.'.format(counter))
                # -- Solving the paths changing problem

                print('%----- Path changing start -----%')
                path_change_start = tm()
                paths_changing_feasibility, paths_changing_solution = changer(
                    locations, edges, capacity_unsat_constraints, graph, paths_combo, paths_combo_edges, previous_paths)
                path_change_end = tm()
                print('%----- Path changing end -----%')

                print('>>        The paths changer problem is {} and took {}s'
                      .format(paths_changing_feasibility,round(path_change_end-path_change_start,2)))


                # paths_changing_feasibility = unsat                        # -- For testing
                # print('>>    The paths changing problem has been made',paths_changing_feasibility)

                previous_paths.append(paths_changing_solution)              # -- Add current path to previous paths

                # -- Intermediate step to convert the paths changing solution into readable format for the route_checker
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

                # -- Need to update paths_combo and paths_combo_edges for the newly found path.
                # -- It's the same code as 'current_paths' but making a copy of 'current paths' caused problems.
                # -- It's an ugly solution but it works (so far)
                paths_combo = {}
                for route in buffer:
                    paths_combo.update({route: {}})
                    for pair in buffer[route]:
                        sequence = list(buffer[route][pair])
                        path = [pair[0]]
                        for _ in range(len(sequence)):
                            for i in sequence:
                                if i[0] == path[-1]:
                                    path.append(i[1])
                        # print(route,pair,path)
                        paths_combo[route].update({pair: path})
                paths_combo_edges = {
                    route: {
                        pair:
                            [(first, second)
                             for first, second in zip(paths_combo[route][pair][:-1], paths_combo[route][pair][1:])]
                        for pair_index, pair in enumerate(paths_combo[route])
                    }
                    for route_index, route in enumerate(paths_combo)
                }

                print('The new set of paths resulting from path changer is:')
                for line in paths_combo:
                    print(paths_combo[line])
                print('--')
                for line in paths_combo_edges:
                    print(paths_combo_edges[line])
                print('--')

                # -- Solving the route verification problem
                routes_check_start = tm()
                routes_checking_feasibility, buffer_routes = routes_checking(
                    edges, jobs, tasks, Autonomy, current_paths, current_routes)
                routes_check_end = tm()
                print('>>          The routes verification problem is {} and took {}s'
                      .format(routes_checking_feasibility, round(routes_check_end - routes_check_start,2)))

                # routes_checking_feasibility = unsat                      # -- For testing
                # print('>>          The routes verification problem has been made',routes_checking_feasibility)


                if routes_checking_feasibility == sat:

                    current_routes = buffer_routes

                    # -- If new paths and routes are feasible, check for assignment
                    assignment2_start = tm()
                    assignment_feasibility_2, locations_2, _ = assignment(
                        ATRs, current_routes, charging_coefficient)
                    assignment2_end = tm()
                    print('>>            The assignment problem of new paths is {} and took {}s'
                          .format(assignment_feasibility_2,round(assignment2_end - assignment2_start,2)))

                    # assignment_feasibility_2 = unsat      # -- For testing
                    # print('>>            The assignment problem of new paths has been made',assignment_feasibility_2)


                    if assignment_feasibility_2 == sat:     # -- If the assignment of new paths is sat, check capacity
                        schedule2_start = tm()
                        print('%----- Capacity verification start (for new paths) -----%')
                        # schedule_feasibility, node_sequence, edge_sequence = schedule(locations_2, edges)
                        schedule_feasibility, node_sequence, edge_sequence, capacity_unsat_constraints = schedule(
                            locations_2, edges, paths_combo, paths_combo_edges,capacity_unsat_constraints)

                        print('%----- Capacity verification end (for new paths) -----%')
                        schedule2_end = tm()
                        print('>>              The capacity verification problem of new paths is {} and took {}s'
                              .format(schedule_feasibility,round(schedule2_end-schedule2_start,2)))

                        # # -- For testing
                        # if len(previous_routes) < routes_to_check:
                        #     schedule_feasibility = unsat
                        # print('>>              The capacity verification problem of new paths has been made'
                        #       , schedule_feasibility)
                        if schedule_feasibility == sat:
                            instance = schedule_feasibility  # -- If a feasible schedule is found, that is the solution

                if bound < 666:
                    counter += 1
    #### the following parts must be commented ON if you have set up a limit on
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

    running_time = round(tm()-starting_time,3)

    optimum = 'None'
    # just some output to check while running the instances in batches

    print('         Feasibility', instance)
    print('         Running time', running_time)
    if instance == sat:
        optimum = sum([item[1] for item in current_routes])
        print('         travelling distance: ',optimum)

        print('##########################################')
        for item in current_routes:
            print(item)
        print('##########################################')
        for item in locations:
            print(item)
        # print('##########################################')
        # for i in node_sequence:
        #     print( i[0].split('_')[1] + '-' + str(int(i[0].split('_')[5].split(':')[0])+1) + ':' + str(i[1]) + ';' )
        #     # print(i)

    return instance,optimum,running_time,len(previous_routes)