import random
from pprint import *
import json
from edges_for_graphs import *

# Utility function to print the
# elements of an array
def printArr(arr, n):
    for i in range(n):
        print(arr[i], end=" ")

    # Function to generate a list of


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

# this function filters the list of nodes such that each node is not further than a certain constant
# from each node in a given set
def maximum_distance_from_node():
    return


def make_an_instance(nodes,num_vehicles,num_jobs,Big_number,edges_reduction,SEED):

        NVJ = str(nodes) + str(num_vehicles) + str(num_jobs)

        to_dump = {}

        random.seed(SEED)

        # range of possible operating range as a function of the number of nodes
        if nodes == 15:
            autonomy_range = [6,12]
        elif nodes == 25:
            autonomy_range = [8,16]
        elif nodes == 35:
            autonomy_range = [10,20]
        else:
            raise ValueError('WRONG NUMBER OF NODES')

        # list of charging stations as a function of the number of nodes
        if nodes == 15:
            charging_stations = [6,8]
        elif nodes == 25:
            charging_stations = [6,8,16,18]
        elif nodes == 35:
            charging_stations = [6,8,16,18,26,28]
        else:
            raise ValueError('WRONG NUMBER OF NODES')



        nodes_list = [i for i in range(nodes)]

        start_list = {
                        "type_A":nodes_list.pop(random.randrange(len(nodes_list))),
                        "type_B":nodes_list.pop(random.randrange(len(nodes_list))),
                        "type_C":nodes_list.pop(random.randrange(len(nodes_list))),
                        # "type_D":nodes_list.pop(random.randrange(len(nodes_list))),
                        # "type_E":nodes_list.pop(random.randrange(len(nodes_list)))
                    }

        test_data = {
            'Big_number' : Big_number,
            'Autonomy' : random.randint(autonomy_range[0],autonomy_range[1]),
            'charging_coefficient' : random.randint(1,3),
            'nodes' : nodes,
            'start_list' : start_list,
            'charging_stations': charging_stations, #random.sample(nodes_list,k=int(nodes/5)),
            'hub_nodes' : list(start_list.values())
        }


        to_dump.update({'test_data':test_data})

        ves = randomList(3, num_vehicles)

        vehicles =  {
                        "type_A": {
                            "units":ves[0]
                            },
                        "type_B": {
                            "units":ves[1]
                            },
                        "type_C": {
                            "units":ves[2]
                            }
                        }


        to_dump.update({'ATRs':vehicles})


        vehicles_per_job = [random.randint(1,sum([
                                1  if vehicles[j]['units'] > 0 else 0 for j in vehicles
                                    ])) for i in range(num_jobs)]

        # print(vehicles_per_job)

        deliveries_per_job = [nodes_list.pop(random.randint(0,len(nodes_list)-1)) for i in range(num_jobs) ]
        # print(deliveries_per_job)

        jobs = {
            'job_{}'.format(i+1):{
                'tasks':{
                    '1':{
                        'location':random.choice(nodes_list),
                        'precedence':[],
                        'TW':"None"
                    },
                    '2':{
                        'location':deliveries_per_job[i],
                        'precedence':['1'],
                        'TW':[5,Big_number-5]
                    }
                },
                'ATR':random.sample([i for i in vehicles if vehicles[i]['units']>0],
                                         k=vehicles_per_job[i]
                                         )
            } for i in range(num_jobs)
        }

        to_dump.update({'jobs':jobs})

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

        to_dump.update({'edges':edges})

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



# nodes   num_vehicles   num_jobs   Big_number   edges_reduction   SEED

for SEED in range(5,10):
    for Big_Num in [15,20,25,30]:
        for NVJ in [[15,3,5],[25,4,7]]: # [15,3,5],[25,4,7],[35,6,8]
            for edge_reduction in [0,25,50]:
                make_an_instance(NVJ[0],NVJ[1],NVJ[2],Big_Num,edge_reduction,SEED)

# make_an_instance(35,6,8,30,0,7)

