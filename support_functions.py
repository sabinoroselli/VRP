import json
import networkx as nx
import csv
from itertools import islice
# this function takes a list of edges (supposedly belonging to a graph) and calculates
# the distance between any two points in the graph when taking the given path
def distance(path,edges):
    total_distance = 0
    for i in range(len(path)-1):
        # print(path[i],path[i + 1],edges[(path[i] , path[i+1])])
        total_distance += edges[(path[i] , path[i+1])][0]
    return total_distance

# just a function to help me print dics and lists i use in the code
def print_support(iterable):
    if type(iterable) == dict:
        for i in iterable:
            print(i,iterable[i])
    elif type(iterable) == list:
        for i in iterable:
            print(i)
    else:
        print('this is not a dict nor a list, it is a ', type(iterable))
    return None

# just a function to help sorting lists
def take_second(elem):
    return elem[1]

# builds a graph structure out of nodes and edges
def make_graph(nodes,edges):
    graph = {
        i: [elem[1] for elem in edges  if i == elem[0]] for i in nodes
    }
    return graph

def json_parser(file_to_parse,monolithic = False):
    with open(file_to_parse,'r') as read_file:
        data = json.load(read_file)
    Big_number = data['test_data']['Big_number']
    charging_stations = data['test_data']['charging_stations']
    hub_nodes = data['test_data']['hub_nodes']
    start_list = data['test_data']['start_list']

    Autonomy = data['test_data']['Autonomy']
    charging_coefficient = data['test_data']['charging_coefficient']
    nodes = [i for i in range(data['test_data']['nodes'])]
    jobs = data['jobs']
    ATRs = data['ATRs']

    if monolithic == False:
        jobs.update(
            {
                "start_{}".format(i): {
                    "tasks": {
                        "0": {
                            "location": start_list[i],
                            "precedence": [],
                            "TW": "None",
                            "Service": 0
                        }
                    },
                    "ATR": i
                }
            for i in start_list
            }
        )
        jobs.update(
            {
                "end_{}".format(i): {
                    "tasks": {
                        "0": {
                            "location": start_list[i],
                            "precedence": [],
                            "TW": [0, Big_number],
                            "Service": 0
                        }
                    },
                    "ATR": i
                }
            for i in start_list
            }
        )
    buffer = data['edges']
    edges = {
        (int(i.split(',')[0]),int(i.split(',')[1])):buffer[i] for i in buffer}
    if monolithic == False:
        return jobs,nodes,edges,Autonomy,ATRs,charging_coefficient
    else:
        return jobs,nodes,edges,Autonomy,ATRs,charging_coefficient,\
               Big_number,charging_stations,hub_nodes,start_list

# this requirement avoids the algorithm to go on for a long time trying to find a feasible solution while the problem
# is clearly unsat because there are not enough robots to execute all the jobs in time.
def ATRs_requirement(routes_plus,ATRs):
    count = {
        i:sum([1 if i in j[3] and len(j[3])<2 else 0 for j in routes_plus]) for i in ATRs
    }
    # print(count)
    result = [False if ATRs[i]['units'] >= count[i] else True for i in ATRs ]
    # print(result)
    return any(result)

# I need this function to generate k paths to connect any two points of interest
def k_shortest_paths(G, source, target, k, weight=None):
    return list(islice(nx.shortest_simple_paths(G, source, target, weight=weight), k))

def paths_formatter(current_routes,current_paths,tasks):
    # this dictonary contains the paths used to traverse the routes
    paths_combo = {
        route_index: {
            (tasks[first], tasks[second]):
                current_paths[(first, second)] for first, second in zip(route[0][:-1], route[0][1:])
        }
        for route_index, route in enumerate(current_routes)
    }

    # convert the shortest path solution into a fromat that can be inputed into the path_changing function
    shortest_paths_solution = [
        (route, pair, (first, second))
        for route in paths_combo
        for pair_index, pair in enumerate(paths_combo[route])
        for first, second in zip(paths_combo[route][pair][:-1], paths_combo[route][pair][1:])
    ]

    return shortest_paths_solution, paths_combo

