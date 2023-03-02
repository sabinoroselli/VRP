from z3 import *
from support_functions import distance
from itertools import permutations

def routing(edges,jobs,tasks,Autonomy, start_list, ATRs, current_path,previous_routes = []):

    # i need to update this dict every time i update the current paths
    distances = {
        i: distance(current_path[i], edges)
        for i in current_path
    }

    # boolean variable that states whether a vehicle travels from customer i to customer j
    direct_travel = [[
        Bool('from_{}_to_{}'.format(i,j))
            for j in tasks]
                for i in tasks]

    # integer variable that keeps track of the arrival of vehicle k at a customer
    customer_served = [Real('{}_is_served'.format(t)) for t in tasks]
    # integer variable that keeps track of the autonomy left when arriving at a customer
    autonomy_left = [Real('autonomy_at_{}'.format(t)) for t in tasks]

    ##### the following constraints guarantee that routes are structured as they should #####

    # --> one arrival at each customer
    one_arrival = [
            PbEq([(direct_travel[i][j], 1)
                  for j,_ in enumerate(tasks)]
                 , 1)
            for i,job in enumerate(tasks)
            if job.split('_')[0] != 'start' and job.split('_')[0] != 'end'
        ]


    # guarantee the flow conservation between start and end
    flow = [
        Implies(
            PbEq([(direct_travel[i][j], 1)
                  for j,job2 in enumerate(tasks)
                  if job.split('_')[0] != 'start'
                  ], n),
            PbEq([(direct_travel[j][i], 1)
                  for j,job2 in enumerate(tasks)
                  if job.split('_')[0] != 'end'
                  ], n),
        )
        for i,job in enumerate(tasks)
        for n in range(len(jobs))
        if job.split('_')[0] != 'start' and job.split('_')[0] != 'end'
    ]


    # no travel from and to the same spot
    not_travel_same_spot = [
        Not(direct_travel[j][j])
        for j, job in enumerate(tasks)
        # if job.split('_')[0] != 'start' and job.split('_')[0] != 'end'
    ]

    # no travel to the starting point
    no_travel_to_start = [
        Not(direct_travel[i][j])
        for i, job1 in enumerate(tasks)
        for j, job2 in enumerate(tasks)
        if job2.split('_')[0] == 'start'
    ]

    # no travel from the end point
    no_travel_from_end = [
        Not(direct_travel[i][j])
        for i, job1 in enumerate(tasks)
        for j, job2 in enumerate(tasks)
        if job1.split('_')[0] == 'end'
    ]

    # no travel from start to end (no empty routes)
    no_from_start_to_end = [
        Not(direct_travel[i][j])
        for i,job1 in enumerate(tasks)
        for j,job2 in enumerate(tasks)
        if job1.split('_')[0] == 'start'
        and job2.split('_')[0] == 'end'
    ]

    # set the max number of routes per each depot equal to the number of vehicles available
    max_vehicles_at_a_depot = [
        PbLe([
            (direct_travel[i][j], 1)
              for j,_ in enumerate(tasks)],
              # ATRs[job.split('_')[1]]['units']
              len(jobs)
                        )
            for i,job in enumerate(tasks)
            if job.split('_')[0] == 'start'
    ]


    # routes must be closed (i.e. every vehicle that goes out has to come back)
    # THIS GIVES WEIRD OUTCOMES WHEN THERE IS ONLY ONE JOB.......FIGURE OUT WHY!!!!!!
    route_continuity = [

            Sum([ direct_travel[i][j]
                  for j,job in enumerate(tasks)
                  ])
            ==
            Sum([ direct_travel[j][k]
                  for j,job in enumerate(tasks)
                  ])

        for i,job1 in enumerate(tasks)
        for k,job2 in enumerate(tasks)
        if job1.split('_')[0] == 'start'
        and job2.split('_')[0] == 'end'
        and job1.split('_')[1] == job2.split('_')[1]
    ]


    ##### the following constraints concern the limited operating range and the time windows ####

    # only allow for positive domain
    domain = [
        And(
            customer_served[t] >= 0,
            autonomy_left[t] >= 0,
            autonomy_left[t] <= Autonomy
        )
        for t,_ in enumerate(tasks)
    ]

    # based on the direct travels, define the arrival time to a customer depending on the departure time from the previous
    infer_arrival_time = [
        Implies(
            direct_travel[i][j],
            customer_served[j] >= customer_served[i] +
                                  distances[(job1,job2)] +
                                  jobs[job1.split('_')[0] + '_' + job1.split('_')[1]]['tasks'][job1.split('_')[2]]['Service']
        )
        for i,job1 in enumerate(tasks)
        for j,job2 in enumerate(tasks)
        if job1 != job2
        ]

    # set the arrival time within the time window for each customer
    time_window = [
        And(
            customer_served[j] >= jobs[job.split('_')[0] + '_' + job.split('_')[1]]['tasks'][job.split('_')[2]]['TW'][0],
            customer_served[j] <= jobs[job.split('_')[0] + '_' + job.split('_')[1]]['tasks'][job.split('_')[2]]['TW'][1]
        )
        for j, job in enumerate(tasks)
        if jobs[job.split('_')[0] + '_' + job.split('_')[1]]['tasks'][job.split('_')[2]]['TW'] != 'None'
    ]
    # pp(time_window)
    # constraint over arrival time when precedence is required
    # i assume that precedence constraints can only be among tasks of the same job
    precedence = [
        customer_served[t1] <= customer_served[t2]
        for t1,job1 in enumerate(tasks)
        for t2,job2 in enumerate(tasks)
        if job1.split('_')[1] == job2.split('_')[1]
        and job2.split('_')[0] != 'start'
        and job2.split('_')[0] != 'end'
        and job1.split('_')[2] in jobs['job' + '_' + job2.split('_')[1]]['tasks'][job2.split('_')[2]]['precedence']
    ]

    # ATRs have to go back before they run out of energy
    autonomy = [
        Implies(
            direct_travel[i][j],
            autonomy_left[j] <= autonomy_left[i] - distances[(job1,job2)]
        )
        for i, job1 in enumerate(tasks)
        for j, job2 in enumerate(tasks)
        if job1 != job2
    ]

    #### these constraints concern creating routes that are actually executable by the ATRs ######

    # this dict holds the info about the mutual exclusive jobs
    mutual_exclusive_jobs = {
        job: [job2 for job2 in jobs if bool(set(jobs[job]['ATR']) & set(jobs[job2]['ATR'])) == False] for job in
        jobs
    }

    # tasks of mutual exclusive jobs cannot be executed on the same route (cause i need a different robot)
    mutual_exclusive = [
        Not(direct_travel[i][j])
        for i, job1 in enumerate(tasks)
        for j, job2 in enumerate(tasks)
        if '{}_{}'.format(job2.split('_')[0],job2.split('_')[1])
           in mutual_exclusive_jobs['{}_{}'.format(job1.split('_')[0],job1.split('_')[1])]
    ]

    # list of possible orderings of tasks belonging to the same job
    permut = { job: list(permutations([job + '_' + task for task in jobs[job]['tasks']])) for job in jobs }


    # if a number of tasks belongs to one job, they have to take place in sequence
    order_within_job = [
        Or([
            And([
                direct_travel[j1][j2]

                for j1, job1 in enumerate(tasks)

                for j2, job2 in enumerate(tasks)


                for elem in range(len(alt) - 1)
                if job1 == alt[elem] and job2 == alt[elem + 1]

            ])
            for alt in permut[job]
        ])
        for job in jobs
        if job.split('_')[0] != 'start'
           and job.split('_')[0] != 'end'
    ]

    routing = Optimize()

    routing.add(
        one_arrival +
        not_travel_same_spot +
        no_travel_to_start +
        no_travel_from_end +
        no_from_start_to_end +
        flow +
        max_vehicles_at_a_depot +
        route_continuity +
        domain +
        infer_arrival_time +
        time_window +
        precedence +
        autonomy +
        mutual_exclusive +
        order_within_job
    )

    if previous_routes != []:
        excluding_previous_routes = [
            Not(And([
                direct_travel[i[0]][i[1]] for i in previous_route
            ]))
            for previous_route in previous_routes
        ]
        routing.add(excluding_previous_routes)


    # the fewer ATRs i have in the system, the less chances there are to have collisions
    # therefore it makes sense to minimize their number
    routing.minimize(
        Sum([
            If(
                direct_travel[i][j],
                1,
                0
            )
            for i, job1 in enumerate(tasks)
            for j, job2 in enumerate(tasks)
            if job1.split('_')[0] == 'start'
        ])
    )
    # # alternative cost function to minimize the number of routes
    # routing.minimize(
    #     Sum([
    #         If(
    #             direct_travel[i][j],
    #             distances[(job1, job2)],
    #             0
    #         )
    #         for i, job1 in enumerate(tasks)
    #         for j, job2 in enumerate(tasks)
    #         if job1 != job2
    #     ])
    # )

    ### THIS PART IS ABOUT MANIPULATING THE SOLUTION TO USE IT AS AN INPUT FOR THE FOLLOWING STEPS ####

    routing_feasibility = routing.check()
    routes_plus = []
    # this list will be use to store the current solution for future runs of the solver
    current_solution = []
    if routing_feasibility == sat:
        routing_solution = routing.model()
        # route stores the info about each route that i generated with the VRPTW extended model
        routes = []
        # segments stores the info o each direct travel from a task location to another
        segments = []
        # here i populate the list based on the variable that evaluated to true in the model
        for i,job1 in enumerate(tasks):
            for j,job2 in enumerate(tasks):
                    if routing_solution[direct_travel[i][j]] == True:
                        # print(direct_travel[i][j])
                        segments.append((job1,job2))
                        current_solution.append([i,j])

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

        for route1,route2 in zip(routes,routes_2):
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
            distance(current_path[elem1,elem2],edges)
                +
            jobs[elem1.split('_')[0] + '_' + elem1.split('_')[1]]
            ['tasks']
            [elem1.split('_')[2]]['Service']

            for elem1,elem2 in zip(route[:-1],route[1:])
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
                    jobs['%s_%s' % (segment.split('_')[0],segment.split('_')[1])]['ATR']
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
                jobs[ task.split('_')[0] + '_' + task.split('_')[1] ]
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

        # for i in routes_plus:
        #     print(i)

    return routing_feasibility, routes_plus, current_solution

