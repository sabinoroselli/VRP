from z3 import *
from support_functions import distance


def routes_checking(edges,jobs,tasks,Autonomy,new_paths,current_routes):

    routes = [i[0] for i in current_routes]

    served = [[Real('serve_route_{}_{}'.format(index,j)) for j in i ] for index,i in enumerate(routes) ]

    charge = [[Real('charge_route_{}_{}'.format(index,j)) for j in i ] for index,i in enumerate(routes) ]

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
                        + distance(new_paths[i][(tasks[job1],tasks[job2])],edges)
                        + jobs[job1.split('_')[0] + '_' + job1.split('_')[1]]
                                ['tasks'][job1.split('_')[2]]['Service']
        for i, route in enumerate(routes)
            for (j1,job1),(j2,job2) in zip(enumerate(route[:-1]),enumerate(route[1:]))
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

    autonomy = [
        charge[i][j2 + 1] <= charge[i][j1] - distance(new_paths[i][(tasks[job1], tasks[job2])], edges)
        for i, route in enumerate(routes)
        for (j1, job1), (j2, job2) in zip(enumerate(route[:-1]), enumerate(route[1:]))
    ]



    checking = Optimize()

    checking.add(
        domain +
        infer_arrival_time +
        time_window +
        autonomy
    )

    checking_feasibility = checking.check()
    routes_plus = []
    if checking_feasibility == sat:

        # for i,route in enumerate(routes):
        #     for j,job in enumerate(route):
        #         print('serve_route_{}_{}'.format(i,job),checking.model()[served[i][j]])
        #         print('charge_route_{}_{}'.format(i,job),checking.model()[charge[i][j]])

        # this list tells how long it takes to reach each location based on the route
        # first step: calculate how long it takes from one location to the following
        arrivals = [
            [distance(new_paths[i][(tasks[elem1],tasks[elem2])],edges)
             for elem1, elem2 in zip(route[:-1], route[1:])]
            for i,route in enumerate(routes)
        ]

        # step two: iteratively sum the one value with the previous one
        arrivals = [
            [elem[i] + sum([elem[j] for j in range(i)]) for i in range(len(elem))]
            for elem in arrivals
        ]

        latest_start = [
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
            ])
            for index,route in enumerate(routes)
        ]
        # this manipulation I have done here is very weird, if I ever get the time, I'll scrap
        # it and redo it better
        tw_per_node = []
        for index,route in enumerate(routes):
            tw_buffer = ['None' for _ in list(new_paths[index].values())[0]]
            tw_buffer[0] = jobs[
                    route[0].split('_')[0] + '_' + route[0].split('_')[1]
                    ]['tasks'][route[0].split('_')[2]]['TW']
            tw_buffer[-1] = jobs[
                route[1].split('_')[0] + '_' + route[1].split('_')[1]
                ]['tasks'][route[1].split('_')[2]]['TW']
            for ind,pair in enumerate(list(new_paths[index].values())[1:]):
                intermediate_tw_buffer = ['None' for _ in pair[1:]]
                intermediate_tw_buffer[-1] = jobs[route[ind+2].split('_')[0] + '_' + route[ind+2].split('_')[1]
                ]['tasks'][route[ind+2].split('_')[2]]['TW']
                tw_buffer += intermediate_tw_buffer
            tw_per_node.append(tw_buffer)

        actual_nodes = []
        for route in new_paths:
            node_buffer = list(new_paths[route].values())[0]
            for pair in list(new_paths[route].values())[1:]:
                node_buffer += pair[1:]
            actual_nodes.append(node_buffer)

        routes_plus = [[
            route,
            arrivals[index][-1],
            latest_start[index],
            current_routes[index][3],
            (actual_nodes[index],tw_per_node[index])
            ]for index,route in enumerate(routes)
        ]

    return checking_feasibility,routes_plus

