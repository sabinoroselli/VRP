from z3 import *
from gurobipy import *
from support_functions import distance,json_parser
import networkx as nx
from itertools import permutations,combinations


def routing(edges, jobs, tasks, Autonomy, start_list, ATRs, current_path, previous_routes = []):

    m = Model('router')
    m.setParam('OutputFlag', 0)

    vehicles = {vehicle + '_' + str(unit): start_list[vehicle]
                     for vehicle in ATRs for unit in range(ATRs[vehicle]['units'])}

    # i need to update this dict every time i update the current paths
    distances = {
        i: distance(current_path[i], edges)
        for i in current_path
    }

    max_routes = len([job for job in jobs if job.split('_')[0] == 'job'])

    # integer variable that states whether a vehicle travels from customer i to customer j
    direct_travel = m.addVars(max_routes,tasks,tasks,vtype=GRB.BINARY,name='direct_travel')

    # integer variable that keeps track of the arrival of vehicle k at a customer
    customer_served = m.addVars(tasks,vtype=GRB.CONTINUOUS,name='customer_served')
    # integer variable that keeps track of the autonomy left when arriving at a customer
    autonomy_left = m.addVars(max_routes,tasks,vtype=GRB.CONTINUOUS,name='autonomy_left')

    # one arrival at each customer
    one_arrival = m.addConstrs(
            quicksum([direct_travel[i,j,k] for i in range(max_routes) for j in tasks]) == 1
            for k in tasks
            if k.split('_')[0] != 'start' and k.split('_')[0] != 'end'
    )


    # guarantee the flow conservation between start and end
    flow = m.addConstrs(
        quicksum([direct_travel[k,i,j] for j in tasks if j.split('_')[0] != 'start'])
        ==
        quicksum([direct_travel[k, j, i] for j in tasks if j.split('_')[0] != 'end'])
        for k in range(max_routes)
        for i in tasks
        if i.split('_')[0] != 'start' and i.split('_')[0] != 'end'
    )

    # no travel from and to the same spot
    not_travel_same_spot = m.addConstrs(
        direct_travel[i,j,j] == 0
        for i in range(max_routes)
        for j in tasks
    )

    # no travel to the starting point
    no_travel_to_start = m.addConstrs(
        direct_travel[k,i,j] == 0
        for k in range(max_routes)
        for i in tasks
        for j in tasks
        if j.split('_')[0] == 'start'
    )

    # no travel from the end point
    no_travel_from_end = m.addConstrs(
        direct_travel[k,i,j] == 0
        for k in range(max_routes)
        for i in tasks
        for j in tasks
        if i.split('_')[0] == 'end'
    )

    # no travel from start to end (no empty routes)
    no_from_start_to_end = m.addConstrs(
        direct_travel[k,i,j] == 0
        for k in range(max_routes)
        for i in tasks
        for j in tasks
        if i.split('_')[0] == 'start'
        and j.split('_')[0] == 'end'
    )

    # only allow for positive domain

    domain = m.addConstrs(
        autonomy_left[i, j] <= Autonomy for i in range(max_routes) for j in tasks
    )

    # based on the direct travels, define the arrival time to a customer depending on the departure time from the previous
    infer_arrival_time = m.addConstrs(
        (direct_travel[k,i,j] == 1)
        >>
        (customer_served[j] >= customer_served[i] +
                                distances[(i,j)] +
                                jobs[i.split('_')[0] + '_' + i.split('_')[1]]['tasks'][i.split('_')[2]]['Service']
         )
        for k in range(max_routes)
        for i in tasks
        for j in tasks
        # if i.split('_')[0] != 'start'
        # and i.split('_')[0] != 'end'
        if i != j
    )

    # set the arrival time within the time window for each customer
    time_window_1 = m.addConstrs(
        customer_served[j] >= jobs[j.split('_')[0] + '_' + j.split('_')[1]]['tasks'][j.split('_')[2]]['TW'][0]
        for j in tasks
        if jobs[j.split('_')[0] + '_' + j.split('_')[1]]['tasks'][j.split('_')[2]]['TW'] != 'None'
    )

    time_window_2 = m.addConstrs(
        customer_served[j] <= jobs[j.split('_')[0] + '_' + j.split('_')[1]]['tasks'][j.split('_')[2]]['TW'][1]
        for j in tasks
        if jobs[j.split('_')[0] + '_' + j.split('_')[1]]['tasks'][j.split('_')[2]]['TW'] != 'None'
    )

    # constraint over arrival time when precedence is required
    # i assume that precedence constraints can only be among tasks of the same job
    precedence = m.addConstrs(
        customer_served[j1] <= customer_served[j2]
        for j1 in tasks
        for j2 in tasks
        if j1.split('_')[1] == j2.split('_')[1]
        and j2.split('_')[0] != 'start'
        and j2.split('_')[0] != 'end'
        and j1.split('_')[2] in jobs['job' + '_' + j2.split('_')[1]]['tasks'][j2.split('_')[2]]['precedence']
    )

    # ATRs have to go back before they run out of energy
    autonomy = m.addConstrs(
        (direct_travel[k,i,j] == 1)
        >>
        (autonomy_left[k,j] <= autonomy_left[k,i] - distances[(i,j)])
        for k in range(max_routes)
        for i in tasks
        for j in tasks
        if i != j
    )

    # this dict holds the info about the mutual exclusive jobs
    mutual_exclusive_jobs = {
        job: [job2 for job2 in jobs if bool(set(jobs[job]['ATR']) & set(jobs[job2]['ATR'])) == False] for job in
        jobs
    }

    # tasks of mutual exclusive jobs cannot be executed on the same route (cause i need a different robot)
    mutual_exclusive = m.addConstrs(
        direct_travel[k,i,j] == 0
        for k in range(max_routes)
        for i in tasks
        for j in tasks
        if '{}_{}'.format(j.split('_')[0], j.split('_')[1])
        in mutual_exclusive_jobs['{}_{}'.format(i.split('_')[0], i.split('_')[1])]
    )

    # list of possible orderings of tasks belonging to the same job
    permut = { job: list(permutations([job + '_' + task for task in jobs[job]['tasks']]))
               for job in jobs if job.split('_')[0] != 'start' and job.split('_')[0] != 'end' }

    # let us declare additional variables to represent the choice of one permutation
    perm = [[m.addVar(vtype=GRB.BINARY,name='perm_{}_{}'.format(i,j))   for j in permut[i] ]  for i in permut ]

    # if a number of tasks belongs to one job, they have to take place in sequence
    for index,i in enumerate(permut):
        for jndex,j in enumerate(permut[i]):
            m.addConstrs(
                (perm[index][jndex] == 1)
                >>
                (quicksum([
                    direct_travel[ k, permut[i][jndex][l], permut[i][jndex][l+1] ] for k in range(max_routes)
                ]) == 1)
                for l in range(len(permut[i][jndex])-1)
            )
    only_one_perm = m.addConstrs(
        quicksum([perm[index][j] for j in range(len(permut[i])) ]) == 1
        for index,i in enumerate(permut)
    )
    # OBSOLETE VERSION
    # routes must be closed (i.e. every vehicle that goes out has to come back)

    # route_countinuity_1 = m.addConstrs(
    #     quicksum([direct_travel[k,i,j] for j in tasks]) == 0
    #     for k in vehicles
    #     for i in tasks
    #     if i.split('_')[0] == 'start'
    #     and tasks[i] != vehicles[k]
    # )
    #
    # route_countinuity_2 = m.addConstrs(
    #     quicksum([direct_travel[k, j, i] for j in tasks]) == 0
    #     for k in vehicles
    #     for i in tasks
    #     if i.split('_')[0] == 'end'
    #     and tasks[i] != vehicles[k]
    # )


    route_continuity = m.addConstrs(

        quicksum([direct_travel[k,i,j] for j in tasks])
        ==
        quicksum([ direct_travel[k,l,m] for l in tasks ])

        for k in range(max_routes)
        for i in tasks
        for m in tasks
        if i.split('_')[0] == 'start'
        and m.split('_')[0] == 'end'
        and tasks[i] == tasks[m]
    )

    #a route can start exactly once
    one_route_one_start = m.addConstrs(
        quicksum([direct_travel[k,i,j] for k in range(max_routes) ]) <= 1
        for i in tasks
        for j in tasks
    )

    if previous_routes != []:
        blabla = {index:i for index,i in enumerate(previous_routes)}
        excluding_previous_routes = m.addConstrs(
            quicksum([ direct_travel[ k[0], k[1], k[2] ] for k in blabla[j] ]) <= len(blabla[j]) - 1
            for j in blabla
        )

    # the cost function is the number of routes
    m.setObjective(
        quicksum([
            direct_travel[k,i,j]
        for k in range(max_routes)
        for i in tasks
        for j in tasks
        if i.split('_')[0] == 'start' ])
    )

    # # alternative cost function is the total travelled distance
    # m.setObjective(
    #     quicksum([
    #         direct_travel[k, i, j] * distances[(i,j)]
    #         for k in range(max_routes)
    #         for i in tasks
    #         for j in tasks
    #         if i != j
    #            ])
    # )

    m.optimize()

    # print(m.getVarByName('direct_travel[0,job_1_1,job_1_1]').X)
    # print('INFEASIBLE',m.status == GRB.INFEASIBLE)
    # print('OPTIMAL',m.status == GRB.OPTIMAL)
    routes_plus = []
    # this list will be use to store the current solution for future runs of the solver
    current_solution = []

    if m.status != GRB.INFEASIBLE:
        routing_feasibility = sat
        # route stores the info about each route that i generated with the VRPTW extended model
        routes = []
        # segments stores the info o each direct travel from a task location to another
        segments = []
        # here i populate the list based on the variable that evaluated to true in the model
        for i in tasks:
            for j in tasks:
                for k in range(max_routes):
                    # print(k,i,j,m.getVarByName('direct_travel[{},{},{}]'.format(k,i,j)).X)
                    if m.getVarByName('direct_travel[{},{},{}]'.format(k,i,j)).X >= 0.5:
                        # print(m.getVarByName('direct_travel[{},{},{}]'.format(k,i,j)).VarName)
                        segments.append((i,j))
                        current_solution.append([k, i, j])
        ########### IN CASE I WANNA TAKE A LOOK AT THE SOLUTION ####################
        # for i in tasks:
        #     print(i,m.getVarByName('customer_served[{}]'.format(i)).X)
        # for i in tasks:
        #     for k in vehicles:
        #         print(k,i,m.getVarByName('autonomy_left[{},{}]'.format(k,i)).X)

        # here i start forming the routes by adding the direct travels that begin from the start point
        for i in segments:
            if i[0].split('_')[0] == 'start':
                routes.append([i])

        # here i concatenate the routes by matching the last location of a direct travel with the first of another one
        for j in routes:
            while j[-1][1].split('_')[0] != 'end':
                for i in segments:
                    if i[0] == j[-1][1]:
                        j.append(i)

        # let's just change the format of storing the routes
        routes_2 = [[route[0][0]] for route in routes]

        for route1, route2 in zip(routes, routes_2):
            for segment in route1:
                route2.append(segment[1])
        # assign routes_2 to routes and keep using routes
        routes = routes_2

        # this list tells the distance between each two locations based on the route
        # first step: calculate distance from one location to the following
        routes_length = [
            [
                distance(current_path[elem1, elem2], edges)
                for elem1, elem2 in zip(route[:-1], route[1:])
            ]
            for route in routes
        ]

        # step two: iteratively sum the one value with the previous one
        routes_length = [
            [elem[i] + sum([elem[j] for j in range(i)]) for i in range(len(elem))]
            for elem in routes_length
        ]

        # this list tells how long it takes to reach each location based on the route
        # first step: calculate how long it takes from one location to the following
        # (same as routes_length but this also accounts for the time I spend at one location servicing the task)
        arrivals = [
            [
                distance(current_path[elem1, elem2], edges)
                +
                jobs[elem1.split('_')[0] + '_' + elem1.split('_')[1]]
                ['tasks']
                [elem1.split('_')[2]]['Service']

                for elem1, elem2 in zip(route[:-1], route[1:])
            ]
            for route in routes
        ]

        # step two: iteratively sum the one value with the previous one
        arrivals = [
            [elem[i] + sum([elem[j] for j in range(i)]) for i in range(len(elem))]
            for elem in arrivals
        ]

        # this list tells which resources can execute each task
        eligible = [
            set.intersection(
                *[set(
                    jobs['%s_%s' % (segment.split('_')[0], segment.split('_')[1])]['ATR']
                ) for segment in route]
            )
            for route in routes
        ]

        # this list tells me the actual nodes that the vehicles must visit to execute the route and if
        # the node has a time window ('None' otherwise)
        actual_nodes = []
        for route in routes:
            points = [jobs[route[0].split('_')[0] + '_' + route[0].split('_')[1]]['tasks']['0']['location']]
            tws = ['None']
            St = [0]
            for segment1, segment2 in zip(route[:-1], route[1:]):
                points += current_path[
                              segment1,
                              segment2
                          ][1:]
                for _ in current_path[
                             segment1,
                             segment2
                         ][1:]:
                    tws.append('None')
                    St.append(0)
                tws[-1] = jobs[segment2.split('_')[0] + '_' + segment2.split('_')[1]]['tasks'][segment2.split('_')[2]][
                    'TW']
                St[-1] = jobs[segment2.split('_')[0] + '_' + segment2.split('_')[1]]['tasks'][segment2.split('_')[2]][
                    'Service']
            actual_nodes.append((points, tws, St))

        # I need to keep track of the cumulative service time.
        cumulative_service_time = [
            sum([
                jobs[task.split('_')[0] + '_' + task.split('_')[1]]
                ['tasks']
                [task.split('_')[2]]['Service']
                for task in route
            ])
            for route in routes
        ]

        # finally the list of routes:
        #   element 1: sublist of direct travels in the route (i won't need it for the job shop problem, but maybe later on)
        #   element 2: route length IN TIME
        #   element 3: latest start for the job that still allows to meet the stricter deadline
        #   element 4: sublist of eligible ATRs (resources) for the job
        #   element 5: sublist of nodes to visit and their time window
        #   element 6: cumulative service time
        #   element 7: route length IN DISTANCE
        routes_plus = [
            [
                route,
                arrivals[index][-1],
                min([
                    jobs[
                        segment.split('_')[0] + '_' + segment.split('_')[1]
                        ]['tasks'][segment.split('_')[2]]['TW'][1]
                    -
                    arrivals[index][oth_ind]
                    for oth_ind, segment in enumerate(route[1:])
                    if jobs[
                        segment.split('_')[0] + '_' + segment.split('_')[1]
                        ]['tasks'][segment.split('_')[2]]['TW'] != 'None'
                ]),
                list(eligible[index]),
                actual_nodes[index],
                cumulative_service_time[index],
                routes_length[index][-1]
            ]
            for index, route in enumerate(routes)
        ]
    else:
        routing_feasibility = unsat

    return routing_feasibility, routes_plus, current_solution


