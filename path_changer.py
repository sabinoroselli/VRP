from z3 import *

# ORIGINAL PATHS CHANGING FUNCTION
# def changer(graph, paths_combo, previous_paths=[]):

# UNSAT CORE GUIDED PATHS SEARCH
def changer(graph, paths_combo, previous_paths=[],
            UGS = False, capacity_unsat_constraints = [],
            locations = [], edges = [], paths_combo_edges = []):

    use_node = [[[Bool('route_{}_pair_{}_node_{}'.format(route,pair,i)) for i in graph.nodes]
                 for pair in paths_combo[route]] for route in paths_combo]
    use_edge = [[[Bool('route_{}_pair_{}_edge_{}'.format(route,pair,i)) for i in graph.edges]
                 for pair in paths_combo[route]] for route in paths_combo]

    node_used = [Int('node_{}'.format(node)) for node in graph.nodes]
    edge_used = [Int('edge_{}'.format(edge)) for edge in graph.edges]


    start_and_end_are_true = [
        use_node[route_i][index][node_index]
            for route_i,route in enumerate(paths_combo)
                for index,pair in enumerate(paths_combo[route])
                    for node_index,node in enumerate(graph.nodes)
                        if node in pair
    ]


    only_one_edge_for_start = [
        PbEq([(use_edge[route_i][pair_index][edge_index],1) for edge_index,i in enumerate(graph.edges)
                                if i in [(pair[0],j) for j in graph.successors(pair[0])]]
             ,1)
        for route_i,route in enumerate(paths_combo)
        for pair_index, pair in enumerate(paths_combo[route])
    ]

    # -- 31.B Exactly zero incoming edges are used for the start node of each route (not every pair, only first)
    # -- !! THIS CONSTRAINT WASN'T PRESENT IN THE ORIGINAL MODEL
    zero_incoming_edge_for_start = [
        PbEq([(use_edge[route_i][pair_index][edge_index], 1) for edge_index, i in enumerate(graph.edges)
              if i in [(j, pair[0]) for j in graph.successors(pair[0])]]
             , 0)
        for route_i,route in enumerate(paths_combo)
        for pair_index, pair in enumerate(paths_combo[route])
        # if pair_index == 0
    ]

    only_one_edge_for_end = [
        PbEq([(use_edge[route_i][pair_index][edge_index],1) for edge_index,i in enumerate(graph.edges)
                                if i in [(j,pair[1]) for j in graph.predecessors(pair[1])]]
             ,1)
        for route_i,route in enumerate(paths_combo)
        for pair_index, pair in enumerate(paths_combo[route])
    ]

    # -- 32.B Exactly zero outgoing edges are used for the end node of each route (not every pair, only first)
    # -- !! THIS CONSTRAINT WASN'T PRESENT IN THE ORIGINAL MODEL
    zero_outgoing_edge_for_end = [
        PbEq([(use_edge[route_i][pair_index][edge_index], 1) for edge_index, i in enumerate(graph.edges)
              if i in [(pair[1], j) for j in graph.successors(pair[1])]]
             , 0)
        for route_i,route in enumerate(paths_combo)
        for pair_index, pair in enumerate(paths_combo[route])
        # if pair_index == (len(paths_combo[route])-1)
    ]

    exactly_two_edges = [
        And([
                If(
                use_node[route_i][pair_index][node_index],
                And(
                    PbEq([(use_edge[route_i][pair_index][edge_index],1) for edge_index,j in enumerate(graph.edges)
                                                if j in [(k,node) for k in graph.predecessors(node)]
                         ]
                             ,1),
                    PbEq([(use_edge[route_i][pair_index][edge_index],1) for edge_index,j in enumerate(graph.edges)
                                                if j in [(node,k) for k in graph.successors(node)]
                          ]
                             ,1)
                ),
                And(
                    PbEq([(use_edge[route_i][pair_index][edge_index], 1) for edge_index, j in enumerate(graph.edges)
                                                if j in [(k, node) for k in graph.predecessors(node)]
                          ]
                            ,0),
                    PbEq([(use_edge[route_i][pair_index][edge_index], 1) for edge_index, j in enumerate(graph.edges)
                                                if j in [(node, k) for k in graph.successors(node)]

                          ]
                            ,0)
                )
            )
        for node_index,node in enumerate(graph.nodes)
            if node != pair[0] and node != pair[1]
        ])
        for route_i,route in enumerate(paths_combo)
        for pair_index, pair in enumerate(paths_combo[route])
    ]

    not_both_directions = [
        Implies(
            use_edge[route_i][pair_index][index_i],
            Not(use_edge[route_i][pair_index][index_j])
        )
        for route_i,route in enumerate(paths_combo)
        for pair_index, pair in enumerate(paths_combo[route])
        for index_i,i in enumerate(graph.edges)
        for index_j,j in enumerate(graph.edges)
        if (j[0],j[1]) == (i[1],i[0])
    ]

    shared_nodes = [
        # node_used[node_index]
        # ==
        # Sum([
        #     If(
        #         Sum([ use_node[route_i][index][node_index] for index, pair in enumerate(paths_combo[route]) ]) > 0,
        #         1,
        #         0
        #     )
        #     for route_i, route in enumerate(paths_combo)
        # ])
        # for node_index,node in enumerate(graph.nodes)

    ]

    shared_edges = [
        # edge_used[index_i]
        # ==
        # Sum([
        #     If(
        #         Sum([use_edge[route_i][index][index_i] for index, pair in enumerate(paths_combo[route])]) > 0,
        #         1,
        #         0
        #     )
        #     for route_i, route in enumerate(paths_combo)
        # ])
        # for index_i,i in enumerate(graph.edges)

    ]

    s = Optimize()

    s.add(
        start_and_end_are_true +
        only_one_edge_for_end +
        only_one_edge_for_start +
        zero_incoming_edge_for_start +
        zero_outgoing_edge_for_end +
        exactly_two_edges +
        not_both_directions #+
        # shared_nodes +
        # shared_edges
    )
    # print(paths_combo)
    # print(paths_combo_edges)
    # print(locations)

    # -- Capacity constraints for edges: at least one of the conflicting routes/pairs must be False
    if UGS == True:
        buffer = []
        for route_index1, route1 in enumerate(paths_combo_edges):
            for pair_index1, pair1 in enumerate(paths_combo_edges[route1]):
                for edge_index1, edge1 in enumerate(graph.edges):

                    for constraint in capacity_unsat_constraints:
                        if 'r{}_p{}_e{}'.format(route_index1, pair1, edge1) in constraint:
                            buffer.append(Not(use_edge[route_index1][pair_index1][edge_index1]))
        if len(buffer) > 0:
            s.add(Or(buffer))
        buffer_2 = []
        for route_index1, route1 in enumerate(paths_combo_edges):
            for pair_index1, pair1 in enumerate(paths_combo[route1]):
                for node_index1, node1 in enumerate(graph.nodes):

                    for constraint in capacity_unsat_constraints:
                        if 'r{}_p{}_e{}'.format(route_index1, pair1, node1) in constraint:
                            buffer_2.append(Not(use_node[route_index1][pair_index1][node_index1]))
        if len(buffer_2) > 0:
            s.add(Or(buffer_2))
    if previous_paths != []:
        for single_solution in previous_paths:
            s.add(
                Or([
                    Not(use_edge[route_i][pair_index][index])
                       for index, i in enumerate(graph.edges)
                            for route_i,route in enumerate(paths_combo)
                                for pair_index, pair in enumerate(paths_combo[route])
                                    if (route,pair,i) in single_solution
                ])
            )

    s.minimize(
        Sum([
            use_edge[route_i][pair_index][edge_index] * graph.get_edge_data(*i)['weight']  #edges[i][0]
            for edge_index,i in enumerate(graph.edges)
            for route_i,route in enumerate(paths_combo)
            for pair_index,_ in enumerate(paths_combo[route])
        ])
        # +
        # Sum([
        #     edge_used[edge_index]
        #     for edge_index, i in enumerate(graph.edges)
        # ])
        # +
        # Sum([
        #     node_used[node]
        #     for node,_ in enumerate(graph.nodes)
        # ])
    )

    PCF = s.check()

    if PCF == sat:

        solution = [
                    ( route, pair, i)
                                for index, i in enumerate(graph.edges)
                                    for route_i,route in enumerate(paths_combo)
                                        for pair_index,pair in enumerate(paths_combo[route])
                                            if s.model()[use_edge[route_i][pair_index][index]] == True
                    ]
    else:
        solution = []

    return PCF, solution