############# THE FOLLOWING FUNCTIONS ARE USED TO MANIPULATE THE TEXT FILES
############# CONTAINING THE TESTS DATA

def list_unknown(file):
    with open(file,'r') as in_file:
        reader = csv.reader(in_file, delimiter=",")
        buffer = []
        for i in reader:
            if i[1] == 'unknown':
                buffer.append('MM_{}_{}_{}_{}'.format(
                    i[3],
                    i[4],
                    i[5],
                    i[6]
                ))
    return buffer

def list_missing(file):

    instances = [

        [NVJ,edge_reduction,Big_Num,SEED]

        for NVJ in [35912,351115]
        for edge_reduction in [0, 25, 50]
        for Big_Num in [40,70,100,150,200,300]
        for SEED in range(5, 10)

            ]
    # print('instances')
    # for i in instances:
    #     print(i)

    with open(file,'r') as in_file:
        reader = csv.reader(in_file, delimiter=",")
        buffer = []
        # print('reader')
        for i in reader:
            # print([i[3],i[4],i[5],i[6],i[7],i[8]])
            if  [int(i[3]),int(i[4]),int(i[5]),int(i[6])] in instances:
                buffer.append( [int(i[3]),int(i[4]),int(i[5]),int(i[6])]

                )

    return_list = [
        ('MM_{}_{}_{}_{}'.format(
                    str(i[0]),
                    i[1],
                    i[2],
                    i[3]
                ),'CA')
        for i in instances if i not in buffer
    ]


    return return_list

def data_analyzer(file):
    with open(file, 'r') as in_file:
        reader = csv.reader(in_file, delimiter=",")
        buffer = []
        for i in reader:
            buffer.append(i)

    grouper = {}
    for method in ['CA']:#,'S']:
        for NVJ in [35912, 351115]:
          for edge_reduction in [0, 25, 50]:
            for Big_Num in [40,70,100,150,200,300]:
                grouper.update({
                    (method,NVJ,edge_reduction,Big_Num):[]
                })

    for key in grouper:
        for instance in buffer:
            if key[0] == instance[0] \
                    and str(key[1]) == instance[3] \
                    and str(key[2]) == instance[4] \
                    and str(key[3]) == instance[5]:
                grouper[key].append(instance)

    # for i in grouper:
    #     print(i,grouper[i])
    data = {}
    for key in grouper:
        counter_sat = 0
        cum_solving_time_sat = 0
        counter_unsat = 0
        cum_solving_time_unsat = 0
        for instance in grouper[key]:
            if float(instance[8]) < 1200:
                if instance[1] == 'sat':
                    counter_sat += 1
                    cum_solving_time_sat += float(instance[8])
                elif instance[1] == 'unsat':
                    counter_unsat += 1
                    cum_solving_time_unsat += float(instance[8])
        data.update({
            key:[
                round(cum_solving_time_sat/counter_sat if counter_sat > 0 else cum_solving_time_sat,2),
                '\'{}/5'.format(counter_sat),
                round(cum_solving_time_unsat / counter_unsat if counter_unsat > 0 else cum_solving_time_unsat,2),
                '\'{}/5'.format(counter_unsat)
            ]})

    return data

def data_printer(data):
    with open('data_for_table_3.txt','w+',newline='') as write_file:

        for big_number in [40,70,100,150,200,300]:
            for method in ['CA']:
                buffer = []
                for NVJ in [35912, 351115]:
                    for edge_reduction in [0, 25, 50]:
                        buffer.append(data[(method,NVJ,edge_reduction,big_number)][0])
                        buffer.append(data[(method,NVJ,edge_reduction,big_number)][1])
                        buffer.append(data[(method, NVJ, edge_reduction, big_number)][2])
                        buffer.append(data[(method, NVJ, edge_reduction, big_number)][3])
                writer = csv.writer(write_file,delimiter=',')
                writer.writerow(buffer)

