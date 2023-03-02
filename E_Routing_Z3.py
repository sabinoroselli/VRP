from z3 import *
from gurobipy import *
from support_functions import distance,json_parser
import networkx as nx
from itertools import permutations,combinations
import math


def routing(edges, jobs, tasks, Autonomy, charging_coefficient, start_list, ATRs, current_path, previous_routes = []):

    m = Model('router')
    m.setParam('OutputFlag', 0)

    vehicles = {vehicle + '_' + str(unit): start_list[vehicle]
                     for vehicle in ATRs for unit in range(ATRs[vehicle]['units'])}

    # i need to update this dict every time i update the current paths
    distances = {
        i: distance(current_path[i], edges)
        for i in current_path
    }

    # max_routes = len([job for job in jobs if job.split('_')[0] == 'job'])

    # binary variable that states whether a vehicle travels from customer i to customer j
    direct_travel = m.addVars(vehicles,tasks,tasks,vtype=GRB.BINARY,name='direct_travel')

    # continuous variable that keeps track of the arrival of vehicle k at a customer
    customer_served = m.addVars(tasks,vtype=GRB.CONTINUOUS,name='customer_served')
    # continuous variable that keeps track of the autonomy left when arriving at a customer
    autonomy_left = m.addVars(vehicles,tasks,vtype=GRB.CONTINUOUS,name='autonomy_left')
    # integer variable that keeps track of the needed to charge
    charging_time = m.addVars(vehicles, tasks, vtype=GRB.INTEGER, name='charging_time')

    # 28 the cost function is number of visits to the recharge station while at the same time minimizing
    # the travelling distance
    m.setObjective(
        quicksum([
            direct_travel[k, i, j]
            for k in vehicles
            for i in tasks
            for j in tasks
            if j.split('_')[0] == 'recharge'])
        +
        quicksum([
            direct_travel[k, i, j] * distances[(i, j)]
            for k in vehicles
            for i in tasks
            for j in tasks
            if i != j
        ])
        # THIS TERM IS ONLY USED FOR GPSS, where i want the vehicles to return as fast as possible to the depots
        # +
        # quicksum([customer_served[i] for i in tasks if i.split('_')[0] == 'recharge'])
    )

    # 29 no travel from and to the same spot
    not_travel_same_spot = m.addConstrs(
        direct_travel[i, j, j] == 0
        for i in vehicles
        for j in tasks
    )

    # 30 no travel to the starting point
    no_travel_to_start = m.addConstrs(
        direct_travel[k, i, j] == 0
        for k in vehicles
        for i in tasks
        for j in tasks
        if j.split('_')[0] == 'start'
    )

    # 31 no travel from the end point
    no_travel_from_end = m.addConstrs(
        direct_travel[k, i, j] == 0
        for k in vehicles
        for i in tasks
        for j in tasks
        if i.split('_')[0] == 'end'
    )

    # 32 tasks of mutual exclusive jobs cannot be executed on the same route (cause i need a different robot)
    mutual_exclusive = m.addConstrs(
        quicksum(direct_travel[k, i, j] for i in tasks) == 0
        for k in vehicles
        for j in tasks
        if '_'.join(k.split('_')[:-1]) not in jobs['_'.join(j.split('_')[:-1])]['ATR']
    )


    # 33 the operating range cannot exceed the given value
    domain = m.addConstrs(
        autonomy_left[i, j] <= Autonomy for i in vehicles for j in tasks
    )

    # 34 constraint over arrival time when precedence is required
    # i assume that precedence constraints can only be among tasks of the same job
    precedence = m.addConstrs(
        customer_served[j1] <= customer_served[j2]
        for j1 in tasks
        for j2 in tasks
        if j1.split('_')[1] == j2.split('_')[1]
        # and j1.split('_')[0] != 'recharge'
        and j2.split('_')[0] != 'recharge'
        and j2.split('_')[0] != 'start'
        and j2.split('_')[0] != 'end'
        and j1.split('_')[2] in jobs['_'.join(j2.split('_')[:-1])]['tasks'][j2.split('_')[-1]]['precedence']
    )

    # 35.1 set the arrival time within the time window for each customer
    time_window_1 = m.addConstrs(
        customer_served[j] >= jobs['_'.join(j.split('_')[:-1])]['tasks'][j.split('_')[-1]]['TW'][0]
        for j in tasks
        if j.split('_')[0] != 'recharge'
        if jobs['_'.join(j.split('_')[:-1])]['tasks'][j.split('_')[-1]]['TW'] != 'None'
    )
    # 35.2 latest arrival time
    time_window_2 = m.addConstrs(
        customer_served[j] <= jobs['_'.join(j.split('_')[:-1])]['tasks'][j.split('_')[-1]]['TW'][1]
        for j in tasks
        if j.split('_')[0] != 'recharge'
        if jobs['_'.join(j.split('_')[:-1])]['tasks'][j.split('_')[-1]]['TW'] != 'None'
    )

    # 36 based on the direct travels, define the arrival time to a customer depending on the departure time from the previous
    infer_arrival_time = m.addConstrs(
        (direct_travel[k,i,j] == 1)
        >>
        (customer_served[j] >= customer_served[i] +
                                distances[(i,j)] +
                                jobs['_'.join(i.split('_')[:-1])]['tasks'][i.split('_')[-1]]['Service']
         )
        for k in vehicles
        for i in tasks
        for j in tasks
        if i != j
        and i.split('_')[0] != 'recharge'
    )

    # 37 auxiliary constraint to connect charging time and state of charge
    charging_time_constraint = m.addConstrs(
        charging_time[k,i] >= (1 / charging_coefficient) * (Autonomy - autonomy_left[k, i])
        for k in vehicles
        for i in tasks
        if i.split('_')[0] == 'recharge'
    )

    # 38 arrival time for charging stations
    infer_arrival_time_2 = m.addConstrs(
        (direct_travel[k, i, j] == 1)
        >>
        ( customer_served[j] >= customer_served[i] +
                                distances[(i, j)] +
                                charging_time[k,i]
          )
        for k in vehicles
        for i in tasks
        for j in tasks
        if i != j
        and i.split('_')[0] == 'recharge'
    )

    # 39 The following two constraints model how energy is consumed by travelling and accumulated again by visiting the
    # charging stations
    autonomy = m.addConstrs(
        (direct_travel[k,i,j] == 1)
        >>
        (autonomy_left[k,j] <= autonomy_left[k,i] - distances[(i,j)])
        for k in vehicles
        for i in tasks
        for j in tasks
        if i != j
        and i.split('_')[0] != 'recharge'
    )
    # 40
    autonomy_2 = m.addConstrs(
        (direct_travel[k, i, j] == 1)
        >>
        (autonomy_left[k, j] <= Autonomy - distances[(i, j)])
        for k in vehicles
        for i in tasks
        for j in tasks
        if i != j
        and i.split('_')[0] == 'recharge'
    )

    # 41 one arrival at each customer
    one_arrival = m.addConstrs(
        quicksum([direct_travel[i, j, k] for i in vehicles for j in tasks]) == 1
        for k in tasks
        if k.split('_')[0] != 'start'
        and k.split('_')[0] != 'end'
        and k.split('_')[0] != 'recharge'
    )

    # 42 at most one arrival
    one_arrival_2 = m.addConstrs(
        quicksum([direct_travel[i, j, k] for i in vehicles for j in tasks]) <= 1
        for k in tasks
        if k.split('_')[0] == 'recharge'
    )

    # 43 guarantee the flow conservation between start and end
    flow = m.addConstrs(
        quicksum([direct_travel[k, i, j] for j in tasks if j.split('_')[0] != 'start'])
        ==
        quicksum([direct_travel[k, j, i] for j in tasks if j.split('_')[0] != 'end'])
        for k in vehicles
        for i in tasks
        if i.split('_')[0] != 'start'
        and i.split('_')[0] != 'end'
    )

    # 44 routes must be closed (i.e. every vehicle that goes out has to come back)
    route_continuity = m.addConstrs(
        quicksum([direct_travel[k, i, j] for j in tasks])
        ==
        quicksum([direct_travel[k, l, m] for l in tasks])

        for k in vehicles
        for i in tasks
        for m in tasks
        if i.split('_')[0] == 'start'
        and m.split('_')[0] == 'end'
        and tasks[i] == tasks[m]
    )

    # list of possible orderings of tasks belonging to the same job
    permut = { job: list(permutations([job + '_' + task for task in jobs[job]['tasks']]))
               for job in jobs if job.split('_')[0] != 'start'
                                and job.split('_')[0] != 'end'
                                and job.split('_')[0] != 'recharge'
               }

    # let us declare additional variables to represent the choice of one permutation
    perm = [[m.addVar(vtype=GRB.BINARY,name='perm_{}_{}'.format(i,j))   for j in permut[i] ]  for i in permut ]

    # 45 if a number of tasks belongs to one job, they have to take place in sequence
    for index,i in enumerate(permut):
        for jndex,j in enumerate(permut[i]):
            m.addConstrs(
                (perm[index][jndex] == 1)
                >>
                (quicksum([
                    direct_travel[ k, permut[i][jndex][l], permut[i][jndex][l+1] ] for k in vehicles
                ]) == 1)
                for l in range(len(permut[i][jndex])-1)
            )

    # 46
    only_one_perm = m.addConstrs(
        quicksum([perm[index][j] for j in range(len(permut[i])) ]) == 1
        for index,i in enumerate(permut)
    )

    # 47 excluding previous routes
    if previous_routes != []:
        blabla = {index:i for index,i in enumerate(previous_routes)}
        excluding_previous_routes = m.addConstrs(
            quicksum([ direct_travel[ k[0], k[1], k[2] ] for k in blabla[j] ]) <= len(blabla[j]) - 1
            for j in blabla
        )

    # no travel from start to end (no empty routes)
    # NOT INCLUDED IN THE PAPER BECAUSE REDOUNDANT because of the cost function
    no_from_start_to_end = m.addConstrs(
        direct_travel[k, i, j] == 0
        for k in vehicles
        for i in tasks
        for j in tasks
        if i.split('_')[0] == 'start'
        and j.split('_')[0] == 'end'
    )

    # vehicles can only start at the depot the are assigned to
    vehicles_to_their_depots = m.addConstrs(
        direct_travel[k, i, j] == 0
        for k in vehicles
        for i in tasks
        for j in tasks
        if vehicles[k] != tasks[i]
        and i.split('_')[0] == 'start'
    )

    # there can at most be one route for each vehicle
    one_vehicle_one_route = m.addConstrs(
        quicksum(direct_travel[k, i, j] for j in tasks) <= 1
        for k in vehicles
        for i in tasks
        if vehicles[k] == tasks[i]
        and i.split('_')[0] == 'start'
    )

    m.optimize()

    # print(m.getVarByName('direct_travel[0,job_1_1,job_1_1]').X)
    # print('INFEASIBLE',m.status == GRB.INFEASIBLE)
    # print('OPTIMAL',m.status == GRB.OPTIMAL)
    routes_plus = []
    # this list will be use to store the current solution for future runs of the solver
    current_solution = []

    if m.status != GRB.INFEASIBLE:
        # print("TTD: ",m.getObjective().getValue())
        routing_feasibility = sat
        # route stores the info about each route that i generated with the VRPTW extended model
        routes = {}
        # segments stores the info o each direct travel from a task location to another
        segments = {}
        # here i populate the list based on the variable that evaluated to true in the model
        for k in vehicles:
            sub_segment = []
            for i in tasks:
                for j in tasks:
                    # print(k,i,j,m.getVarByName('direct_travel[{},{},{}]'.format(k,i,j)).X)
                    if m.getVarByName('direct_travel[{},{},{}]'.format(k,i,j)).X >= 0.5:
                        # print(m.getVarByName('direct_travel[{},{},{}]'.format(k,i,j)).VarName)
                        sub_segment.append((i,j))
                        current_solution.append([k, i, j])
            segments.update({k:sub_segment})
        ########### IN CASE I WANNA TAKE A LOOK AT THE SOLUTION ####################
        # print('############ CUSTOMER SERVED ################')
        # for i in tasks:
        #     print(i,round(m.getVarByName('customer_served[{}]'.format(i)).X))
        # print('############# AUTONOMY LEFT #################')
        # for k in vehicles:
        #     for i in tasks:
        #         print(k,i,round(m.getVarByName('autonomy_left[{},{}]'.format(k,i)).X))
        ############################################################################

        # here i start forming the routes by adding the direct travels that begin from the start point
        for k in segments:
            for i in segments[k]:
                if i[0].split('_')[0] == 'start':
                    routes.update({k:[i]})

        # here i concatenate the routes by matching the last location of a direct travel with the first of another one
        for j in routes:
            while routes[j][-1][1].split('_')[0] != 'end':
                for i in segments[j]:
                    if i[0] == routes[j][-1][1]:
                        routes[j].append(i)

        # let's just change the format of storing the routes
        routes_2 = {route:[routes[route][0][0]] for route in routes}


        for route1, route2 in zip(routes, routes_2):
            for segment in routes[route1]:
                routes_2[route2].append(segment[1])
        # assign routes_2 to routes and keep using routes
        routes = routes_2


        # this list tells the distance between each two locations based on the route
        # first step: calculate distance from one location to the following
        routes_length = {
            route:[
                    distance(current_path[elem1, elem2], edges)
                    for elem1, elem2 in zip(routes[route][:-1], routes[route][1:])
                ]
            for route in routes
        }

        # step two: iteratively sum the one value with the previous one
        routes_length = {
            elem: [routes_length[elem][i]
                  +
                  sum([routes_length[elem][j] for j in range(i)]) for i in range(len(routes_length[elem]))]
            for elem in routes_length
        }
        '_'.join(j.split('_')[:-1])
        # this list tells me the actual nodes that the vehicles must visit to execute the route and if
        # the node has a time window ('None' otherwise)
        actual_nodes = {}
        for route in routes:
            points = [jobs['_'.join(routes[route][0].split('_')[:-1])]['tasks']['0']['location']]
            tws = ['None']
            St = [0]
            Ct = [0]
            for segment1, segment2 in zip(routes[route][:-1], routes[route][1:]):
                points += current_path[segment1, segment2][1:]
                for _ in current_path[segment1, segment2][1:]:
                    tws.append('None')
                    St.append(0)
                    Ct.append(0)
                tws[-1] = jobs['_'.join(segment2.split('_')[:-1])]['tasks'][segment2.split('_')[-1]][
                    'TW']
                St[-1] = jobs['_'.join(segment2.split('_')[:-1])]['tasks'][segment2.split('_')[-1]][
                    'Service']
                if segment2.split('_')[0] == 'recharge':
                    Ct[-1] = math.ceil((1 / charging_coefficient) \
                    *\
                    (Autonomy - round(m.getVarByName('autonomy_left[{},{}]'.format(route, segment2)).X)))

            actual_nodes.update({route:(points, tws, St,Ct)})

        actual_nodes_2 = {
            elem:[(current, next) for current, next in zip(
                actual_nodes[elem][0],
                actual_nodes[elem][0][1:])
             ]
            for elem in actual_nodes
        }

        # finally the list of routes:
        routes_plus = {
            route:(
                # 0 actual nodes of the route
                actual_nodes[route][0],
                # 1 actual edges
                actual_nodes_2[route],
                # 2 time window by node
                actual_nodes[route][1],
                # 3 service time by node
                actual_nodes[route][2],
                # 4 sequence of tasks
                routes[route],
                # 5 route length in distance
                routes_length[route][-1],
                # 6 charging time by node
                actual_nodes[route][3]
            )
            for route in routes
        }
    else:
        routing_feasibility = unsat

    locations_plus = {}
    for j in routes_plus:
        locations_plus.update({
            j: {
                (tasks[task1], tasks[task2]):
                    {
                        'TW': ['None' if i != tasks[task2]
                               else jobs['_'.join(task2.split('_')[:-1])]['tasks'][task2.split('_')[-1]]['TW']
                               for i in current_path[(task1, task2)]
                               ],
                        'St': [0 if i != tasks[task1]
                               else jobs['_'.join(task1.split('_')[:-1])]['tasks'][task1.split('_')[-1]]['Service']
                               for i in current_path[(task1, task2)]
                               ],
                        'Ct': [0 if i != tasks[task2] or task2.split('_')[0] != 'recharge'
                               else math.ceil((1 / charging_coefficient) \
                                    *\
                                    (Autonomy - round(m.getVarByName('autonomy_left[{},{}]'.format(j, task2)).X)))
                               for i in current_path[(task1, task2)]
                               ]
                    }
                for task1, task2 in zip(routes_plus[j][4][:-1], routes_plus[j][4][1:])
            }
        })

    # print('-- LOCATION PLUS --')
    # for i in locations_plus:
    #     print(i, locations_plus[i])

    return routing_feasibility, routes_plus, current_solution,locations_plus

#
# routing_feasibility, routes_plus, current_solution = routing(edges, jobs, tasks, Autonomy, start_list, ATRs, current_path)
#
# print(routing_feasibility)
# for i in routes_plus:
#     print(i,routes_plus[i])

