from MonoMod import modello
from ComSat import Compositional
from support_functions import list_unknown,list_missing,data_analyzer,data_printer
from multiprocessing import Pool,cpu_count


def instance_writer(instance,method):
    if method == 'CA':
        feasibility, optimum, solving_time, len_prev_routes = Compositional(instance)
        generation_time = 'None'
    elif method == 'S' or method == 'O':
        feasibility, optimum, generation_time, solving_time = modello(instance,method)
        len_prev_routes = 'None'
    else:
        raise ValueError('WRONG METHOD')
    with open('data_storage.txt','a+') as write_file:
        write_file.write('{},{},{},{},{},{},{},{},{},{} \n'.format(
                                                            method,
                                                            feasibility,
                                                            optimum,
                                                            instance.split('_')[1],
                                                            instance.split('_')[2],
                                                            instance.split('_')[3],
                                                            instance.split('_')[4],
                                                            generation_time,
                                                            solving_time,
                                                            len_prev_routes
                                                            )
        )
        return instance,method,feasibility,solving_time

###################### HERE IS WHERE THE ACTUAL TESTING STARTS ######################

# the specific problem instance i am solving
# problem = 'MM_1535_50_20_5'
# problem = 'MMM_1535_0_15_5_bis'
# print(problem)

#solving method can be optimization 'O' or satisfiability 'S' or compositional algorithm 'CA'

# modello(problem,'S')
# Compositional(problem)




#### SEQUENTIAL EXECUTION #####

# for NVJ in [35610]:#[1535,2547,3568]:
#     for edge_reduction in [0,25,50]:
#         for Big_Num in [30, 40, 50, 60]:  # [15,20,25,30]:
#             for SEED in range(5, 10):
#                 instance_writer('MM_{}_{}_{}_{}'.format(NVJ,edge_reduction,Big_Num,SEED), 'CA')


missing_instances = list_missing('unknown_instances')

# for i in missing_instances:
#     # instance_writer(i,'CA')
#     print(i)
# print(len(missing_instances))

## PARALLEL EXECUTION ####

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

# instances = [
#     ( 'MM_{}_{}_{}_{}'.format(NVJ,edge_reduction,Big_Num,SEED), 'S')
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

whatever = data_analyzer('data_for_evaluation')

for i in whatever:
    print(i,whatever[i])
    # print(i)
data_printer(whatever)

