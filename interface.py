from monolithic_model import modello

test_case = 'test_case_7'
# test_case = 'MM_1535_0_20_5'

#solving method can be optimization 'O' or satisfiability ''
method = 'S'

# this variable is 'default' if all vehicles start at node 0, anything else otherwise
# (in that case starting point must be specified)
depot_condition = ''

param = modello(test_case,method,depot_condition)

# for i in range(5,10):
#     test_case = 'MM_1535_0_40_{}'.format(i)
#     param = modello(test_case,method,depot_condition)

def instance_runner(method,nodes,vehicles,jobs,edge_reduction,horizon,SEED):

    instance = 'MM_{}_{}_{}_{}'.format(
                                        str(nodes) + str(vehicles) + str(jobs),
                                        edge_reduction,
                                        horizon,
                                        SEED
    )

    print('solving: ', instance)

    feasibility, optimum, generation_time, solving_time = modello(instance,method,'')

    with open('data_storage.txt','a+') as write_file:
        write_file.write('{},{},{},{},{},{},{},{},{},{},{} \n'.format(
                                                method,
                                                feasibility,
                                                optimum,
                                                nodes,
                                                vehicles,
                                                jobs,
                                                edge_reduction,
                                                horizon,
                                                SEED,
                                                round(generation_time,2),
                                                round(solving_time,2)
                                                )
        )
# THIS IS OBSOLETE NOW, THE FUNCTION MODELLO DOES THE WRITING AS WELL!!!
# instance_runner('S',15,3,3,0,20,7)
# for NVJ in [[35,5,9]]: # [15,3,5],[25,4,7],
#     for edge_red in [0,25,50]:
#         for horizon in [15,20,25,30]:
#             for SEED in [5,6,7,8,9]:
#                 instance_runner('S',NVJ[0],NVJ[1],NVJ[2],edge_red,horizon,SEED)