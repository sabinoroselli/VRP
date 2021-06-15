from z3 import *
import networkx as nx
from support_functions import json_parser

def changer(graph, paths_combo, previous_paths=[]):

    use_node = [[[Bool('route_{}_pair_{}_node_{}'.format(route,pair,i)) for i in graph.nodes]
                 for pair in paths_combo[route]] for route in paths_combo]
    use_edge = [[[Bool('route_{}_pair_{}_edge_{}'.format(route,pair,i)) for i in graph.edges]
                 for pair in paths_combo[route]] for route in paths_combo]


    start_and_end_are_true = [
        use_node[route][index][node]
            for route in paths_combo
                for index,pair in enumerate(paths_combo[route])
                    for node in graph.nodes
                        if node in pair
    ]


    only_one_edge_for_start = [
        PbEq([(use_edge[route][pair_index][edge_index],1) for edge_index,i in enumerate(graph.edges)
                                if i in [(pair[0],j) for j in graph.successors(pair[0])]]
             ,1)
        for route in paths_combo
        for pair_index, pair in enumerate(paths_combo[route])
    ]

    only_one_edge_for_end = [
        PbEq([(use_edge[route][pair_index][edge_index],1) for edge_index,i in enumerate(graph.edges)
                                if i in [(j,pair[1]) for j in graph.predecessors(pair[1])]]
             ,1)
        for route in paths_combo
        for pair_index, pair in enumerate(paths_combo[route])
    ]

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

    s = Optimize()

    s.add(
        start_and_end_are_true +
        only_one_edge_for_end +
        only_one_edge_for_start +
        exactly_two_edges +
        not_both_directions
    )

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

    s.minimize(
        Sum([
            If(use_node[route][pair_index][edge_index],1,0)
            for edge_index,i in enumerate(graph.nodes)
            for route in paths_combo
            for pair_index,_ in enumerate(paths_combo[route])
        ])
    )

    PCF = s.check()

    if PCF == sat:
        # for route in paths_combo:
        #     for pair_index,_ in enumerate(paths_combo[route]):
        #         for index,i in enumerate(graph.edges):
        #             if s.model()[use_edge[route][pair_index][index]] == True:
        #                 print(use_edge[route][pair_index][index])
                # for index,i in enumerate(graph.nodes):
                #     if s.model()[use_node[route][pair_index][index]] == True:
                #         print(use_node[route][pair_index][index])

        solution = [
                    ( route, pair, i)
                                for index, i in enumerate(graph.edges)
                                    for route in paths_combo
                                        for pair_index,pair in enumerate(paths_combo[route])
                                            if s.model()[use_edge[route][pair_index][index]] == True
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
