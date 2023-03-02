from z3 import *
import networkx as nx
from support_functions import json_parser, paths_formatter
from itertools import combinations
from time import time as tm


# from routing_2index_Gurobi import routing
# from routing_2index_Z3 import routing

# from routing_3index_Gurobi import routing
# from routing_3index_Z3 import routing

# from routing_3index_Gurobi_2 import routing
# from routing_3index_Z3_2 import routing

from assignment_model_2 import assignment



from path_changer_2 import changer


from route_checker import routes_checking

def Compositional(routing_model,problem,UGS = False):

    if routing_model == '1':
        from routing_3index_Gurobi import routing
    elif routing_model == '2':
        from routing_3index_Gurobi_2 import routing

    if UGS == True:
        from scheduling_model_UC import schedule
    elif UGS == False:
        from scheduling_model_basic import schedule

    print('COMPOSITIONAL ALGORITHM')
    print('instance',problem)

    starting_time = tm()

    # first of all, let's parse the json file with the plant layout and the jobs info
    jobs, nodes, edges, Autonomy, ATRs, charging_coefficient, start_list = json_parser('test_cases/%s.json' % problem)

    # for i in jobs:
    #     print(i,jobs[i])

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

    # I wanna know if paths are changed
    paths_changed = "NO"
    # this parameter is only for testing and it makes the "schedule check" UNSAT for a number of iterations to trigger
    routes_to_check = 2

    while routing_feasibility != unsat and instance == unknown and len(previous_routes) < routes_bound:

        #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
        print('length of previous routes', len(previous_routes))

        # let's solve the routing problem
        routing_start = tm()
        routing_feasibility,current_routes, routes_solution = routing(
                                            edges, jobs, tasks, Autonomy, start_list, ATRs, shortest_paths, previous_routes
                                                    )
        routing_end = tm()
        # for index,i in enumerate(current_routes):
        #     print(i[0])
        #     print(i[4])
        #     print('######################')

        previous_routes.append(routes_solution)
        # pp(previous_routes)

        ########### TEST #############
        # routing_feasibility = unsat

        #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
        print('routing', routing_feasibility, round(routing_end - routing_start,2))

        if routing_feasibility == unsat:
            break

        # let's set the assigment problem feasibility to unknown before running the problem
        assignment_feasibility = unknown

        # initialize the list of used assignments
        previous_assignments = []

        # -- The following list will contain all unsat constraints of all iterations of the capacity verification
        # -- problem AND all iterations of the path changer!!
        capacity_unsat_constraints = []

        while assignment_feasibility != unsat and instance == unknown:

            #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
            # print('length of previous ass', len(previous_assignments))

            ##### THIS WILL BE REMOVED AFTER I AM DONE FIXING STUFF ######
            current_paths = shortest_paths

            # shortest_paths_solution,paths_combo = paths_formatter(current_routes,current_paths,tasks)
            assignment_start = tm()
            assignment_feasibility, locations, current_assignment = assignment(
                ATRs, current_routes, charging_coefficient, previous_assignments
            )
            assignment_end = tm()
            # print('############ LOCATIONS ##############')
            # for i in locations:
            #     print(i,locations[i])

            previous_assignments.append(current_assignment)

            ########### TEST #############
            # assignment_feasibility = sat

            #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
            print(' assignment',assignment_feasibility, round(assignment_end - assignment_start,2))

            if assignment_feasibility == unsat:
                break

            # UC: Format the current paths to use them as a previous solutions for the scheduling and path changing
            shortest_paths_solution, paths_combo, paths_combo_edges = paths_formatter(current_routes, current_paths,
                                                                                          tasks)

            schedule_start = tm()
            # schedule_feasibility, node_sequence, edge_sequence = schedule(locations, edges)
            ################ UC: NEW SCHEDULING FUNCTION ####################
            schedule_feasibility, node_sequence, edge_sequence, capacity_unsat_constraints = schedule(
                locations, edges, paths_combo, paths_combo_edges, charging_coefficient, capacity_unsat_constraints)
            schedule_end = tm()
            # print("this is the UC holder")
            # print(capacity_unsat_constraints)
            ########### TEST #############
            # if len(previous_routes) < routes_to_check:
            #     schedule_feasibility = unsat
            # schedule_feasibility = unsat

            #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
            print('     schedule', schedule_feasibility, round(schedule_end - schedule_start,2))

            if schedule_feasibility == sat:
                instance = schedule_feasibility

            # I DON'T NEED THIS ANY LONGER SINCE I DO IT BEFORE THE SCHEDULE FUNCTION
            # # let's format the current paths so that I can use them as a previous solutions for the
            # # path changing problem
            # shortest_paths_solution, paths_combo = paths_formatter(current_routes, current_paths, tasks)

            # initialize status of used paths for the current set of routes
            previous_paths = [shortest_paths_solution]

            # initialize status of the assignment problem
            paths_changing_feasibility = unknown

            # let's set a limit on the number of paths to try otherwise we'll get stuck in this loop
            bound = 500
            counter = 0
            while paths_changing_feasibility != unsat and instance == unknown and counter < bound:

                #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
                print('iteration', counter)

                path_change_start = tm()

                # paths_changing_feasibility, paths_changing_solution = changer(
                #     graph, paths_combo, previous_paths
                # )

                ############### UC: REPLACED BY THE NEW UC GUIDED PATHS CHANGER ################
                paths_changing_feasibility, paths_changing_solution = changer(
                    graph, paths_combo, previous_paths, UGS, capacity_unsat_constraints,
                    locations, edges, paths_combo_edges
                    )
                path_change_end = tm()
                paths_changed = 'YES'
                ################## TEST ##################
                # paths_changing_feasibility = unsat

                # $$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
                print('         paths_changer', paths_changing_feasibility, round(path_change_end - path_change_start, 2))

                if paths_changing_feasibility == sat:

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
                    ################ UC CHANGE ######################
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

                    # route verification problem
                    routes_check_start = tm()
                    routes_checking_feasibility, buffer_routes = routes_checking(
                        edges, jobs, tasks, Autonomy, current_paths, current_routes
                    )
                    routes_check_end = tm()

                    ########### TEST #############
                    # routes_checking_feasibility = unsat

                    #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
                    print('         routes check', routes_checking_feasibility, round(routes_check_end
                                                                                      -
                                                                                      routes_check_start,2))

                    if routes_checking_feasibility == sat:

                        current_routes = buffer_routes

                        ass_2_start = tm()
                        assignment_feasibility_2, locations_2, _ = assignment(
                            ATRs, current_routes, charging_coefficient
                        )
                        ass_2_end = tm()

                        ########### TEST #############
                        # assignment_feasibility_2 = unsat

                        #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
                        print('             assignment check', assignment_feasibility_2, round(ass_2_end - ass_2_start,2))

                        if assignment_feasibility_2 == sat:
                            sched_2_start = tm()
                            ############ UC CHANGE ################
                            # schedule_feasibility, node_sequence, edge_sequence = schedule(locations_2, edges)
                            schedule_feasibility, node_sequence, edge_sequence, capacity_unsat_constraints = schedule(
                                locations_2, edges, paths_combo, paths_combo_edges, charging_coefficient, capacity_unsat_constraints)
                            sched_2_end = tm()
                            # print("this is the UC holder")
                            # print(capacity_unsat_constraints)
                            #### TEST ###########
                            # if len(previous_routes) < routes_to_check:
                            #     schedule_feasibility = unsat

                            #$$$$$$$$$$$ PRINTING $$$$$$$$$$$$$#
                            print('                 schedule check',schedule_feasibility, round(sched_2_end
                                                                                                -
                                                                                                sched_2_start,2))

                            if schedule_feasibility == sat:
                                instance = schedule_feasibility
                                locations = locations_2

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

    running_time = round(tm()-starting_time,2)

    optimum = 'None'
    # just some output to check while running the instances in batches

    print('         feasibility', instance)
    print('         running time', running_time)
    if instance == sat:
        optimum = sum([i[6] for i in current_routes])
        print('         travelling distance: ',optimum)

        # print('##########################################')
        # for i in current_routes:
        #     print(i[0],"distance",i[6],'time',i[1],'latest start',i[2])
        # print('##########################################')
        # for i in locations:
        #     print(i,locations[i])
        # print('##########################################')
        # for i in node_sequence:
        #     # print( i[0].split('_')[1] + '-' + str(int(i[0].split('_')[5].split(':')[0])+1) + ':' + str(i[1]) + ';' )
        #     print(i)
        # # for i in edge_sequence:
        # #     print(i)

    return instance,optimum,running_time,len(previous_routes),paths_changed,counter
