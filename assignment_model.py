from z3 import *
import math

def assignment(ATRs,routes_plus,charging_coefficient,previous_assignments = []):
    # set_option(rational_to_decimal=True)

    # i just flatten out the list of vehicles
    vehicles = [x + '_%s' % i for x in ATRs for i in range(ATRs[x]['units'])]

    # boolean that evaluates to true if resource i is assigned to job (route) j
    allocation = [[Bool('%s_executes_%s' % (i, j)) for j in range(len(routes_plus))] for i in vehicles]
    # integer that states the start time of route j
    start = [Real('%s_starts' % i) for i in range(len(routes_plus))]
    # integer that states the end time of route j (don't really need it, but it is handy in the development phase)
    end = [Real('%s_ends' % i) for i in range(len(routes_plus))]

    # no negative starting time(pretty obvious -.-)
    domain = [
        start[i] >= 0 for i in range(len(routes_plus))
    ]
    # set the end time of a route based on its length
    end_time = [
        end[i] >= start[i] + routes_plus[i][1] for i in range(len(routes_plus))
    ]

    ###### this could be improved further by adding the time to travel from the task location back to the depot ######
    end_after_time_window = [
        end[i] >= routes_plus[i][4][1][j][0]
        for i in range(len(routes_plus))
        for j in range(len(routes_plus[i][4][1]))
        if routes_plus[i][4][1][j] != "None"
    ]

    # in order to meet the time windows, each job cannot start later than a certain time
    latest_start = [
        start[i] <= routes_plus[i][2] for i in range(len(routes_plus))
    ]
    # exactly one resource is assigned to a job
    exactly_one = [
        PbEq([(allocation[i][j], 1) for i in range(len(vehicles))], 1) for j in range(len(routes_plus))
    ]

    # one of the eligible resources has to execute the job
    res_alloc = [
        Or([
            allocation[i_index][j_index]
            for i_index, i in enumerate(vehicles)
            if i.split('_')[0] in j[3]

        ])
        for j_index, j in enumerate(routes_plus)
    ]

    # if a resource executes two jobs, those cannot overlap in time (also charging time has to be taken into account)
    # here I am assuming that vehicles charge to full battery after executing a route
    non_overlap = [
        Implies(
            And(
                allocation[i][j],
                allocation[i][k]
            ),
            Or(
                start[j] >= end[k] + math.ceil(routes_plus[k][6]/charging_coefficient),
                start[k] >= end[j] + math.ceil(routes_plus[j][6]/charging_coefficient)
            )
        )
        for i in range(len(vehicles))
        for j in range(len(routes_plus))
        for k in range(len(routes_plus))
        if k != j
    ]

    # pp(non_overlap)

    set_option(rational_to_decimal=True)
    set_option(precision=2)

    assignment = Solver()

    constraints = {
        'domain':domain,
        'end_time':end_time,
        'end_after_timewindow':end_after_time_window,
        'latest_start':latest_start,
        'exactly_one':exactly_one,
        'res_alloc':res_alloc,
        'non_overlap':non_overlap
    }

    # IF I JUST WANT TO ASSERT THE CONSTRAINTS...
    for i in constraints:
        assignment.add(constraints[i])

    # IF I WANT TO TRACK THEM IN CASE THE PROBLEM IS UNSAT...
    # for cons in constraints:
    #     for index,i in enumerate(constraints[cons]):
    #         assignment.assert_and_track(i,cons + '-{}'.format(str(index)))

    if previous_assignments != []:
        excluding_previous_assignments = [
            Or([
                Not(allocation[i[0]][i[1]]) for i in previous_assignment
            ])
        for previous_assignment in previous_assignments
        ]
        assignment.add(excluding_previous_assignments)

    assignment_feasibility = assignment.check()
    locations = {}
    current_assignment = []
    if assignment_feasibility == sat:
        m2 = assignment.model()


        #let's save the current solution so that we can rule it out in the next iteration
        for j in range(len(routes_plus)):
            for i,v in enumerate(vehicles):
                if m2[allocation[i][j]] == True:
                    current_assignment.append([i,j])
                    # print('route',j,'vehicle',v)

        actual_nodes = [ i[4] for i in routes_plus ]

        # this dict keeps track of which nodes (and edges) the vehicle will cross
        # need to extend the dict such that also the edges the ATR crosses while travelling the routes are reported

        locations.update(
        {
            (i, m2[start[j_index]]): (
                actual_nodes[j_index][0],
                [(current, next) for current, next in zip(
                    actual_nodes[j_index][0],
                    actual_nodes[j_index][0][1:])
                 ],
                actual_nodes[j_index][1],
                actual_nodes[j_index][2]
            )
            for j_index, j in enumerate(routes_plus)
            for i_index, i in enumerate(vehicles)
            if m2[allocation[i_index][j_index]] == True
        }
        )

        # for i in locations:
        #     print(i,locations[i])
    # else:
    #     buffer = [
    #             # 'domain',
    #             'end_time',
    #             'latest_start',
    #             'exactly_one',
    #             'res_alloc',
    #             'non_overlap'
    #              ]
        # UC = assignment.unsat_core()
        # for i in UC:
        #     if str(i).split('-')[0] in buffer:
        #         print(i,constraints[str(i).split('-')[0]][int(str(i).split('-')[1])])

    return assignment_feasibility, locations, current_assignment
