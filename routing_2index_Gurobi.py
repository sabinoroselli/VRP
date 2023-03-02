from z3 import *
from gurobipy import *

from support_functions import distance,json_parser
import networkx as nx
from itertools import permutations,combinations

def routing(edges, jobs, tasks, Autonomy, start_list, ATRs, current_path, previous_routes = []):

    m = Model('router')
    m.setParam('OutputFlag', 0)

    # i need to update this dict every time i update the current paths
    distances = {
        i: distance(current_path[i], edges)
        for i in current_path
    }

    # boolean variable that states whether a vehicle travels from customer i to customer j
    direct_travel = m.addVars(tasks,tasks,vtype=GRB.BINARY,name='direct_travel')
    # integer variable that keeps track of the arrival of vehicle k at a customer
    customer_served = m.addVars(tasks,vtype=GRB.CONTINUOUS,name='customer_serverd')
    # integer variable that keeps track of the autonomy left when arriving at a customer
    autonomy_left = m.addVars(tasks,vtype=GRB.CONTINUOUS,name='autonomy_left')

    ##### the following constraints guarantee that routes are structured as they should #####

    # --> one arrival at each customer
    one_arrival = m.addConstrs(
                quicksum([direct_travel[i,j] for i in tasks]) == 1
                for j in tasks
                if j.split('_')[0] != 'start' and j.split('_')[0] != 'end'
    )

    # guarantee the flow conservation between start and end
    flow = m.addConstrs(
        quicksum([direct_travel[i,j] for j in tasks if j.split('_')[0] != 'start' ])
        ==
        quicksum([direct_travel[j,i] for j in tasks if j.split('_')[0] != 'end' ])
        for i in tasks
        if i.split('_')[0] != 'start' and i.split('_')[0] != 'end'
    )

    # no travel from and to the same spot
    not_travel_same_spot = m.addConstrs(
        direct_travel[j,j] == 0
        for j in tasks

    )

    # no travel to the starting point
    no_travel_to_start = m.addConstrs(
        direct_travel[i,j] == 0
        for i in tasks
        for j in tasks
        if j.split('_')[0] == 'start'
    )

    # no travel from the end point
    no_travel_from_end = m.addConstrs(
        direct_travel[i,j] == 0
        for i in tasks
        for j in tasks
        if i.split('_')[0] == 'end'
    )

    # no travel from start to end (no empty routes)
    no_from_start_to_end = [
        direct_travel[i,j] == 0
        for i in tasks
        for j in tasks
        if i.split('_')[0] == 'start'
        and j.split('_')[0] == 'end'
    ]

    # set the max number of routes per each depot equal to the number of vehicles available
    max_vehicles_at_a_depot = m.addConstrs(
        quicksum([direct_travel[i,j] for j in tasks]) <= len(jobs)
        for i in tasks if i.split('_')[0] == 'start'
    )

    # routes must be closed (i.e. every vehicle that goes out has to come back)
    # THIS GIVES WEIRD OUTCOMES WHEN THERE IS ONLY ONE JOB.......FIGURE OUT WHY!!!!!!
    route_continuity = m.addConstrs(

        quicksum([ direct_travel[i,j] for j in tasks ])
        ==
        quicksum([ direct_travel[j,k] for j in tasks ])

        for i in tasks
        for k in tasks
        if i.split('_')[0] == 'start'
        and k.split('_')[0] == 'end'
        and i.split('_')[1] == k.split('_')[1]
    )

    # only allow for positive domain
    domain_1 = m.addConstrs(customer_served[j] >= 0 for j in tasks)
    domain_2 = m.addConstrs(autonomy_left[j] >= 0 for j in tasks)
    domain_3 = m.addConstrs(autonomy_left[j] <= Autonomy for j in tasks)

    # based on the direct travels, define the arrival time to a customer depending on the departure
    # time from the previous one
    infer_arrival_time = m.addConstrs(
        (direct_travel[i,j] == 1)
        >>
        (
          customer_served[j] >= customer_served[i] +
                                distances[(i,j)] +
                                jobs[i.split('_')[0] + '_' + i.split('_')[1]]['tasks'][i.split('_')[2]]['Service']
         )
        for i in tasks
        for j in tasks
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
        customer_served[t1] <= customer_served[t2]
        for t1 in tasks for t2 in tasks
        if t1.split('_')[1] == t2.split('_')[1]
        and t2.split('_')[0] != 'start'
        and t2.split('_')[0] != 'end'
        and t1.split('_')[2] in jobs['job' + '_' + t2.split('_')[1]]['tasks'][t2.split('_')[2]]['precedence']
    )

    # ATRs have to go back before they run out of energy
    autonomy = m.addConstrs(
        (direct_travel[i,j] == 1)
         >>
        ( autonomy_left[j] <= autonomy_left[i] - distances[(i,j)] )
        for i in tasks
        for j in tasks
        if i != j
        )

    #### these constraints concern creating routes that are actually executable by the ATRs ######

    # this dict holds the info about the mutual exclusive jobs
    mutual_exclusive_jobs = {
        job: [job2 for job2 in jobs if bool(set(jobs[job]['ATR']) & set(jobs[job2]['ATR'])) == False] for job in
        jobs
    }

    # tasks of mutual exclusive jobs cannot be executed on the same route (cause i need a different robot)
    mutual_exclusive = m.addConstrs(
        direct_travel[i,j] == 0
        for i in tasks
        for j in tasks
        if '{}_{}'.format(j.split('_')[0], j.split('_')[1])
           in mutual_exclusive_jobs['{}_{}'.format(i.split('_')[0], i.split('_')[1])]
    )

    # list of possible orderings of tasks belonging to the same job
    permut = {job: list(permutations([job + '_' + task for task in jobs[job]['tasks']])) for job in jobs
                            if job.split('_')[0] != 'start' and job.split('_')[0] != 'end'
              }

    # let us declare additional variables to represent the choice of one permutation
    perm = [[m.addVar(vtype=GRB.BINARY, name='perm_{}_{}'.format(i, j)) for j in permut[i]] for i in permut]
    # print(permut)

    # if a number of tasks belongs to one job, they have to take place in sequence
    for index,i in enumerate(permut):
        for jndex,j in enumerate(permut[i]):
            # print(i,j)
            m.addConstrs(
                (perm[index][jndex] == 1)
                >>
                (direct_travel[ permut[i][jndex][l], permut[i][jndex][l+1] ] == 1)
                for l in range(len(permut[i][jndex])-1)
            )

    only_one_perm = m.addConstrs(
        quicksum([perm[index][j] for j in range(len(permut[i])) ]) == 1
        for index,i in enumerate(permut)
    )

    if previous_routes != []:
        blabla = {index:i for index,i in enumerate(previous_routes)}
        excluding_previous_routes = m.addConstrs(
            quicksum([ direct_travel[ k[0], k[1] ] for k in blabla[j] ]) <= len(blabla[j]) - 1
            for j in blabla
        )

    # # the goal is to minimize the total travelled distance
    # m.setObjective(
    #     quicksum([ direct_travel[i,j] * distances[(i,j)] for i in tasks for j in tasks if i != j ])
    # )
    # alternative cost function that minimizes the number of routes
    m.setObjective(
        quicksum([direct_travel[i,j] for i in tasks for j in tasks if i.split('_')[0] == 'start'])
    )

    m.optimize()

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
                if m.getVarByName('direct_travel[{},{}]'.format(i,j)).X >= 0.5:
                    # print(m.getVarByName('direct_travel[{},{}]'.format(i,j)).VarName)
                    segments.append((i,j))
                    current_solution.append([i, j])

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
        #   element 7: routes length IN DISTANCE
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

        # for i in routes_plus:
        #     print(i)

    return routing_feasibility, routes_plus, current_solution

