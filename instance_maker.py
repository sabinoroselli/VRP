import random
# from pprint import *
import json
from edges_for_graphs import *
from funzioni_di_supporto import distance, make_graph


# Utility function to print the elements of an array
def printArr(arr, n):
    for i in range(n):
        print(arr[i], end=" ")

# m random non-negative integers
# whose sum is n
def randomList(m, n):
    # Create an array of size m where
    # every element is initialized to 0
    arr = [0] * m

    # To make the sum of the final list as n
    for i in range(n):
        # Increment any random element
        # from the array by 1
        arr[random.randint(0, n) % m] += 1

    # Print the generated list
    return arr

def make_an_instance(nodes,num_vehicles,num_jobs,edges_reduction,Big_number,SEED):

        NVJ = str(nodes) + str(num_vehicles) + str(num_jobs)

        print('making instance {}_{}_{}_{}'.format(NVJ,edges_reduction,Big_number,SEED))

        to_dump = {}

        random.seed(SEED)

        # range of possible operating range as a function of the number of nodes
        if nodes == 15:
            autonomy_range = [9,18]
        elif nodes == 25:
            autonomy_range = [12,24]
        elif nodes == 35:
            autonomy_range = [15,30]
        else:
            raise ValueError('WRONG NUMBER OF NODES')

        # list of charging stations as a function of the number of nodes
        # if nodes == 15:
        #     charging_stations = [6,8]
        # elif nodes == 25:
        #     charging_stations = [6,8,16,18]
        # elif nodes == 35:
        #     charging_stations = [6,8,16,18,26,28]
        # else:
        #     raise ValueError('WRONG NUMBER OF NODES')



        nodes_list = [str(i) for i in range(nodes)]
        depots = random.sample(nodes_list,3)
        start_list = {
                        "A":str(depots[0]),
                        "B":str(depots[1]),
                        "C":str(depots[2])
                        # "type_D":nodes_list.pop(random.randrange(len(nodes_list))),
                        # "type_E":nodes_list.pop(random.randrange(len(nodes_list)))
                    }

        test_data = {
            'Big_number' : Big_number,
            'Autonomy' : random.randint(autonomy_range[0],autonomy_range[1]),
            'charging_coefficient' : random.randint(1,3),
            'nodes' : nodes_list,
            'start_list' : start_list,
            'charging_stations': [str(i) for i in depots], #random.sample(nodes_list,k=int(nodes/5)),
            'hub_nodes' : [str(i) for i in depots]
        }


        to_dump.update({'test_data':test_data})

        ves = randomList(3, num_vehicles)

        vehicles =  {
                        "A": {
                            "units":ves[0]
                            },
                        "B": {
                            "units":ves[1]
                            },
                        "C": {
                            "units":ves[2]
                            }
                        }


        to_dump.update({'ATRs':vehicles})

        if nodes == 15:
            if edges_reduction == 0:
                edges = edges_15_100
            elif edges_reduction == 25:
                edges = edges_15_75
            elif edges_reduction == 50:
                edges = edges_15_50
            else:
                raise ValueError('WRONG EDGE REDUCTION')
        elif nodes == 25:
            if edges_reduction == 0:
                edges = edges_25_100
            elif edges_reduction == 25:
                edges = edges_25_75
            elif edges_reduction == 50:
                edges = edges_25_50
            else:
                raise ValueError('WRONG EDGE REDUCTION')
        elif nodes == 35:
            if edges_reduction == 0:
                edges = edges_35_100
            elif edges_reduction == 25:
                edges = edges_35_75
            elif edges_reduction == 50:
                edges = edges_35_50
            else:
                raise ValueError('WRONG EDGE REDUCTION')
        else:
            raise ValueError('WRONG NUMBER OF NODES')


        vehicles_per_job = [random.randint(1,sum([
                                1  if vehicles[j]['units'] > 0 else 0 for j in vehicles
                                    ])) for i in range(num_jobs)]

        # print(vehicles_per_job)

        buffer_node_list = nodes_list.copy()
        for i in depots:
            buffer_node_list.remove(i)

        pickup_per_job = [random.choice(buffer_node_list) for _ in range(num_jobs)]

        double_buffer_node_list = buffer_node_list.copy()
        for i in pickup_per_job:
            if i in double_buffer_node_list:
                double_buffer_node_list.remove(i)
        deliveries_per_job = [random.choice(double_buffer_node_list) for _ in range(num_jobs)]

        edges_for_graph = {(int(i.split(',')[0]),int(i.split(',')[1])):edges[i] for i in edges}

        with open('paths_container/PL_{}_{}.json'.format(nodes,edges_reduction),'r') as read_file:
            paths = json.load(read_file)

        jobs = {}
        # print('bibidi')
        for i in range(num_jobs):
            lower_bound = random.randint(5,Big_number-10)
            # print(lower_bound)
            upper_bound = min(lower_bound + 10,Big_number-5)
            jobs.update({
                'job_{}'.format(i+1):{
                    'tasks':{
                        '1':{
                            'location':str(pickup_per_job[i]),
                            'precedence':[],
                            'TW':"None",
                            'Service': random.randint(1,3)
                        },
                        '2':{
                            'location':str(deliveries_per_job[i]),
                            'precedence':['1'],
                            'TW':[lower_bound,upper_bound],
                            'Service': random.randint(1, 3)
                        }
                    },
                    'ATR':random.sample([i for i in vehicles if vehicles[i]['units']>0],
                                             k=vehicles_per_job[i]
                                             )
                }
            })



        to_dump.update({'jobs':jobs})

        to_dump.update({'edges': edges})

        # pprint(test_data)
        # pprint(vehicles)
        # pprint(jobs)
        # pprint(edges)

        with open('test_cases/MM_{}_{}_{}_{}.json'.format(
                                                        NVJ,
                                                        edges_reduction,
                                                        Big_number,
                                                        SEED
                                                        ), 'w+') as write_file:
                json.dump(to_dump,write_file,indent=4)


