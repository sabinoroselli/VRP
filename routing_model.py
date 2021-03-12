from z3 import *
from itertools import permutations
from funzioni_di_supporto import distance

def routing(edges,jobs,Autonomy,current_path,previous_routes = []):

    # i need to update this dict every time i update the current paths
    distances = {
        i: distance(current_path[i], edges)
        for i in current_path
    }

    # boolean variable that states whether a vehicle travels from task t1 of job j1 to task t2 of job j2
    direct_travel = [[[[Bool('travel_from_%s_%s_to_%s_%s' % (j1, t1, j2, t2))
                        for t2 in jobs[j2]['tasks']]
                       for j2 in jobs]
                      for t1 in jobs[j1]['tasks']]
                     for j1 in jobs]
    # integer variable that keeps track of the arrival of a vehicle at a customer
    customer_served = [[Int('%s_%s_is_served' % (j, t)) for t in jobs[j]['tasks']] for j in jobs]
    # integer variable that keeps track of the autonomy left when arriving at a customer
    autonomy_left = [[Int('autonomy_when_in_%s_%s' % (j, t)) for t in jobs[j]['tasks']] for j in jobs]

    # only allow for positive domain
    domain = [
        And(
            customer_served[j][t] >= 0,
            autonomy_left[j][t] >= 0,
            autonomy_left[j][t] <= Autonomy
        )
        for j, job in enumerate(jobs)
        for t, _ in enumerate(jobs[job]['tasks'])
    ]

    # --> one arrival at each customer
    one_arrival = [
        PbEq([(direct_travel[j2][t2][j1][t1], 1)
              for j2, job2 in enumerate(jobs)
              for t2, _ in enumerate(jobs[job2]['tasks'])]
             , 1)

        for j1, job1 in enumerate(jobs)
        for t1, _ in enumerate(jobs[job1]['tasks'])
        if job1 != 'start' and job1 != 'end'
    ]

    # guarantee the flow conservation between start and end
    flow = [
        Implies(
            PbEq([(direct_travel[j][t][j2][t2], 1)
                  for j2, job2 in enumerate(jobs)
                  for t2, _ in enumerate(jobs[job2]['tasks'])
                  if job2 != 'start'
                  ], n),
            PbEq([(direct_travel[j2][t2][j][t], 1)
                  for j2, job2 in enumerate(jobs)
                  for t2, _ in enumerate(jobs[job2]['tasks'])
                  if job2 != 'end'
                  ], n),
        )
        for j, job in enumerate(jobs)
        for t, task in enumerate(jobs[job]['tasks'])
        for n in range(len(jobs))
        if job != 'start' and job != 'end'
    ]

    # no travel from and to the same spot
    not_travel_same_spot = [
        Not(direct_travel[j][t][j][t])
        for j, job in enumerate(jobs)
        for t, _ in enumerate(jobs[job]['tasks'])
        if job != 'start' and job != 'end'
    ]

    # no travel to the starting point
    no_travel_to_start = [
        Not(direct_travel[j][t][list(jobs.keys()).index('start')][0])
        for j, job in enumerate(jobs)
        for t, _ in enumerate(jobs[job]['tasks'])

    ]

    # no travel from the end point
    no_travel_from_end = [
        Not(direct_travel[list(jobs.keys()).index('end')][0][j][t])
        for j, job in enumerate(jobs)
        for t, _ in enumerate(jobs[job]['tasks'])

    ]
    # based on the direct travels, define the arrival time to a customer depending on the departure time from the previous
    infer_arrival_time = [
        Implies(
            direct_travel[j1][t1][j2][t2],
            customer_served[j2][t2] >= customer_served[j1][t1] + distances[(job1 + '_' + task1, job2 + '_' + task2)]
        )
        for j1, job1 in enumerate(jobs)
        for t1, task1 in enumerate(jobs[job1]['tasks'])
        for j2, job2 in enumerate(jobs)
        for t2, task2 in enumerate(jobs[job2]['tasks'])
        if job1 != job2 or task1 != task2
    ]

    # set the arrival time within the time window for each customer
    time_window = [
        And(
            customer_served[j][t] >= jobs[job]['tasks'][task]['TW'][0],
            customer_served[j][t] <= jobs[job]['tasks'][task]['TW'][1]
        )
        for j, job in enumerate(jobs)
        for t, task in enumerate(jobs[job]['tasks'])
        if jobs[job]['tasks'][task]['TW'] != 'None'
    ]

    # ATRs have to go back before they run out of energy
    autonomy = [
        Implies(
            direct_travel[j1][t1][j2][t2],
            autonomy_left[j2][t2] <= autonomy_left[j1][t1] - distances[(job1 + '_' + task1, job2 + '_' + task2)]
        )
        for j1, job1 in enumerate(jobs)
        for t1, task1 in enumerate(jobs[job1]['tasks'])
        for j2, job2 in enumerate(jobs)
        for t2, task2 in enumerate(jobs[job2]['tasks'])
        if job1 != job2 or task1 != task2
    ]

    # list of possible orderings of tasks belonging to the same job
    permut = {job: list(permutations([job + '_' + task for task in jobs[job]['tasks']])) for job in jobs}

    # if a number of tasks belongs to one job, they have to take place in sequence
    # "this constraint was a pain in the ass to code!!!!"
    order_within_job = [
        Or([
            And([
                direct_travel[j1][t1][j2][t2]

                for j1, job1 in enumerate(jobs)
                for t1, task1 in enumerate(jobs[job1]['tasks'])
                for j2, job2 in enumerate(jobs)
                for t2, task2 in enumerate(jobs[job2]['tasks'])

                for elem in range(len(alt) - 1)
                if job1 + '_' + task1 == alt[elem] and job2 + '_' + task2 == alt[elem + 1]

            ])
            for alt in permut[job]
        ])
        for job in jobs
    ]

    # constraint over arrival time when precedence is required
    # i assume that precedence constraints can only be among tasks of the same job
    precedence = [
        customer_served[j1][t1] >= customer_served[j1][t2]
        for j1, job1 in enumerate(jobs)
        for t1, task1 in enumerate(jobs[job1]['tasks'])
        for t2, task2 in enumerate(jobs[job1]['tasks'])
        if task2 in jobs[job1]['tasks'][task1]['precedence']
    ]

    # this dict holds the info about the mutual exclusive jobs
    mutual_exclusive_jobs = {
        job: [job2 for job2 in jobs if bool(set(jobs[job]['ATR']) & set(jobs[job2]['ATR'])) == False] for job in jobs
    }

    # tasks of mutual exclusive jobs cannot be executed on the same route (cause i need a different robot)

    # I NEED TO FIGURE OUT THE JOBS THAT CAN BE EXECUTED TOGETHER INSTEAD
    # I KNOW HOW. I HAVE TO FIX IT ASAP!!!!! HERE IT IS: NO DIRECT TRAVEL IS ALLOWED BETWEEN  THE DELIVERY
    # OF ONE JOB AND ANY PICKUP OF THE MUTUAL EXCLUSIVE
    # ACTUALLY, IF ANY OF THE ALLOWED JOBS HAS A DIRECT TRAVEL TO THE INITIAL ONE (OR THE INITIAL HAS
    # A DIRECT TRAVEL TO ONE ALLOWED), THE ALLOWED ONE CANNOT TRAVEL TO THE MUTUAL EXCLUSIVE
    # ...BIG MESS UH???

    mutual_exclusive = [
        Not(direct_travel[j1][t1][j2][t2])
        for j1, job1 in enumerate(jobs)
        for t1, task1 in enumerate(jobs[job1]['tasks'])
        for j2, job2 in enumerate(jobs)
        for t2, task2 in enumerate(jobs[job2]['tasks'])

        if job2 in mutual_exclusive_jobs[job1]
    ]

    routing = Optimize()

    routing.add(
        domain +
        one_arrival +
        not_travel_same_spot +
        no_travel_to_start +
        no_travel_from_end +
        infer_arrival_time +
        time_window +
        autonomy +
        order_within_job +
        precedence +
        mutual_exclusive +
        flow
    )

    if previous_routes != []:
        excluding_previous_routes = [
            Or([
                Not(direct_travel[i[0]][i[1]][i[2]][i[3]]) for i in previous_route
            ])
            for previous_route in previous_routes
        ]
        routing.add(excluding_previous_routes)



    # the fewer ATRs i have in the system, the less chances there are to have collisions
    # therefore it makes sense to minimize their number
    routing.minimize(
        Sum([
            If(
                direct_travel[list(jobs.keys()).index('start')][0][j][t],
                1,
                0
            )
            for j, job in enumerate(jobs)
            for t, _ in enumerate(jobs[job]['tasks'])
        ])
    )

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
        for j1, job1 in enumerate(jobs):
            for t1, task1 in enumerate(jobs[job1]['tasks']):
                for j2, job2 in enumerate(jobs):
                    for t2, task2 in enumerate(jobs[job2]['tasks']):
                        if routing_solution[direct_travel[j1][t1][j2][t2]] == True:
                            segments.append(((job1, task1), (job2, task2)))
                            current_solution.append([j1,t1,j2,t2])

        # here i start forming the routes by adding the direct travels that begin from the start point
        for i in segments:
            if i[0][0] == 'start':
                routes.append([i])
        # here i concatenate the routes by matching the last location of a direct travel with the first of another one
        for j in routes:
            while j[-1][1][0] != 'end':
                for i in segments:
                    if i[0][0] == j[-1][1][0] and i[0][1] == j[-1][1][1]:
                        j.append(i)

        # this list tells how long it takes to reach each location based on the route
        # first step: calculate how long it takes from one location to the following
        arrivals = [
            [distance(
                current_path[
                    segment[0][0] + '_' + segment[0][1],
                    segment[1][0] + '_' + segment[1][1]
                ],
                edges
            ) for segment in route]
            for route in routes
        ]

        # step two: iteratively sum the one value with the previous one
        arrivals = [
            [elem[i] + sum([elem[j] for j in range(i)]) for i in range(len(elem))]
            for elem in arrivals
        ]

        # this list tells which resources can execute each task
        eligible = [
            set.intersection(*[set(jobs['%s' % segment[1][0]]['ATR']) for segment in route])
            for route in routes
        ]

        # finally the list of routes:
        #   element 1: sublist of direct travels in the route (i won't need it for the job shop problem, but maybe later on)
        #   element 2: route lenght
        #   element 3: latest start for the job that still allowes to meet the stricter deadline
        #   element 4: sublist of eligible ATRs (resources) for the job

        routes_plus = [
            [
                route,
                arrivals[index][-1],
                min([
                    jobs[segment[1][0]]['tasks'][segment[1][1]]['TW'][1] - arrivals[index][oth_ind]
                    for oth_ind, segment in enumerate(route)
                    if jobs[segment[1][0]]['tasks'][segment[1][1]]['TW'] != 'None'
                ]),
                list(eligible[index])
            ]
            for index, route in enumerate(routes)
        ]

    return routing_feasibility, routes_plus, current_solution