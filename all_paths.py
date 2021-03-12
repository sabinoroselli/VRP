import itertools
#
# graph = {'A': ['B', 'C'],
#              'B': ['C', 'D'],
#              'C': ['D'],
#              'D': ['C'],
#              'E': ['F'],
#              'F': ['C']}


def find_path(graph, start, end, path=[]):
    path = path + [start]
    if start == end:
        return path
    if start not in graph:
        return None
    for node in graph[start]:
        if node not in path:
            newpath = find_path(graph, node, end, path)
            if newpath: return newpath
    return None

# print(find_path(graph,'A','D'))


def find_all_paths(graph, start, end, path=[]):
    path = path + [start]
    if start == end:
        return [path]
    if start not in graph:
        return []
    paths = []
    for node in graph[start]:
        if node not in path:
            newpaths = find_all_paths(graph, node, end, path)
            for newpath in newpaths:
                paths.append(newpath)
    return paths

# print(find_all_paths(graph,'A','D'))

def find_shortest_path(graph, start, end, path=[]):
    path = path + [start]
    if start == end:
        return path
    if start not in graph:
        return None
    shortest = None
    for node in graph[start]:
        if node not in path:
            newpath = find_shortest_path(graph, node, end, path)
            if newpath:
                if not shortest or len(newpath) < len(shortest):
                    shortest = newpath
    return shortest

# print([find_shortest_path(graph,'A','D')])

# Paths = {
#     (i,j):find_all_paths(graph,i,j,path=[]) for i in graph for j in graph if i != j and find_all_paths(graph,i,j,path=[]) != []
# }
#
#
#
#
# for i in Paths:
#     print(i,Paths[i])
#
# prova = list(itertools.product(*list(Paths.values())))
# print('*************')
# for i in prova:
#     print(i)
#
# print(len(prova))
#
# one_path = {
#     i:j for i,j in zip(Paths,prova.pop(0))
# }
#
# while prova != []:
#     one_path = {
#     i:j for i,j in zip(Paths,prova.pop(0))
#       }
#     print(one_path)
#     print(len(prova))

