from z3 import *

# -- If the problem is feasible, returns a solution to the feasible problem. If the problem is infeasible, filters out
# -- the constraints from the unsat core that could practically be changed (e.g. not the domain constraints), then adds
# -- all constraints again such that in the end, the returned problem is infeasible. However, we now know which
# -- constraints are infeasible and we can use this information for the path scheduling problem
# -- <==> path_changer_v3/v4

def schedule(locations,edges, paths_combo, paths_combo_edges, capacity_unsat_constraints, locations_plus):

    # print('The capacity constraints will be checked for the following set of paths:')

    # print('-- PATHS COMBO --')
    # for line in paths_combo:
    #     print(line,paths_combo[line])
    #
    # print('-- PATHS COMBO EDGES')
    # for line in paths_combo_edges:
    #     print(paths_combo_edges[line])
    #
    # print('-- LOCATIONS ')
    # for i_index, i in enumerate(locations):
    #     print(i,locations[i])

    hubs = list(dict.fromkeys([
        locations[i][0][0]
        for i in locations
    ]))


    # -- Generate a variable for each node (operation) and edge of each route and pair
    visit_node = [[[Real('visit_route_{}_pair_{}_node_{}'.format(route, pair, node))
                              for node_index, node in enumerate(paths_combo[route][pair])]
                             for pair_index, pair in enumerate(paths_combo[route])]
                            for route in paths_combo]
    leave_node = [[[Real('leave_route_{}_pair_{}_node_{}'.format(route, pair, node))
                              for node_index, node in enumerate(paths_combo[route][pair])]
                             for pair_index, pair in enumerate(paths_combo[route])]
                            for route in paths_combo]
    visit_edge = [[[Real('visit_route_{}_pair_{}_edge_{}'.format(route, pair, edge))
                              for edge_index, edge in enumerate(paths_combo_edges[route][pair])]
                             for pair_index, pair in enumerate(paths_combo_edges[route])]
                            for route in paths_combo]




    s = Solver()                        # -- Generate solver
    s.push()                            # -- Generate push environment such that all constraint can easily be removed
    unsat_constraints_iteration = set()       # -- Set that will contain all unsat constraints
    attempt = 1                         # -- Counter for required number of iterations
    last_iteration = 0                  # -- Counter, if it becomes 1 we are going to do our last iteration


    while last_iteration <= 1:          # -- Stop looping when we have reached our last + 1 iteration

        # -- If last_iteration == 0, we're going to filter out constraints until we're feasible
        if last_iteration == 0:
            print('Capacity verification problem .. Iteration {}.'.format(attempt))

        # -- If last_iteration == 1, we're going to add all constraints one more time (leads to infeasibility)
        elif last_iteration == 1:
            print('Last iteration is now going to start. All constraints are added again, '
                  'which wil make the problem unsatisfiable again.')
        track_tags = set()              # -- Initialize tracking_tags, will be cleared every iteration

        # -- ADD ALL CONSTRAINTS --
        # -- XX Domain constraint 1&2: All node variables should be positive integers
        domain_scheduling_node = [
                   And(
                        visit_node[route_index][pair_index][node_index] >= 0,
                        leave_node[route_index][pair_index][node_index] >= 0
                    )
        for route_index,route in enumerate(paths_combo)
            for pair_index, pair in enumerate(paths_combo[route])
                for node_index, node in enumerate(paths_combo[route][pair])
            ]
        s.add(domain_scheduling_node)


        # -- XX Domain constraint 3: All edge variables should be positive integers

        domain_scheduling_edge = [
            visit_edge[route_index][pair_index][edge_index] >= 0
        for route_index,route in enumerate(paths_combo)
            for pair_index, pair in enumerate(paths_combo_edges[route])
                for edge_index, edge in enumerate(paths_combo_edges[route][pair])
                    ]
        s.add(domain_scheduling_edge)

        # -- 23/24 Precedence constraints among nodes and edges visited in a route


        visit_precedence = [
                And(
                    visit_edge[route_index][pair_index][edge_index] >=
                    visit_node[route_index][pair_index][edge_index]
                    + locations_plus[route][pair]['St'][edge_index],  # Service time                    ,
                    visit_node[route_index][pair_index][edge_index + 1] ==
                    visit_edge[route_index][pair_index][edge_index] + edges[edge][0]  # Travel time
                )
            for route_index, route in enumerate(locations_plus)
            for pair_index, pair in enumerate(paths_combo[route])
            for edge_index, edge in enumerate(paths_combo_edges[route][pair])
            # # Not last element of pair: that one is the duplicate node
            # if edge_index < (len(paths_combo[route][pair]) - 1)
        ]
        s.add(visit_precedence)
        # pp(visit_precedence)

        # -- XX If two routes have the same vehicle the first one has to finish before the second can start\
        # -- !! THIS CONSTRAINT WASN'T PRESENT IN THE ORIGINAL MODEL
        non_overlap = [

                visit_edge[route_index][pair_index][node_index]
                >=
                visit_node[route_index][pair_index][node_index]
                +
                locations_plus[route][pair]['Ct'][node_index]
        for route_index, route in enumerate(locations)
            for pair_index, pair in enumerate(paths_combo[route])
                for node_index, node in enumerate(paths_combo[route][pair])
                    if node_index < (len(paths_combo[route][pair]) - 1)
                        if locations_plus[route][pair]['Ct'][node_index] > 0
                            # -- This line prevents duplicate constraints from being added:
                            # if 'charge_time_r{}_p{}_n{}'.format(route_index,pair_index,node) not in track_tags
                            #     # -- Track tags in order to keep track of duplicates
                            #     track_tags.add('charge_time_r{}_p{}_n{}'.format(route_index,pair_index,node))
        ]
        s.add(non_overlap)

        # -- XX A vehicle leaves a node when it visits the following edge
        leaving_a_node = [
                leave_node[route_index][pair_index][node_index] ==
                visit_edge[route_index][pair_index][node_index]

        for route_index, route in enumerate(locations)
            for pair_index, pair in enumerate(paths_combo[route])
                for node_index, node in enumerate(paths_combo[route][pair])
                    if node_index != (len(paths_combo[route][pair]) - 1)
        # # -- For the last node of the last pairs we set leave_node equal to visit_node, because otherwise
        # # -- leave_node is undefined for this node (which doesn't really matter, but then they end up
        # # -- becoming equal to 0 )
        # if pair_index == (len(paths_combo[route])-1):
        #     if node_index == (len(paths_combo[route][pair]) - 1):
        #         # print(pair_index,node_index)
        #         s.add(
        #             leave_node[route_index][pair_index][node_index] ==
        #             visit_node[route_index][pair_index][node_index]
        #         )
        ]

        s.add(leaving_a_node)

        # -- Careful: Duplicates need to have the same time. So the leaving/arrival time of the last node of each pair
        # -- needs to be equal to the first node of the next pair. Doesn't hold for the first node of first pair and
        # -- last node of last pair.

        matching_pairs = [
               And(
                    visit_node[route_index][pair_index][-1] == visit_node[route_index][pair_index+1][0],
                    leave_node[route_index][pair_index][-1] == leave_node[route_index][pair_index+1][0]
                )
            for route_index,route in enumerate(paths_combo)
                for pair_index, pair in enumerate(paths_combo[route])
                    if pair_index != (len(paths_combo[route]) - 1)
            ]
        s.add(matching_pairs)
        # -- 25 Nodes that correspond to tasks have time windows
        # -- Time windows could be changed. --> Track this constraint
        for route_index, route in enumerate(locations):
            for pair_index, pair in enumerate(list(paths_combo[route])):
                for node_index, node in enumerate(paths_combo[route][pair]):
                    # # -- Skip duplicates
                    # if index_conversion[route_index][pair_index][node_index] != 'Duplicate':
                        # -- Time window can't be 'None'
                        if locations_plus[route][pair]['TW'][node_index] != 'None':
                            if 'timewindow_r{}_p{}_n{}_'.format(route_index, pair, node) not in unsat_constraints_iteration:
                                track_tags.add('timewindow_r{}_p{}_n{}_'.format(route_index, pair, node))

                                s.assert_and_track(
                                    And(
                                        visit_node[route_index][pair_index][node_index] >=
                                        locations_plus[route][pair]['TW'][node_index][0],
                                        visit_node[route_index][pair_index][node_index] <=
                                        locations_plus[route][pair]['TW'][node_index][1]
                                    )
                                    , 'timewindow_r{}_p{}_n{}_'.format(route_index, pair, node)
                                )
            # # this is only for the last pair in each route
            # for node_index, node in enumerate(list(paths_combo[route])[-1]):
            #     # -- Time window can't be 'None'
            #     if locations[route][2][index_conversion_2[route][list(paths_combo[route])[-1]][node_index]] != 'None':
            #         if 'timewindow_r{}_p{}_n{}_'.format(route_index, list(paths_combo[route])[-1], node) \
            #                 not in unsat_constraints_iteration:
            #             track_tags.add('timewindow_r{}_p{}_n{}_'.format(route_index, list(paths_combo[route])[-1], node))
            #
            #             s.assert_and_track(
            #                 And(
            #                     visit_node[route_index][len(paths_combo[route])-1][node_index] >=
            #                     locations[route][2][index_conversion_2[route][list(paths_combo[route])[-1]][node_index]][0],
            #                     visit_node[route_index][len(paths_combo[route])-1][node_index] <=
            #                     locations[route][2][index_conversion_2[route][list(paths_combo[route])[-1]][node_index]][1]
            #                 )
            #                 , 'timewindow_r{}_p{}_n{}_'.format(route_index, list(paths_combo[route])[-1], node)
            #             )
        # -- CAUTION: THE "_" AT THE END OF EACH STRING IS CRUCIAL FOR CORRECT EXTRACTION OF THE CONSTRAINTS IN THE
        # -- PATH FINDER, WITHOUT THIS "_" E.G. NUMBERS 1 AND 10 WILL BE INTERPRETED AS THE SAME VALUE!!

        # -- 26 Vehicles can't use the same node at the same time (unless the node is a hub)
        # -- Paths can be changed. --> Track this constraint
        for route_index1, route1 in enumerate(locations):
            for pair_index1, pair1 in enumerate(paths_combo[route1]):
                for node_index1, node1 in enumerate(paths_combo[route1][pair1]):

                    for route_index2, route2 in enumerate(locations):
                        for pair_index2, pair2 in enumerate(paths_combo[route2]):
                            for node_index2, node2 in enumerate(paths_combo[route2][pair2]):

                                if route1 != route2:
                                    if node1 == node2 and node1 not in hubs:

                                        # -- Tag of constraint and 'mirror' constraint can't be in unsat constraints
                                        if 'capacity_node_r{}_p{}_n{}_r{}_p{}_n{}_'.format(
                                                route_index1,pair1,node1,route_index2,pair2,node2) \
                                                not in unsat_constraints_iteration:
                                            if 'capacity_node_r{}_p{}_n{}_r{}_p{}_n{}_'.format(
                                                    route_index2, pair2, node2, route_index1, pair1, node1) \
                                                    not in unsat_constraints_iteration:

                                                # -- This line prevents 'mirror' constraints from being added:
                                                if 'capacity_node_r{}_p{}_n{}_r{}_p{}_n{}_'.format(
                                                        route_index2, pair2,node2,route_index1, pair1,node1) \
                                                        not in track_tags:

                                                    # -- Track tags in order to keep track of 'mirror' constraints
                                                    track_tags.add('capacity_node_r{}_p{}_n{}_r{}_p{}_n{}_'.format(
                                                        route_index1,pair1,node1,route_index2,pair2,node2))
                                                    s.assert_and_track(
                                                        Or(
                                                            visit_node[route_index1][pair_index1][node_index1] >=
                                                            leave_node[route_index2][pair_index2][node_index2] + 1,

                                                            visit_node[route_index2][pair_index2][node_index2] >=
                                                            leave_node[route_index1][pair_index1][node_index1] + 1
                                                        )
                                                        , 'capacity_node_r{}_p{}_n{}_r{}_p{}_n{}_'.format(
                                                            route_index1,pair1,node1,route_index2,pair2,node2)
                                                    )
        # -- CAUTION: THE "_" AT THE END OF EACH STRING IS CRUCIAL FOR CORRECT EXTRACTION OF THE CONSTRAINTS IN THE
        # -- PATH FINDER, WITHOUT THIS "_" E.G. NUMBERS 1 AND 10 WILL BE INTERPRETED AS THE SAME VALUE!!

        # -- In the original model, every OR constraint was added twice but swapped around. This leads to the fact that
        # -- double the amount of constraints we're imposed. This didn't really cause problems because the constraints
        # -- were identical, but it also wasn't necessary. That's why I filter out 'mirror' constraints


        # -- 27 Vehicles can't transit over the same edge in the same direction at the same time
        # -- Paths can be changed. --> Track this constraint
        for route_index1, route1 in enumerate(locations):
            for pair_index1, pair1 in enumerate(paths_combo_edges[route1]):
                for edge_index1, edge1 in enumerate(paths_combo_edges[route1][pair1]):

                    for route_index2, route2 in enumerate(locations):
                        for pair_index2, pair2 in enumerate(paths_combo_edges[route2]):
                            for edge_index2, edge2 in enumerate(paths_combo_edges[route2][pair2]):

                                if route1 != route2:
                                    if edge1 == edge2: # and edges[edge1][1] == 1:
                                        # print(route_index1, pair_index1, edge_index1, edge1)
                                        # print(route_index2, pair_index2, edge_index2, edge2)
                                        # print('--')

                                        # -- Tag of constraint and 'mirror' constraint can't be in unsat constraints
                                        if 'capacity_edge_same_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                        route_index1,pair1,edge1,route_index2,pair2,edge2) \
                                                not in unsat_constraints_iteration:
                                            if 'capacity_edge_same_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                        route_index2,pair2,edge2,route_index1,pair1,edge1) \
                                                    not in unsat_constraints_iteration:

                                                # -- This line prevents 'mirror' constraints from being added:
                                                if 'capacity_edge_same_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                        route_index2,pair2,edge2,route_index1,pair1,edge1) \
                                                        not in track_tags:

                                                    # -- Track tags in order keep track of 'mirror'
                                                    track_tags.add('capacity_edge_same_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                        route_index1,pair1,edge1,route_index2,pair2,edge2))
                                                    s.assert_and_track(
                                                        Or(
                                                            visit_edge[route_index1][pair_index1][edge_index1] >=
                                                            visit_edge[route_index2][pair_index2][edge_index2] + 1,

                                                            visit_edge[route_index2][pair_index2][edge_index2] >=
                                                            visit_edge[route_index1][pair_index1][edge_index1] + 1
                                                        )
                                                        , 'capacity_edge_same_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                        route_index1,pair1,edge1,route_index2,pair2,edge2)
                                                    )
        # -- CAUTION: THE "_" AT THE END OF EACH STRING IS CRUCIAL FOR CORRECT EXTRACTION OF THE CONSTRAINTS IN THE
        # -- PATH FINDER, WITHOUT THIS "_" E.G. NUMBERS 1 AND 10 WILL BE INTERPRETED AS THE SAME VALUE!!

        # -- In the original model, every OR constraint was added twice but swapped around. This leads to the fact that
        # -- double the amount of constraints we're imposed. This didn't really cause problems because the constraints
        # -- were identical, but it also wasn't necessary. That's why I filter out 'mirror' constraints


        # -- 28 Vehicles can't transit over the same edge in the opposite direction
        # -- Paths can be changed. --> Track this constraint
        for route_index1, route1 in enumerate(locations):
            for pair_index1, pair1 in enumerate(paths_combo_edges[route1]):
                for edge_index1, edge1 in enumerate(paths_combo_edges[route1][pair1]):

                    for route_index2, route2 in enumerate(locations):
                        for pair_index2, pair2 in enumerate(paths_combo_edges[route2]):
                            for edge_index2, edge2 in enumerate(paths_combo_edges[route2][pair2]):

                                if route1 != route2:
                                    if edge1[0] == edge2[1] and edge1[1] == edge2[0]: # and edges[edge1][1] == 1:
                                        # print(route_index1, pair_index1, edge_index1, edge1)
                                        # print(route_index2, pair_index2, edge_index2, edge2)
                                        # print('--')

                                        # -- Tag of constraint and 'mirror' constraint can't be in unsat constraints
                                        if 'capacity_edge_diff_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                        route_index1,pair1,edge1,route_index2,pair2,edge2) \
                                                not in unsat_constraints_iteration:
                                            if 'capacity_edge_diff_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                        route_index2,pair2,edge2,route_index1,pair1,edge1) \
                                                    not in unsat_constraints_iteration:

                                                # -- This line prevents 'mirror' constraints from being added:
                                                if 'capacity_edge_diff_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                        route_index2,pair2,edge2,route_index1,pair1,edge1) \
                                                        not in track_tags:

                                                    # -- Track tags in order keep track of 'mirror' constraints
                                                    track_tags.add('capacity_edge_diff_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                        route_index1,pair1,edge1,route_index2,pair2,edge2))

                                                    s.assert_and_track(
                                                        Or(
                                                            visit_edge[route_index1][pair_index1][edge_index1] >=
                                                            visit_edge[route_index2][pair_index2][edge_index2]
                                                            + edges[edge2][0],

                                                            visit_edge[route_index2][pair_index2][edge_index2] >=
                                                            visit_edge[route_index1][pair_index1][edge_index1]
                                                            + edges[edge1][0]
                                                        )
                                                        , 'capacity_edge_diff_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                        route_index1,pair1,edge1,route_index2,pair2,edge2)
                                                    )
        # -- CAUTION: THE "_" AT THE END OF EACH STRING IS CRUCIAL FOR CORRECT EXTRACTION OF THE CONSTRAINTS IN THE
        # -- PATH FINDER, WITHOUT THIS "_" E.G. NUMBERS 1 AND 10 WILL BE INTERPRETED AS THE SAME VALUE!!

        # -- In the original model, every OR constraint was added twice but swapped around. This leads to the fact that
        # -- double the amount of constraints we're imposed. This didn't really cause problems because the constraints
        # -- were identical, but it also wasn't necessary. That's why I filter out 'mirror' constraints

        nodes_schedule = {}
        edges_schedule = []
        scheduling_feasibility = s.check()
       # safe guard to avoid endless loops when the assignment problem is sat while the CapVer is unsat
        if all([True if x.split('_')[0] == 'timewindow' else False for x in [str(item) for item in s.unsat_core()] ])\
                and s.check() == unsat:
            # print('The constraints in the unsat core are: \n {}.'.format(s.unsat_core()))
            break
        # -- If we are unsatisfiable and have not yet reached our last iteration, we need to start to iteratively
        # -- remove constraints until we become satisfiable
        elif s.check() == unsat and last_iteration == 0:
            # print('The capacity verification problem is {}.'.format(scheduling_feasibility))
            # print('The unsatisfiable core of this iteration contains {} unsatisfiable constraints (both time windows'
            #       ' and capacity constraints!)'.format(len(s.unsat_core())))
            # print('The constraints in the unsat core are: \n {}.'.format(s.unsat_core()))

            unsat_constraints = [str(item) for item in s.unsat_core()]  # Filter out all unsat constraints


            # -- From each set of unsatisfiable constraints, we can either filter out only the first unsat constraint
            # -- (this is rather random) or all of the constraints, and add them to 'unsat_constraints_iteration'.
            # -- Theoretically, there is no reason to remove all conflicting constraints. If there are two conflicting
            # -- constraints, the second one can just stay, if there are 3 or more conflicting constraints, they will
            # -- be caught later in loop anyway. However, because you're not sure what constraint you remove, I
            # -- believe its better to remove all of them, and in the path changing problem decide what you do with it.

            # for item in unsat_constraints[0::-1]:           # -- Add only the first unsat constraint to list
            for item in unsat_constraints:
                if item[0:8] == 'capacity':                 # -- Only filter capacity constraints and add them to list
                    unsat_constraints_iteration.add(item)   # -- unsat_constraints_iteration contains all filtered constraints
            # print(unsat_constraints_iteration)

            # print('{} unsatisfiable capacity constraints (!!) have been filtered out so far'.format(len(unsat_constraints_iteration)))

            s.pop()                 # -- Remove all previous constraints that made the model infeasible
            s.push()                # -- Generate new environment for new constraints to try
            attempt +=1

        # -- If we are unsat and have reached our last iteration, this means that we have already gone through the
        # -- entire process of removing constraints until we're satisfiable and we just added all constraints for the
        # -- last time in order send an unsatisfiable problem to path changing problem
        elif s.check() == unsat and last_iteration == 1:
            break
            # -- Break out of while loop, return feasibility and unsat constraints (no nodes or edge schedule)

        elif s.check() == sat:          # -- If we have reached satisfiability
            m3 = s.model()

            for route_index, route in enumerate(locations):
                for pair_index, pair in enumerate(paths_combo[route]):
                    for node_index, node in enumerate(paths_combo[route][pair]):
                        nodes_schedule.update(

                            {
                                (route,pair,node):m3[visit_node[route_index][pair_index][node_index]]
                            }
                        )
                        # print (
                        #         'vehicle_{}_visits_route_{}_pair_{}_node_{}: '.format(route, route_index, pair, node),
                        #         m3[visit_node[route_index][pair_index][node_index]]
                        #     )

            for route_index, route in enumerate(locations):
                for pair_index, pair in enumerate(paths_combo_edges[route]):
                    for edge_index, edge in enumerate(paths_combo_edges[route][pair]):
                        edges_schedule.append(
                            (
                                'vehicle_{}_visits_route_{}_pair_{}_edge_{}: '.format(route[0], route_index, pair, edge),
                                    m3[visit_edge[route_index][pair_index][edge_index]]
                            )
                        )

            # -- If it only took one attempt to become satisfiable, the problem was already satisfiable by itself
            # -- and the entire loop didn't have to be started because no constraints had to be removed
            if attempt == 1:
                # print('The capacity verification problem is {}, no unsatisfiable capacity constraints have to be '
                #       'filtered out.'.format(scheduling_feasibility,len(unsat_constraints_iteration)))
                break
                # -- Break out of while loop, return feasibility, node schedule and edge schedule (no unsat constraints)

            # -- If it took more than one attempt to become satisfiable, unsatisfiable constraints must have been
            # -- removed. So, we once again add all constraints such that the problem that we send to the path
            # -- changing problem is unsatisfiable.
            elif attempt > 1:
                # print('The capacity verification problem is {}. In total, {} unsatisfiable capacity constraints (!!) '
                #       'have been filtered out.'.format(scheduling_feasibility, len(unsat_constraints_iteration)))

                s.pop()                         # -- Remove ALL constraints
                s.push()                        # -- Generate new environment to add new constraints for last time

                # -- After this line only one more iteration in while loop will be performed. This iteration
                # -- will add all constraints again, including the unsatisfiable ones, which will send the unsatisfiable
                # -- problem plus the unsatisfiable constraints to the path changer problem
                last_iteration += 1

                # -- 'unsat_constraints_iteration' has to be cleared so that all constraints can be added again
                # -- for the last time, but before clearing all constraints are saved in 'capacity_unsat_constraints'
                for constraint in sorted(unsat_constraints_iteration):
                    capacity_unsat_constraints.append(constraint)
                unsat_constraints_iteration.clear()

    # print('All unsatisfiable capacity constraints (!!) are:'.format())
    # for unsat_constr in capacity_unsat_constraints:
    #     print(unsat_constr)

    return scheduling_feasibility,nodes_schedule,edges_schedule,capacity_unsat_constraints
