import math

from z3 import *
from support_functions import make_graph, print_support, take_second, json_parser
from time import time as tm


def modello(instance,method):

    print('begin processing instance: ',instance,'method: ',method,)

    start_generation = tm()

    # first of all, let's parse the json file with the plant layout and the jobs info
    jobs,nodes,edges,Autonomy,ATRs,charging_coefficient,\
    Big_number,charging_stations,hub_nodes,start_list = json_parser('test_cases/%s.json' % instance,True)

    # now let's build the graph out of nodes and edges
    graph = make_graph(nodes,edges)

    # here are the jobs, with subtasks, precedence constraints and time windows
    # since it is a PICKUP-DELIVERY problem, at least one task per job has to have a
    # precedence constraint

    # i just flatten out the list of vehicles
    vehicles = [x + '_%s' % i for x in ATRs for i in range(ATRs[x]['units']) ]

    # i need to figure out how to calculate this value
    # the time horizon must be increased by a constant whose value is equal to the longest
    # edge in the graph

    c = max([i[0] for i in edges.values()])

    time_horizon = [i for i in range(Big_number + c)]

    # z3 variables

    # objective function dummy variable
    Z = Int('Z')

    # this boolean variables state whether a vehicle is assigned to a job or not
    assigned_to_job = [[Bool('%s_TO_%s' % (i,j)) for j in jobs ] for i in vehicles ]

    # this is the same as above, but for the single task. it may be redundant, but it makes
    # it easier to model
    assigned_to_task = [[[Bool('%s_TO_%s_%s' % (i,j,k))
                          for k in jobs[j]['tasks'] ]
                         for j in jobs ]
                        for i in vehicles ]

    serves_task = [[[[Bool('%s_SERVES_%s_%s_TIME_%s' % (i,j,k,t))
                            for t in time_horizon ]
                          for k in jobs[j]['tasks'] ]
                         for j in jobs ]
                        for i in vehicles ]

    # this new set of variables is required to make sure vehicles recharge fully, not parcially when they return to the
    # depot
    rc_bool = [[Bool('vehicle_%s_time%s' % (i,j)) for j in time_horizon] for i in vehicles]

    rc = [[Int('vehicle_%s_time%s' % (i,j)) for j in time_horizon] for i in vehicles]

    at = [[[Bool('%s_AT_%s_time_%s' % (i,j,t)) for t in time_horizon] for j in nodes] for i in vehicles]

    move = [[[Bool('%s_TO_%s_time_%s'% (i,j,t)) for t in time_horizon] for j in nodes] for i in vehicles]

    # z3 constraints

    # in order to serve a task, a vehicle has to be at its location and cannot leave it for as long as the
    # service takes
    service_at_location = [
        Implies(
            serves_task[i][j][k][t],
            And([
                at[i][jobs[job]['tasks'][task]['location']][t1]
                for t1 in range(t,t+jobs[job]['tasks'][task]['Service'] + 1)
            ])
        )
        for i,_ in enumerate(vehicles)
        for j,job in enumerate(jobs)
        for k,task in enumerate(jobs[job]['tasks'])
        for t in range(len(time_horizon)- jobs[job]['tasks'][task]['Service'] - 1)
    ]

    exactly_one_service = [
        PbEq([
            (serves_task[i][j][k][t], 1) for i, _ in enumerate(vehicles) for t in time_horizon
        ], 1)
        for j, job in enumerate(jobs)
        for k, task in enumerate(jobs[job]['tasks'])
    ]

    # exactly one vehicle is assigned to a job

    one_vehicle_per_job = [
        PbEq([
            (assigned_to_job[i][j],1) for i,_ in enumerate(vehicles)
        ],1)
        for j,_ in enumerate(jobs)
    ]

    # same story with tasks

    one_vehicle_per_task = [
        PbEq([
            (assigned_to_task[i][j][k],1) for i,_ in enumerate(vehicles)
        ],1)
        for j,job in enumerate(jobs)
        for k,_ in enumerate(jobs[job]['tasks'])
    ]

    # if a vehicle is assigned to a task, it has to visit its location at some point
    visit_task_loc = [
        Implies(
            assigned_to_task[i][j][k],
            Or([
                serves_task[i][j][k][t] for t in time_horizon
               ])
        )
        for i,_ in enumerate(vehicles)
        for j,job in enumerate(jobs)
        for k,task in enumerate(jobs[job]['tasks'])
        if jobs[job]['tasks'][task]['TW'] == 'None'
    ]

    # precedence constraints among tasks
    precedence = [
        Implies(
            serves_task[i][j][k1][t],
            And([
                Not(serves_task[i][j][k2][t_prime])
                for k2,task2 in enumerate(jobs[job]['tasks'])
                if task2 in jobs[job]['tasks'][task1]['precedence']
                for t_prime in range(t,len(time_horizon))
            ])
        )
        for i,_ in enumerate(vehicles)
        for j,job in enumerate(jobs)
        for k1,task1 in enumerate(jobs[job]['tasks'])
        if jobs[job]['tasks'][task1]['precedence'] != []
        for t in time_horizon
    ]

    # if assigned to a job, a vehicle must execute all its tasks

    all_tasks = [
        Implies(
            assigned_to_job[i][j],
            And([
                assigned_to_task[i][j][k] for k,_ in enumerate(jobs[job]['tasks'])
            ])
        )
        for j,job in enumerate(jobs)
        for i,_ in enumerate(vehicles)
    ]

    # if a vehicle is assigned to a task, it has to reach the location within the time window, if such exists
    time_window = [
        Implies(
            assigned_to_task[i][j][k],
            Or([
                serves_task[i][j][k][t] for t in range(
                                        jobs[job]['tasks'][task]['TW'][0],
                                        jobs[job]['tasks'][task]['TW'][1] + 1
                                        )
               ])
        )
        for i,_ in enumerate(vehicles)
        for j,job in enumerate(jobs)
        for k,task in enumerate(jobs[job]['tasks'])
        if jobs[job]['tasks'][task]['TW'] != 'None'
    ]

    # only eligible ATRs can execute the corresponding tasks

    eligibility = [
        Not(assigned_to_job[i][j])
        for i,atr in enumerate(vehicles)
        for j,job in enumerate(jobs)
        if '_'.join(atr.split('_')[:-1]) not in jobs[job]['ATR']
    ]


    # THESE CONSTRAINTS ARE RELATED TO THE ROBOTS MOVEMENTS
    # take a look at the file 'conflict_free_no_edges.py' for comments on the constraints

    initial_location = [
        at[i_index][start_list['_'.join(i.split('_')[:-1])]][0] for i_index,i in enumerate(vehicles)
    ]

    # ATRs are supposed to go back to their initial location after they are finished
    # this must be decreased by the same constant c as above

    return_trip = [
        at[i_index][start_list['_'.join(i.split('_')[:-1])]][len(time_horizon) - c] for i_index, i in enumerate(vehicles)
    ]

    no_ubiquity = [
        PbLe([
            (at[i][j_index][t],1) for j_index in nodes
        ],1)
        for i,_ in enumerate(vehicles)
        for t in time_horizon
    ]


    uni_to = [
        PbLe([
            (move[i][j_index][t],1) for j_index in nodes
        ],1)
        for i,_ in enumerate(vehicles)
        for t in time_horizon
    ]

    not_moving_vehicle = [
        Implies(
            And(
                at[i][j][t],
                And([
                    Not(move[i][k][t]) for k in nodes if j != k
                ])
            ),
            at[i][j][t+1]
        )
        for i,_ in enumerate(vehicles)
        for j in nodes
        for t in time_horizon[:-1]

    ]

    # if a vehicle is moving to a point, it will disappear (i know it sounds strange) while it is crossing the
    # edge and reappear at the arriving node after as many time steps as it takes to cross the edge
    moving_vehicle = [
        Implies(
            And(
                at[i][j][t],
                move[i][k][t]
            ),
            And(
                And([
                    Not(at[i][l][t_prime])
                    for l in nodes
                    for t_prime in range(t+1,t + edges[(j,k)][0])
                ]),
                at[i][k][t + edges[(j,k)][0]]
            )
        )
        for i,_ in enumerate(vehicles)
        for j in nodes
        for k in nodes
        if (j,k) in edges
        for t in time_horizon[:-(edges[(j,k)][0])]
    ]

    not_to_the_same = [
        Implies(
            at[i][j][t],
            Not(move[i][j][t])
        )
        for i,_ in enumerate(vehicles)
        for j in nodes
        for t in time_horizon
    ]


    adjacent = [
        Implies(
            at[i][j][t],
            And([
                Not(move[i][k][t])
                for k in nodes
                if k not in graph[j]
            ])
        )
        for i,_ in enumerate(vehicles)
        for j in nodes
        for t in time_horizon
    ]

    # if an ATR is selected for multiple jobs, it has to execute them in sequence
    # (finish all tasks of a job before executing any other task)
    # it is a PICKUP-DELIVERY problem so i can exploit the fact that i always
    # know which is the last task of a job (the delivery)

    sequence = [
        Implies(
            And(
                serves_task[i][j1][k1][t1],
                serves_task[i][j1][k2][t2]
            ),
            And([
                Not(serves_task[i][j2][k][t])
                for j2,job2 in enumerate(jobs)
                if job1 != job2
                for k,_ in enumerate(jobs[job2]['tasks'])
                for t in range(t1+1,t2)
                if '_'.join(atr.split('_')[:-1]) in jobs[job2]['ATR']
            ])
        )
        for i,atr in enumerate(vehicles)
        for j1,job1 in enumerate(jobs)
        for k1,task1 in enumerate(jobs[job1]['tasks'])
        for k2,task2 in enumerate(jobs[job1]['tasks'])
        for t1 in time_horizon
        for t2 in range(t1,len(time_horizon))
        if task1 != task2
        if '_'.join(atr.split('_')[:-1]) in jobs[job1]['ATR']
    ]

    # CONSTRAINTS FOR CONFLICT FREE ROUTING

    # if two robots are on the same node and are to cross the same edge, they cannot do it
    # at the same time step

    conflict_direct = [
        Implies(
            And(
                at[i1][j][t],
                at[i2][j][t]
            ),
            And([
                Or(
                    Not(move[i1][k][t]),
                    Not(move[i2][k][t])
                )
            for k in graph[j]
            ])
        )
        for i1,atr1 in enumerate(vehicles)
        for i2,atr2 in enumerate(vehicles)
        if atr1 != atr2
        for j in nodes
        for t in time_horizon

    ]

    # if two vehicles are on the opposite sides of an edge, and one is crossing the edge, the other cannot cross
    # it until the first one is done traversing.

    conflict_inverse =[
        Implies(
            And(
                at[i1][edge[0]][t],
                at[i2][edge[1]][t],
                move[i1][edge[1]][t]
            ),
            And([
                Not(move[i2][edge[0]][t_prime])
                for t_prime in range(t,t + edges[edge][0] )
            ])
        )
        for i1,atr1 in enumerate(vehicles)
        for i2,atr2 in enumerate(vehicles)
        if atr1 != atr2
        for edge in edges
        for t in time_horizon[:-(edges[edge][0])]
    ]

    # if the node is not a hub (hubs can accommodate an infinite number of vehicles), it can only accommodate one
    # vehicle at the time

    one_vehicle_at_a_time = [
        PbLe([
            (at[i][j_index][t], 1) for i, _ in enumerate(vehicles)
        ], 1)
        for j_index in nodes if j_index not in hub_nodes
        for t in time_horizon
    ]

    # CONSTRAINTS FOR BATTERY MANAGEMENT

    domain = [
        And(
            rc[i][t] >= 0,
            rc[i][t] <= Autonomy
        )
        for i,_ in enumerate(vehicles)
        for t in time_horizon
    ]

    # whenever a decision to move is made, battery charge will decrease by one unit for as many step as the move length
    rc_decrease = [
        Implies(
            And(
                at[i][j][t],
                move[i][k][t]
            ),
            And([
                rc[i][t1] <= rc[i][t1-1] - 1
                for t1 in range(t+1,t + edges[(j,k)][0]+1)
                ]),
        )
        for i,_ in enumerate(vehicles)
        for j in nodes
        for k in nodes
        if (j,k) in edges
        for t in time_horizon[:-(edges[(j,k)][0])]
    ]

    # if the vehicle does not move charge does not decrease
    rc_stationary = [
        Implies(
            And(
                at[i][j][t],
                And([
                    Not(move[i][k][t]) for k in nodes
                ])
            ),
            rc[i][t + 1] <= rc[i][t]
        )
        for i,vehicle in enumerate(vehicles)
        for j in nodes
        if j != start_list[vehicle.split('_')[0]]
        for t in time_horizon[:-1]
    ]
    ################ THIS IS THE OBSOLETE ONE ###################
    # rc_recharge = [
    #     Implies(
    #         And(
    #             at[i][j][t],
    #             And([
    #                 Not(move[i][k][t]) for k in nodes
    #                 ])
    #         ),
    #         rc[i][t+1] == rc[i][t] + charging_coefficient
    #     )
    #     for i,vehicle in enumerate(vehicles)
    #     for j in nodes
    #     if j == start_list[vehicle.split('_')[0]]
    #     for t in time_horizon[:-1]
    # ]
    ###############################################################

    # only by willingly choosing to recharge the vehicles can increase their battery state
    rc_recharge_1 = [
        Implies(
            Not(rc_bool[i][t]),
            rc[i][t+1] <= rc[i][t]
        )
        for i,_ in enumerate(vehicles)
        for t in time_horizon[:-1]
    ]

    # a vehicle that recharges has to remain at the depot till its battery is fully charged
    rc_recharge_2 = [
        Implies(
            And(
                rc_bool[i][t],
                rc[i][t] == rc1
            ),
            And(
                And([ at[i][j][t1] for t1 in range(t,t + math.ceil((Autonomy - rc1)/charging_coefficient)) ]),
                And([ rc[i][t2 + 1] == rc[i][t2] + charging_coefficient
                      for t2 in range(t, t + math.ceil((Autonomy - rc1)/charging_coefficient)) ])
            )
        )
    for i, vehicle in enumerate(vehicles)
    for rc1 in range(Autonomy + 1)
    for j in nodes
    if j == start_list[vehicle.split('_')[0]]
    for t in range(len(time_horizon) - math.ceil((Autonomy - rc1)/charging_coefficient) )
    ]

    # for i in rc_recharge_2:
    #     print(i)

    # a vehicle cannot recharge too close to the end of the time horizon
    # (it wouldn't make sense since it is not going to use the charge)
    rc_recharge_3 = [
        Not(rc_bool[i][t])
        for i,_ in enumerate(vehicles)
        for t in range(len(time_horizon) - Autonomy, len(time_horizon))
    ]

    rc_recharge = rc_recharge_1 + rc_recharge_2 + rc_recharge_3

    # no charge in between tasks of the same job
    no_charge_while_work = [
        Implies(
            And(
                serves_task[i][j1][k1][t1],
                serves_task[i][j1][k2][t2]
            ),
            And([Not(rc_bool[i][t]) for t in range(t1,t2)])
        )
        for i, atr in enumerate(vehicles)
        for j1, job1 in enumerate(jobs)
        for k1, task1 in enumerate(jobs[job1]['tasks'])
        for k2, task2 in enumerate(jobs[job1]['tasks'])
        for t1 in time_horizon
        for t2 in range(t1, len(time_horizon))
        if task1 != task2
        if '_'.join(atr.split('_')[:-1]) in jobs[job1]['ATR']
    ]

    no_moves_after_c = [
        Not(move[i][k][t])
        for i,_ in enumerate(vehicles)
        for k in nodes
        for t in range(len(time_horizon) - c, len(time_horizon))
    ]

    opti = [
        Z
        ==
        Sum([
            If(
            And(
                at[i][j][t],
                move[i][k][t]
            ),
            edges[(j,k)][0],
            0
            )
            for i,_ in enumerate(vehicles)
            for j in nodes
            for k in graph[j]
            for t in time_horizon
        ])
    ]

    generation_time = round(tm() - start_generation,2)
    print('generation: ', generation_time)
    # HERE THE MODEL IS BUILT AND SOLVED BY Z3
    print('MONOLITHIC MODEL')
    if True:
        start_solving = tm()

        if method == 'O':
            s = Optimize()
        else:
            s = Solver()

        # making z3 more verbose
        # set_option("verbose", 2)
        s.set('timeout',1200*1000)

        s.add(
            conflict_direct +
            conflict_inverse +
            sequence +
            eligibility +
            all_tasks +
            precedence +
            service_at_location +
            exactly_one_service +
            one_vehicle_per_job +
            one_vehicle_per_task +
            one_vehicle_at_a_time +
            visit_task_loc +
            initial_location +
            return_trip +
            no_ubiquity +
            uni_to +
            time_window +
            not_moving_vehicle +
            moving_vehicle +
            not_to_the_same +
            adjacent +
            domain +
            rc_decrease +
            rc_stationary +
            rc_recharge +
            no_charge_while_work +
            no_moves_after_c +
            opti
        )
        # COST FUNCTION
        # minimize the traveled distance
        if method == 'O':
            s.minimize(Z)

        # printing functions
        feasibility = s.check()
        if feasibility == sat:
            m = s.model()
            optimum = m[Z]
            print('travelling distance: ', optimum)

            # print(s.statistics())

            def elem(stringa):
                return str(stringa).split('_')[0]

            def elem2(stringa):
                return int(str(stringa).split('_')[5])

            assignments = []
            service = []
            tasks = []
            path = []
            movements = []
            remaining_charge = []
            charge_action = []


            for i,_ in enumerate(vehicles):
                for j,job in enumerate(jobs):
                    for k,_ in enumerate(jobs[job]['tasks']):
                        for t in time_horizon:
                            if m[serves_task[i][j][k][t]] == True:
                                service.append(serves_task[i][j][k][t])
            tasks = sorted(tasks, key=elem2)


            for i,_ in enumerate(vehicles):
                for j,_ in enumerate(jobs):
                    if m[assigned_to_job[i][j]] == True:
                        assignments.append(assigned_to_job[i][j])

            for i,_ in enumerate(vehicles):
                for j,job in enumerate(jobs):
                    for k,_ in enumerate(jobs[job]['tasks']):
                        if m[assigned_to_task[i][j][k]] == True:
                            tasks.append(assigned_to_task[i][j][k])

            for i, _ in enumerate(vehicles):
                for t in time_horizon:
                    for j in nodes:

                        if m[at[i][j][t]]  == True:
                            path.append(at[i][j][t])
            path = sorted(path, key=elem)

            for i,_ in enumerate(vehicles):
                for j in nodes:
                    for t in time_horizon:
                        if m[move[i][j][t]]  == True:
                            movements.append(move[i][j][t])
            movements = sorted(movements, key=elem2)

            for i,_ in enumerate(vehicles):
                for t in time_horizon:
                    remaining_charge.append((rc[i][t],m[rc[i][t]]))
                    if m[rc_bool[i][t]] == True:
                        charge_action.append((rc_bool[i][t]))

            print('ASSIGNMENTS')
            for i in assignments:
                print(i)
            # print('TASKS')
            # for i in tasks:
            #     print(i)
            print('PATH')
            for i in path:
                print(i)
            print('MOVES')
            for i in movements:
                print(i)
            print('SERVICE')
            for i in service:
                print(i)
            print('REMAINING CHARGE')
            for i in remaining_charge:
                print(i)
            print('CHARGE ACTION')
            for i in charge_action:
                print(i)
        else:
            print('model is ', feasibility)
            optimum = 'None'
    if method == 'O':
        print('solving mode: Optimizer')
    elif method == 'S':
        print('solving mode: Solver')
    else:
        raise ValueError('WRONG SOLUTION METHOD')
    print('instance: ',instance)
    solving_time = round(tm() - start_solving,2)
    print('solving time: ', solving_time)
    # result = '{},{},{},{},{},{},{},{},{},{},{} \n'.format(
    #                                                 method,
    #                                                 feasibility,
    #                                                 optimum,
    #                                                 instance.split('_')[1][0] + instance.split('_')[1][1],
    #                                                 instance.split('_')[1][2],
    #                                                 instance.split('_')[1][3],
    #                                                 instance.split('_')[2],
    #                                                 instance.split('_')[3],
    #                                                 instance.split('_')[4],
    #                                                 generation_time,
    #                                                 solving_time
    #                                                 )
    #
    # with open('data_storage.txt', 'a+') as write_file:
    #     write_file.write(result)
    # print(s.statistics())

    return feasibility,optimum,generation_time,solving_time



