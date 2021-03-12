from monolithic_model import modello
from compo_algo import the_algorithm
from multiprocessing import Pool,cpu_count

# test_case = 'test_case_10'
test_case = 'MM_1535_0_15_6'


#solving method can be optimization 'O' or satisfiability 'S' or compositional algorithm 'CA'

# param1 = modello(test_case,'S')

param2 = the_algorithm(test_case)

def instance_writer(instance,method):
    if method == 'CA':
        feasibility, optimum, generation_time, solving_time = the_algorithm(instance)
    elif method == 'S' or method == 'O':
        feasibility, optimum, generation_time, solving_time = modello(instance,method)
    else:
        raise ValueError('WRONG METHOD')
    with open('data_storage.txt','a+') as write_file:
        write_file.write('{},{},{},{},{},{},{},{},{},{},{} \n'.format(
                                                            method,
                                                            feasibility,
                                                            optimum,
                                                            instance.split('_')[1][0] + instance.split('_')[1][1],
                                                            instance.split('_')[1][2],
                                                            instance.split('_')[1][3],
                                                            instance.split('_')[2],
                                                            instance.split('_')[3],
                                                            instance.split('_')[4],
                                                            generation_time,
                                                            solving_time
                                                            )
        )
        return instance,method,feasibility,solving_time

#### SEQUENTIAL EXECUTION #####

# for i in range(16):
#     instance_writer('MM_1535_0_15_{}'.format(i), 'CA')


#### PARALLEL EXECUTION ####

# instances = [
#     ( 'MM_{}_{}_{}_{}'.format(NVJ,edge_reduction,Big_Num,SEED), 'CA' )
#     for SEED in range(5,10)
#     for Big_Num in [15,20,25,30]
#     for NVJ in [1535,2547,3568]
#     for edge_reduction in [0,25,50]
# ]
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
#
# instances = [
#     ( 'MM_{}_{}_{}_{}'.format(NVJ,edge_reduction,Big_Num,SEED), 'S' )
#     for SEED in range(5,10)
#     for Big_Num in [15,20,25,30]
#     for NVJ in [1535,2547,3568]
#     for edge_reduction in [0,25,50]
# ]
#
#
# pool = Pool(processes=nprocs)
#
# multi_result = [pool.apply_async(instance_writer, inp) for inp in instances]
#
# result = [x for p in multi_result for x in p.get()]
# for i in result:
#     print(i)