# # the specific problem instance i am solving
# # problem = 'MM_counter_example'
# # problem = 'MM_1535_0_30_9'
# problem = 'MM_2547_50_30_7'
# # problem = 'MM_3568_0_60_5'
# # problem = 'MM_351115_50_300_9'
# # problem = "T-ASE_test_case_1"

# previous_routes = []
#
# # first of all, let's parse the json file with the plant layout and the jobs info
# jobs, nodes, edges, Autonomy, ATRs, charging_coefficient, start_list = json_parser('test_cases/%s.json' % problem)
#
# # print(ATRs)
# # print(jobs)
#
# # now let's build the graph out of nodes and edges
# graph = nx.DiGraph()
# graph.add_nodes_from(nodes)
# graph.add_weighted_edges_from([
#     (i[0], i[1], edges[i][0]) for i in edges
# ])
#
# # i am flattening the jobs and their task to calculate distances between any two interest point
# tasks = {j + '_' + i: jobs[j]['tasks'][i]['location'] for j in jobs for i in jobs[j]['tasks']}
# combination = {i: (tasks[i[0]], tasks[i[1]]) for i in combinations(tasks, 2)}
# print(tasks)
# # here I compute the shortest paths between any two customers
# shortest_paths = {
#     (i[0], i[1]): nx.shortest_path(graph, combination[i][0], combination[i][1], weight='weight')
#     for i in combination
# }
# shortest_paths.update({
#     (i[1], i[0]): nx.shortest_path(graph, combination[i][1], combination[i][0], weight='weight')
#     for i in combination
#     # if k_shortest_paths(graph,combination[i][0],combination[i][1],K,weight='weight') != []
# })
#
# current_path = shortest_paths

# routing_feasibility, routes_plus, current_solution = routing(edges,jobs,tasks,Autonomy,current_path,previous_routes)
#
# print(routing_feasibility)
# for i in routes_plus:
#     print(i[:4])
