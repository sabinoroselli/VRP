from mono_2 import modello
from Compo_algo import Compositional
from Compo_slim import Compo_slim
from support_functions import list_unknown,list_missing,data_analyzer,data_printer,make_Sequence_Planner_json
from multiprocessing import Pool,cpu_count


def instance_writer(instance,method, UGS = False, routing_model = ''):
    if method == 'CA':
        feasibility, optimum, solving_time, len_prev_routes, paths_changed = Compositional(routing_model,instance,UGS)
        # generation_time = 'None'
    elif method == 'CS':
        feasibility, optimum, solving_time, len_prev_routes, paths_changed = Compo_slim(instance,UGS)
    elif method == 'S' or method == 'O':
        feasibility, optimum, generation_time, solving_time = modello(instance,method)
        len_prev_routes = 'None'
        paths_changed = 'None'
        routing_model = ''
    else:
        raise ValueError('WRONG METHOD')
    with open('data_storage.txt','a+') as write_file:
        write_file.write('{},{},{},{},{},{},{},{},{},{} \n'.format(
                                                            method + routing_model,
                                                            feasibility,
                                                            optimum,
                                                            instance.split('_')[1],
                                                            instance.split('_')[2],
                                                            instance.split('_')[3],
                                                            instance.split('_')[4],
                                                            solving_time,
                                                            len_prev_routes,
                                                            paths_changed
                                                            )
        )
        return instance,method,feasibility,solving_time

###################### HERE IS WHERE THE ACTUAL TESTING STARTS ######################

# the specific problem instance i am solving
# problem = 'MM_1535_50_40_5'
# problem = 'MM_2547_25_30_6'
# problem = 'MM_2547_50_50_5'
# problem = "MM_351115_50_300_9"
# problem = 'path_change_test_1'
# problem = 'Volvo_gpss'
# problem = 'Volvo_AIToC'

######### test Remco instances ###########
# problem = 'example_pathchanger_v2'
# problem = 'example_web_4jobs_v3_withtime_nuance'

#solving method can be optimization 'O' or satisfiability 'S' or compositional algorithm 'CA'

######### MONOMOD ############
# modello(problem,'S')
######### COMSAT WITH UC PATH CHANGING ############
# UCG = False
# print('UCG',UCG)
# Compositional('1',problem, UCG)

problems = [
    # 'example_pathchanger_v1',
    # 'example_pathchanger_v3',
    # 'example_pathchanger_v2',
    # 'example_web_4jobs_v3_withtime',
    'example_web_4jobs_v3_withtime_nuance'
]
UCGs = [
    False,
    # True
]

results = []
for problem in problems:
    for UCG in UCGs:
        print("UCG",UCG)
        instance, optimum, running_time, num_previous_routes, paths_changed, counter = Compositional('1',problem, UCG)
        results.append((problem,UCG,running_time,counter))
for i in results:
    print(i)
######### COMSAT WITH ASSIGNMENT AND ROUTING IN ONE FUNCTION ##########
# Compo_slim(problem,False)
######### TEST EXECUTION ##############
# instance_writer(problem, 'CA', True, '2')

########### INFECTED INSTANCES ###########

### SEQUENTIAL EXECUTION #####
# for routing_model in ['1','2']:
#     for NVJ in [1535,2547]:
#         for edge_reduction in [0,25,50]:
#             for Big_Num in [20, 25, 30, 40, 50, 60]:
#                 for SEED in range(5, 10):
#                     instance_writer('MM_{}_{}_{}_{}'.format(NVJ, edge_reduction, Big_Num, SEED), 'CA', True, routing_model)
# for UGS in [False,True]:
#     for NVJ in [1535,2547]:
#         for edge_reduction in [0,25,50]:
#             for Big_Num in [20, 25, 30, 40, 50, 60]:
#                 for SEED in range(5, 10):
#                     instance_writer('MM_{}_{}_{}_{}'.format(NVJ, edge_reduction, Big_Num, SEED), 'CS',UGS)

# for NVJ in [1535,2547]:
#     for edge_reduction in [0,25,50]:
#         for Big_Num in [20, 25, 30, 40, 50, 60]:
#             for SEED in range(5, 10):
#                 instance_writer('MM_{}_{}_{}_{}'.format(NVJ, edge_reduction, Big_Num, SEED), 'S')


# missing_instances = list_missing('unknown_instances')

# for i in instances:
#     instance_writer(i,'CA')
    # print(i)
# print(len(missing_instances))

# PARALLEL EXECUTION ####

# instances = [
#     ( 'MM_{}_{}_{}_{}'.format(NVJ,edge_reduction,Big_Num,SEED), 'CA')
#     for NVJ in [35912,351115]
#     for edge_reduction in [0,25,50]
#     for Big_Num in [40,70,100,150,200,300]
#     for SEED in range(5,10)
# ]
#
# nprocs = cpu_count()
# print('available cores: ', nprocs)
#
# pool = Pool(processes=nprocs)
#
# multi_result = [pool.apply_async(instance_writer, inp) for inp in missing_instances]
#
# result = [x for p in multi_result for x in p.get()]
# for i in result:
#     print(i)
#
# instances = [
#     ( 'MM_{}_{}_{}_{}'.format(NVJ,edge_reduction,Big_Num,SEED), 'CA')
#     for NVJ in [1535, 2547]
#     for edge_reduction in [0, 25, 50]
#     for Big_Num in [20, 25, 30, 40, 50, 60]
#     for SEED in range(5, 10)
# ]
#
#
# nprocs = cpu_count()
# print('available cores: ', nprocs)
#
# pool = Pool(processes=nprocs)
#
# multi_result = [pool.apply_async(instance_writer, inp) for inp in instances]
#
# result = [x for p in multi_result for x in p.get()]
# for i in result:
#     print(i)

################ DATA ANALYSIS ######################

# whatever = data_analyzer('data_for_evaluation')
#
# for i in whatever:
#     print(i,whatever[i])
#     # print(i)
# data_printer(whatever)

############## LET US PARSE STUFF ##############

# instance,optimum,running_time,len_previous_routes,paths_changed, [node_sequence,current_routes] = \
#     Compo_slim(problem,False)
# if optimum != 'None':
#     make_Sequence_Planner_json(node_sequence, current_routes)




