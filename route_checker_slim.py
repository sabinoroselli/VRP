from z3 import *
from support_functions import distance


def routes_checking(edges,jobs,tasks,Autonomy,new_paths,current_routes,charging_coefficient):

    routes = [current_routes[i][4] for i in current_routes]

    served = [[Real('serve_route_{}_{}'.format(route,customer)) for customer in current_routes[route][4] ]
                                                        for route in current_routes ]

    charge = [[Real('charge_route_{}_{}'.format(route,customer)) for customer in current_routes[route][4] ]
                                                        for route in current_routes ]

    domain = [
        And(
            served[i][j] >= 0,
            charge[i][j] >= 0,
            charge[i][j] <= Autonomy
        )
        for i,route in enumerate(routes)
        for j,_ in enumerate(route)
    ]

    infer_arrival_time = [
        served[i][j2+1] >= served[i][j1]
                        + distance(new_paths[route][(tasks[job1],tasks[job2])],edges)
                        + jobs[job1.split('_')[0] + '_' + job1.split('_')[1]]
                                ['tasks'][job1.split('_')[2]]['Service']
        for i, route in enumerate(current_routes)
            for (j1,job1),(j2,job2) in zip(enumerate(current_routes[route][4][:-1]),
                                           enumerate(current_routes[route][4][1:]))
    ]

    time_window = [
        And(
            served[i][j] >= jobs[job.split('_')[0] + '_' + job.split('_')[1]]['tasks'][job.split('_')[2]]['TW'][0],
            served[i][j] <= jobs[job.split('_')[0] + '_' + job.split('_')[1]]['tasks'][job.split('_')[2]]['TW'][1]
        )
        for i, route in enumerate(routes)
        for j, job in enumerate(route)
        if jobs[job.split('_')[0] + '_' + job.split('_')[1]]['tasks'][job.split('_')[2]]['TW'] != 'None'

    ]

    autonomy_1 = [
        charge[i][j2 + 1] <= charge[i][j1] - distance(new_paths[route][(tasks[job1], tasks[job2])], edges)
        for i, route in enumerate(current_routes)
        for (j1, job1), (j2, job2) in zip(enumerate(current_routes[route][4][:-1]),
                                          enumerate(current_routes[route][4][1:]))
        if job1.split('_')[0] != 'recharge'

    ]

    autonomy_2 = [
        charge[i][j2 + 1] <= Autonomy - distance(new_paths[route][(tasks[job1], tasks[job2])], edges)
        for i, route in enumerate(current_routes)
        for (j1, job1), (j2, job2) in zip(enumerate(current_routes[route][4][:-1]),
                                          enumerate(current_routes[route][4][1:]))
        if job1.split('_')[0] == 'recharge'

    ]

    autonomy = autonomy_1 + autonomy_2

    checking = Optimize()

    checking.add(
        domain +
        infer_arrival_time +
        time_window +
        autonomy
    )

    checking_feasibility = checking.check()
    routes_plus = []
    locations_plus = {}
    if checking_feasibility == sat:

        # this list tells the distance between each two locations based on the route
        # first step: calculate distance from one location to the following
        routes_length = {
            route: [
                distance(new_paths[route][tasks[elem1], tasks[elem2]], edges)
                for elem1, elem2 in zip(current_routes[route][4][:-1], current_routes[route][4][1:])
            ]
            for route in current_routes
        }

        # step two: iteratively sum the one value with the previous one
        routes_length = {
            elem: [routes_length[elem][i]
                   +
                   sum([routes_length[elem][j] for j in range(i)]) for i in range(len(routes_length[elem]))]
            for elem in routes_length
        }

        # for i,route in enumerate(routes):
        #     for j,job in enumerate(route):
                # print('serve_route_{}_{}'.format(i,job),checking.model()[served[i][j]])
                # print('charge_route_{}_{}'.format(i,job),checking.model()[charge[i][j]])

        # this manipulation I have done here is very weird, if I ever get the time, I'll scrap
        # it and redo it better
        # 20/10/2021: ....I WISH I HAD DONE IT BETTER :(
        # 10/11/2022: ... NAH...IT AIN'T GOING TO HAPPEN....LIVE WITH THAT!
        # 21/12/2022, 11.41: OK.....TODAY IS THE DAY.....
        # 21/12/2022, 12.30: I CAN'T BELIEVE IT....I FIXED IT

        actual_nodes = {}
        for i,route in enumerate(current_routes):
            points = [
                jobs[current_routes[route][4][0].split('_')[0] + '_' + current_routes[route][4][0].split('_')[1]]['tasks']['0']['location']]
            tws = ['None']
            St = [0]
            Ct = [0]
            for j,(segment1, segment2) in enumerate(zip(current_routes[route][4][:-1], current_routes[route][4][1:])):
                points += new_paths[route][
                              tasks[segment1],
                              tasks[segment2]
                          ][1:]
                for _ in new_paths[route][
                             tasks[segment1],
                             tasks[segment2]
                         ][1:]:
                    tws.append('None')
                    St.append(0)
                    Ct.append(0)
                tws[-1] = jobs[segment2.split('_')[0] + '_' + segment2.split('_')[1]]['tasks'][segment2.split('_')[2]][
                    'TW']
                St[-1] = jobs[segment2.split('_')[0] + '_' + segment2.split('_')[1]]['tasks'][segment2.split('_')[2]][
                    'Service']
                if segment2.split('_')[0] == 'recharge':
                    Ct[-1] = math.ceil((1 / charging_coefficient)
                                       * (Autonomy - round(int(str(checking.model()[charge[i][j+1]])))))

            actual_nodes.update({route: (points, tws, St, Ct)})

        actual_nodes_2 = {
            elem: [(current, next) for current, next in zip(
                actual_nodes[elem][0],
                actual_nodes[elem][0][1:])
                   ]
            for elem in actual_nodes
        }

        routes_plus = {
            route: (
                actual_nodes[route][0],
                actual_nodes_2[route],
                actual_nodes[route][1],
                actual_nodes[route][2],
                current_routes[route][4],
                routes_length[route][-1],
                actual_nodes[route][3]

            )
            for route in current_routes
        }

        for j_index,j in enumerate(routes_plus):
            locations_plus.update({
                j: {
                    (tasks[task1], tasks[task2]):
                        {
                            'TW': ['None' if i != tasks[task2]
                                   else jobs[task2.split('_')[0]
                                             + '_'
                                             + task2.split('_')[1]]['tasks'][task2.split('_')[2]]['TW']
                                   for i in new_paths[j][(tasks[task1], tasks[task2])]
                                   ],
                            'St': [0 if i != tasks[task1]
                                   else jobs[task1.split('_')[0]
                                             + '_'
                                             + task1.split('_')[1]]['tasks'][task1.split('_')[2]]['Service']
                                   for i in new_paths[j][(tasks[task1], tasks[task2])]
                                   ],
                            'Ct': [0 if i != tasks[task1] or task2.split('_')[0] != 'recharge'
                                   else math.ceil((1 / charging_coefficient)
                                       * (Autonomy - round(int(str(checking.model()[charge[j_index][index + 1 ]])))))
                                   for index,i in enumerate(new_paths[j][(tasks[task1], tasks[task2])])
                                   ]
                        }
                    for task1, task2 in zip(routes_plus[j][4][:-1], routes_plus[j][4][1:])
                }
            })

    return checking_feasibility,routes_plus, locations_plus

