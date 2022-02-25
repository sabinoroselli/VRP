from z3 import *
import networkx as nx
from support_functions import json_parser

# -- From the capacity verification problem, receive the constraints that have been filtered from the unsatisfiable
# -- core. For each of the conflicting constraints, use an (OR(NOT)) statement, so that at maximum one of the
# -- routes/pairs can use this node/edge. This can also mean that none of the routes/pairs can uses this node/edge.
# -- Then, minimize the cost function, i.e. minimize the total path length.
# -- <==> scheduling_model_v4

def changer(locations, edges, capacity_unsat_constraints, graph, paths_combo, paths_combo_edges, previous_paths=[]):

    # print('The following set of paths that was unsatisfiable in the previous step. This set of paths will be changed')
    # for line in paths_combo:
    #     print(paths_combo[line])
    # print('--')
    # for line in paths_combo_edges:
    #     print(paths_combo_edges[line])
    # print('--')

    s = Optimize()

    use_node = [[[Bool('route_{}_pair_{}_node_{}'.format(route,pair,i)) for i in graph.nodes]
                 for pair in paths_combo[route]] for route in paths_combo]
    use_edge = [[[Bool('route_{}_pair_{}_edge_{}'.format(route,pair,i)) for i in graph.edges]
                 for pair in paths_combo[route]] for route in paths_combo]
    # print(use_node)
    # print(use_edge)

    # -- By setting this True or False, we can easily switch between using the 'smart' path finder or not.
    smart_path_finder = False
    if smart_path_finder == True:

        # -- Capacity constraints for nodes: at least one of the conflicting routes+pairs must be False
        for route_index1, route1 in enumerate(locations):
            for pair_index1, pair1 in enumerate(paths_combo[route_index1]):
                for node1 in graph.nodes:
                    # -- Loop over all nodes, not only the ones that are part of the routes. The nodes that are used
                    # -- namely change (that's the goal of the path finder) so this fucks up the loop. Sadly this
                    # -- makes this part of the algorithm rather slow.

                    for route_index2, route2 in enumerate(locations):
                        for pair_index2, pair2 in enumerate(paths_combo[route_index2]):
                            for node2 in graph.nodes:           # -- Loop over all nodes

                                for constraint_index, constraint in enumerate(capacity_unsat_constraints):

                                    # -- NODE CAPACITY
                                    if ('capacity_node_r{}_p{}_n{}_r{}_p{}_n{}_'.format(
                                            route_index1, pair1, node1, route_index2, pair2, node2)) \
                                        in constraint:

                                                # print('route{}_pair{}_node{} route{}_pair{}_node{}'.format(
                                                #     route_index1,pair_index1,node1,
                                                #     route_index2,pair_index2,node2))
                                                s.add(
                                                    Or(
                                                        Not(
                                                            use_node[route_index1][pair_index1][node1]
                                                        )
                                                        ,
                                                        Not(
                                                            use_node[route_index2][pair_index2][node2]
                                                        )
                                                    )
                                                )


        # -- Capacity constraints for edges: at least one of the conflicting routes/pairs must be False
        for route_index1, route1 in enumerate(locations):
            for pair_index1, pair1 in enumerate(paths_combo_edges[route_index1]):
                for edge_index1, edge1 in enumerate(graph.edges):
                    # -- Loop over all edges, not only the ones that are part of the routes. The edges that are used
                    # -- namely change (that's the goal of the path finder) so this fucks up the loop. Sadly this
                    # -- makes this part of the algorithm rather slow.

                    for route_index2, route2 in enumerate(locations):
                        for pair_index2, pair2 in enumerate(paths_combo_edges[route_index2]):
                            for edge_index2, edge2 in enumerate(graph.edges): # -- Loop over all edges

                                for constraint_index, constraint in enumerate(capacity_unsat_constraints):

                                    # -- EDGE CAPACITY IN THE SAME DIRECTION
                                    if edge1 == edge2:    # -- Must already be true for these tags, but just to be sure
                                        if ('capacity_edge_same_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                            route_index1, pair1, edge1, route_index2, pair2, edge2)) \
                                                in constraint:

                                                # print('route{}_pair{}_edgeindex{}_edge{} route{}_pair{}_edgeindex{}_edge{}'.format(
                                                #     route_index1,pair_index1,edge_index1,edge1,
                                                #     route_index2,pair_index2,edge_index2,edge2))
                                            s.add(
                                                Or(
                                                    Not(
                                                        use_edge[route_index1][pair_index1][edge_index1]
                                                    )
                                                    ,
                                                    Not(
                                                        use_edge[route_index2][pair_index2][edge_index1]
                                                    )
                                                )
                                            )

                                    # -- EDGE CAPACITY IN THE OPPOSITE DIRECTION
                                    if edge1[0] == edge2[1] and edge1[1] == edge2[0]: # -- Must already be true for these tags, but just to be sure
                                        if ('capacity_edge_diff_r{}_p{}_e{}_r{}_p{}_e{}_'.format(
                                                route_index1, pair1, edge1, route_index2, pair2, edge2)) \
                                            in constraint:

                                            # print('route{}_pair{}_edgeindex{}_edge{} route{}_pair{}_edgeindex{}_edge{}'.format(
                                            #     route_index1,pair1,edge_index1,edge1,
                                            #     route_index2,pair2,edge_index2,edge2))
                                            s.add(
                                                Or(
                                                    Not(
                                                        use_edge[route_index1][pair_index1][edge_index1]
                                                    )
                                                    ,
                                                    Not(
                                                        use_edge[route_index2][pair_index2][edge_index2]
                                                    )
                                                )
                                            )
    print('Assertions for capacity constraints:',s.assertions()) # -- Assertions so far are the capacity constraints


    # -- 30 For each path of each route start and end node must be used
    start_and_end_are_true = [
        use_node[route][index][node]
            for route in paths_combo
                for index,pair in enumerate(paths_combo[route])
                    for node in graph.nodes
                        if node in pair
    ]


    # -- 31.A Exactly one outgoing edge is used for the start node of each pair of each route
    only_one_edge_for_start = [
        PbEq([(use_edge[route][pair_index][edge_index],1) for edge_index,i in enumerate(graph.edges)
                                if i in [(pair[0],j) for j in graph.successors(pair[0])]]
             ,1)
        for route in paths_combo
        for pair_index, pair in enumerate(paths_combo[route])
    ]
    # -- 31.B Exactly zero incoming edges are used for the start node of each route (not every pair, only first)
    # -- !! THIS CONSTRAINT WASN'T PRESENT IN THE ORIGINAL MODEL
    zero_incoming_edge_for_start = [
        PbEq([(use_edge[route][pair_index][edge_index],1) for edge_index,i in enumerate(graph.edges)
                                if i in [(j,pair[0]) for j in graph.successors(pair[0])]]
             ,0)
        for route in paths_combo
        for pair_index, pair in enumerate(paths_combo[route])
        # if pair_index == 0
    ]


    # -- 32.A Exactly one incoming edge is used for the end node of each pair of each route
    only_one_edge_for_end = [
        PbEq([(use_edge[route][pair_index][edge_index],1) for edge_index,i in enumerate(graph.edges)
                                if i in [(j,pair[1]) for j in graph.predecessors(pair[1])]]
             ,1)
        for route in paths_combo
        for pair_index, pair in enumerate(paths_combo[route])
    ]
    # -- 32.B Exactly zero outgoing edges are used for the end node of each route (not every pair, only first)
    # -- !! THIS CONSTRAINT WASN'T PRESENT IN THE ORIGINAL MODEL
    zero_outgoing_edge_for_end = [
        PbEq([(use_edge[route][pair_index][edge_index], 1) for edge_index, i in enumerate(graph.edges)
              if i in [(pair[1],j) for j in graph.successors(pair[1])]]
             , 0)
        for route in paths_combo
        for pair_index, pair in enumerate(paths_combo[route])
        # if pair_index == (len(paths_combo[route])-1)
    ]


    # -- 33 A path can't use the same edge and its reverse
    not_both_directions = [
        Implies(
            use_edge[route][pair_index][index_i],
            Not(use_edge[route][pair_index][index_j])
        )
        for route in paths_combo
        for pair_index, pair in enumerate(paths_combo[route])
        for index_i,i in enumerate(graph.edges)
        for index_j,j in enumerate(graph.edges)
        if (j[0],j[1]) == (i[1],i[0])
    ]


    # -- 34 For each node except start and end, exactly one outgoing and one incoming edge are used
    exactly_two_edges = [
        And([
                If(
                use_node[route][pair_index][node],
                And(
                    PbEq([(use_edge[route][pair_index][edge_index],1) for edge_index,j in enumerate(graph.edges)
                                                if j in [(k,node) for k in graph.predecessors(node)]
                         ]
                             ,1),
                    PbEq([(use_edge[route][pair_index][edge_index],1) for edge_index,j in enumerate(graph.edges)
                                                if j in [(node,k) for k in graph.successors(node)]
                          ]
                             ,1)
                ),
                And(
                    PbEq([(use_edge[route][pair_index][edge_index], 1) for edge_index, j in enumerate(graph.edges)
                                                if j in [(k, node) for k in graph.predecessors(node)]
                          ]
                            ,0),
                    PbEq([(use_edge[route][pair_index][edge_index], 1) for edge_index, j in enumerate(graph.edges)
                                                if j in [(node, k) for k in graph.successors(node)]

                          ]
                            ,0)
                )
            )
        for node in graph.nodes
            if node != pair[0] and node != pair[1]
        ])
        for route in paths_combo
        for pair_index, pair in enumerate(paths_combo[route])
    ]


    s.add(
        start_and_end_are_true +
        only_one_edge_for_end +
        only_one_edge_for_start +
        exactly_two_edges +
        not_both_directions +
        zero_incoming_edge_for_start +
        zero_outgoing_edge_for_end
    )


    # -- 35 Rule out previous paths as a solution
    if previous_paths != []:
        for single_solution in previous_paths:
            s.add(
                Or([
                    Not(use_edge[route][pair_index][index])
                       for index, i in enumerate(graph.edges)
                            for route in paths_combo
                                for pair_index, pair in enumerate(paths_combo[route])
                                    if (route,pair,i) in single_solution
                ])
            )

    # -- 29 Objective: Minimize the total number of used edges
    # h = s.minimize(
    #     Sum([
    #         If(
    #             use_node[route][pair_index][node_index],
    #             1,
    #             0
    #         )
    #         for node_index,i in enumerate(graph.nodes)
    #         for route in paths_combo
    #         for pair_index,_ in enumerate(paths_combo[route])
    #     ])
    # )
    h = s.minimize(
        Sum([
            If(
                use_edge[route][path_index][edge_index],                            # -- If True ..
                edges[edge][0],                                                     # -- Then ..
                0                                                                   # -- Else ..
            )
            for edge_index, edge in enumerate(graph.edges)                          # -- For each edge
            for route in paths_combo                                                # -- For each route
            for path_index, path in enumerate(paths_combo[route])                   # -- For each path in each route
        ])
    )

    PCF = s.check()
    print('Objective function is', s.lower(h))

    if PCF == sat:
        # for route in paths_combo:
        #     for pair_index,_ in enumerate(paths_combo[route]):
        #         for index,i in enumerate(graph.edges):
        #             if s.model()[use_edge[route][pair_index][index]] == True:
        #                 print(use_edge[route][pair_index][index])
        #         for index,i in enumerate(graph.nodes):
        #             if s.model()[use_node[route][pair_index][index]] == True:
        #                 print(use_node[route][pair_index][index])

        solution = [
                    ( route, pair, edge)
                                for edge_index, edge in enumerate(graph.edges)
                                    for route in paths_combo
                                        for pair_index,pair in enumerate(paths_combo[route])
                                            if s.model()[use_edge[route][pair_index][edge_index]] == True
                    ]
    else:
        solution = []


    return PCF, solution

# previous_solutions = []
# PCF = unknown
# while PCF != unsat:
#     PCF,solution = changer(problem,previous_solutions)
#     previous_solutions.append(solution)
#     print('#####################')