# def path_generator(nodes,edges_reduction):
#
#     print(nodes,edges_reduction)
#
#     to_dump = {}
#
#     if nodes == 15:
#         if edges_reduction == 0:
#             edges = edges_15_100
#         elif edges_reduction == 25:
#             edges = edges_15_75
#         elif edges_reduction == 50:
#             edges = edges_15_50
#         else:
#             raise ValueError('WRONG EDGE REDUCTION')
#     elif nodes == 25:
#         if edges_reduction == 0:
#             edges = edges_25_100
#         elif edges_reduction == 25:
#             edges = edges_25_75
#         elif edges_reduction == 50:
#             edges = edges_25_50
#         else:
#             raise ValueError('WRONG EDGE REDUCTION')
#     elif nodes == 35:
#         if edges_reduction == 0:
#             edges = edges_35_100
#         elif edges_reduction == 25:
#             edges = edges_35_75
#         elif edges_reduction == 50:
#             edges = edges_35_50
#         else:
#             raise ValueError('WRONG EDGE REDUCTION')
#     else:
#         raise ValueError('WRONG NUMBER OF NODES')
#
#     nodes_list = [i for i in range(nodes)]
#     edges_for_graph = {(int(i.split(',')[0]), int(i.split(',')[1])): edges[i] for i in edges}
#
#     graph = make_graph(
#         nodes_list,
#         edges_for_graph
#     )
#
#     paths = {
#         # '{},{}'.format(i,j): find_shortest_path(graph, i, j)
#         # for i in nodes_list
#         # for j in nodes_list
#     }
#     for i in nodes_list:
#         for j in nodes_list:
#             print(i,j)
#             paths.update({'{},{}'.format(i,j): find_shortest_path(graph, i, j)})
#
#     to_dump.update(paths)
#
#     with open('paths_container/PL_{}_{}.json'.format(
#                                                     nodes,
#                                                     edges_reduction
#                                                     ), 'w+') as write_file:
#             json.dump(to_dump, write_file, indent=4)



# nodes   num_vehicles   num_jobs   edges_reduction   Big_number   SEED

for SEED in range(5,10):
    for Big_Num in [40,70,100,150,200,300]:
        for NVJ in [[35,9,12],[35,11,15]]: #[15,3,5],[25,4,7]
            for edge_reduction in [0,25,50]:
                make_an_instance(NVJ[0],NVJ[1],NVJ[2],edge_reduction,Big_Num,SEED)

# for NVJ in [[15,3,5],[25,4,7]]:
#     for edge_reduction in [0,25,50]:
#         for Big_Num in [20, 25, 30, 40, 50, 60]:
#             for i in range(5,10):
#                 make_an_instance(NVJ[0],NVJ[1],NVJ[2],edge_reduction,Big_Num,i)



# for nodes in [15,25,35]:
#     for edge_reduction in [0,25,50]:
#         path_generator(nodes,edge_reduction)


