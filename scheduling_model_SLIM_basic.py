from z3 import *

def schedule(locations,edges,paths_combo, paths_combo_edges, capacity_unsat_constraints, locations_plus):
    # i can now start building the model in z3. i am going to treat this part as a standard job shop problem
    # where each node/edge is a resource, each route a job and the nodes to visit are operations.
    # some operations i.e. the deliveries have time windows

    # print("LOCATIONS")
    # for i in locations:
    #     print(i,locations[i])

    hubs = list(dict.fromkeys([
        locations[i][0][0]
        for i in locations
    ]))

    # a variable for each node (operation) of each route (job)
    visit_node = [[Real('route_%s_node_%s' % (i_index, j))
                   for j,_ in enumerate(locations[i][0])]
                  for i_index, i in enumerate(locations)]

    leave_node = [[Real('leave_route_{}_node_{}'.format(i_index,j))
                   for j,_ in enumerate(locations[i][0])]
                  for i_index,i in enumerate(locations)]

    # i am going to declare a different set of variables for the edges
    visit_edge = [[Real('route_%s_edge_%s' % (i_index, j))
                   for j, _ in enumerate(locations[i][1])]
                  for i_index, i in enumerate(locations)]

    # all variable should be positive integer (really??? -.-)
    domain_scheduling_1 = [
        visit_node[i_index][j] >= 0 for i_index, i in enumerate(locations) for j, _ in enumerate(locations[i][0])
    ]

    domain_scheduling_1_dot_2 = [
        leave_node[i_index][j] >= 0 for i_index, i in enumerate(locations) for j, _ in enumerate(locations[i][0])
    ]

    domain_scheduling_2 = [
        visit_edge[i_index][j] >= 0 for i_index, i in enumerate(locations) for j, _ in enumerate(locations[i][1])
    ]
    domain_scheduling = domain_scheduling_1 + domain_scheduling_1_dot_2 + domain_scheduling_2

    # account for charging time
    charge_time = [
        visit_edge[i_index][j] >= visit_node[i_index][j] + locations[i][6][j]
        for i_index, i in enumerate(locations)
        for j,_ in enumerate(locations[i][1])
        if locations[i][6][j] > 0
    ]

    # establish precedence constraints among operations of the jobs
    visit_precedence = [
        And(
            visit_edge[i_index][j] >= visit_node[i_index][j] + locations[i][3][j],
            visit_node[i_index][j + 1] == visit_edge[i_index][j] + edges[actual_edge][0]
        )
        for i_index, i in enumerate(locations)
        for j, actual_edge in enumerate(locations[i][1])
    ]

    # some operations have time windows
    visit_tw = [
        And(
            visit_node[i_index][j_index] >= j[0],
            visit_node[i_index][j_index] <= j[1]
        )
        for i_index, i in enumerate(locations)
        for j_index, j in enumerate(locations[i][2])
        if j != 'None'
    ]

    # A vehicle leaves a node when it visits the following edge
    leaving_a_node = [
        leave_node[i_index][j] == visit_edge[i_index][j]
        for i_index, i in enumerate(locations)
        for j, actual_edge in enumerate(locations[i][1])
    ]

    # two operations cannot use the same node at the same time (unless the node is a hub)
    one_node_at_a_time = [
        Or(
            visit_node[i1][j1] >= leave_node[i2][j2] + 1,
            visit_node[i2][j2] >= leave_node[i1][j1] + 1
        )
        for i1, route1 in enumerate(locations)
        for j1, node1 in enumerate(locations[route1][0])
        for i2, route2 in enumerate(locations)
        for j2, node2 in enumerate(locations[route2][0])
        if route1 != route2
            and node1 == node2
            and node1 not in hubs
    ]

    # if two operations are going to use the same edge (from the same side), they cannot start at the same time
    edges_direct = [
        Or(
            visit_edge[i1][j1] >= visit_edge[i2][j2] + 1,
            visit_edge[i2][j2] >= visit_edge[i1][j1] + 1,
        )

        for i1, route1 in enumerate(locations)
        for j1, edge1 in enumerate(locations[route1][1])
        for i2, route2 in enumerate(locations)
        for j2, edge2 in enumerate(locations[route2][1])
        if route1 != route2
        and edge1 == edge2
        and edges[edge1][1] == 2

    ]

    edges_inverse = [
        Or(
            visit_edge[i1][j1] >= visit_edge[i2][j2] + edges[edge2][0],
            visit_edge[i2][j2] >= visit_edge[i1][j1] + edges[edge1][0],
        )

        for i1, route1 in enumerate(locations)
        for j1, edge1 in enumerate(locations[route1][1])
        for i2, route2 in enumerate(locations)
        for j2, edge2 in enumerate(locations[route2][1])
        if route1 != route2
        and edge1[0] == edge2[1] and edge1[1] == edge2[0]
        and edges[edge1][1] == 2
    ]

    # HERE I BUILD UP THE MODEL FOR THE SCHEDULING PROBLEM
    set_option(rational_to_decimal=True)
    set_option(precision=2)
    scheduling = Optimize()

    constraints = {
        'domain_scheduling': domain_scheduling,
        'visit_precedence': visit_precedence,
        'charge_time': charge_time,
        'visit_tw': visit_tw,
        'leaving_a_node': leaving_a_node,
        'one_node_at_the_time': one_node_at_a_time,
        'edges_direct': edges_direct,
        'edges_inverse': edges_inverse
    }

    to_track = [
        'edges_inverse',
        'edges_direct',
        'one_node_at_the_time'
    ]

    # IF I JUST WANT TO ASSERT THE CONSTRAINTS...
    for i in constraints:
        scheduling.add(constraints[i])

    # IF I WANT TO TRACK THEM IN CASE THE PROBLEM IS UNSAT...
    # for cons in constraints:
    #     for index,i in enumerate(constraints[cons]):
    #         scheduling.assert_and_track(i,cons + '-{}'.format(str(index)))

    ############ THIS I NEED ONLY WHEN I SCHEDULE FOR SEQUENCE PLANNER ###############
    scheduling.minimize(Sum([
        visit_node[i_index][j]
        for i_index, i in enumerate(locations)
        for j, _ in enumerate(locations[i][0])

    ]))

    nodes_schedule = {}
    edges_schedule = []
    scheduling_feasibility = scheduling.check()
    if scheduling_feasibility == sat:
        m3 = scheduling.model()
        for i_index, i in enumerate(locations):
            for j_index, j in enumerate(locations[i][0]):
                # print(j_index)
                nodes_schedule.update(
                    # (
                    #     'vehicle_%s_visits_node_%s: ' % (i, j),
                    #     m3[visit_node[i_index][j_index]]
                    # )
                {
                    (i,j_index):(j, m3[visit_node[i_index][j_index]])
                }
                )
                # print(
                #     'vehicle_%s_visits_node_%s: ' % (i, j),
                #     m3[visit_node[i_index][j_index]]
                # )
        for i_index, i in enumerate(locations):
            for j_index, j in enumerate(locations[i][1]):
                edges_schedule.append(
                    (
                        'vehicle_%s_visits_edge_%s: ' % (i, j),
                        m3[visit_edge[i_index][j_index]]
                    )
                )
    else:

        UC = scheduling.unsat_core()
        # for i in UC:
        #     if str(i).split('-')[0] in to_track:
        #         print(i)
        #         print(constraints[str(i).split('-')[0]][int(str(i).split('-')[1])])

    return scheduling_feasibility,nodes_schedule,edges_schedule,capacity_unsat_constraints
