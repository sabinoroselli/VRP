import json
import networkx as nx
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
                "start": {
                    "tasks": {
                        "0": {
                            "location": list(data['test_data']['start_list'].values())[0],
                            "precedence": [],
                            "TW": "None"
                        }
                    },
                    "ATR": [i for i in ATRs]
                },
                "end": {
                    "tasks": {
                        "0": {
                            "location": list(data['test_data']['start_list'].values())[0],
                            "precedence": [],
                            "TW": [0, Big_number]
                        }
                    },
                    "ATR": [i for i in ATRs]
                }

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

