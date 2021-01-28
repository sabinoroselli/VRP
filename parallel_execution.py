from multiprocessing import Pool,cpu_count
from monolithic_model import modello
import csv


instances = [
    (
        'MM_{}_{}_{}_{}'.format(
                                str(NVJ[0]) + str(NVJ[1]) + str(NVJ[2]),
                                edge_reduction,
                                horizon,
                                SEED
                                ),
        'S',
        ''
    )
    for NVJ in [[15,3,5],[25,4,7]] #,[35,6,8]
        for edge_reduction in [0,25,50]
            for horizon in [15,20,25,30]
                for SEED in [5,6,7,8,9]
]

# instances = []
# with open('re_runs.txt',mode='r') as in_file:
#     reader = csv.reader(in_file,delimiter=',')
#     for i in reader:
#         if i[1] == 'unknown':
#             instances.append((
#         'MM_{}_{}_{}_{}'.format(
#                                 str(i[3]) + str(i[4]) + str(i[5]),
#                                 i[6],
#                                 i[7],
#                                 i[8]
#                                 ),
#         'S',
#         ''
#                              ))
# print(instances)

nprocs = cpu_count()
# print('available cores: ', nprocs)

pool = Pool(processes=nprocs)

multi_result = [pool.apply_async(modello, inp) for inp in instances]

result = [x for p in multi_result for x in p.get()]
# for i in result:
#     print(result)


