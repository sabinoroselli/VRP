from z3 import *
from funzioni_di_supporto import distance

def path_finder(Paths,edges,used_paths = []):
    # HERE I BUILD THE MODEL TO FIND A FEASIBLE PATH

    path_variable = [[Bool('points_%s_path_%s' % (i, j_index)) for j_index, _ in enumerate(Paths[i])] for i in Paths]

    # exactly one path can be chosen for each pair of points
    exactly_one_path = [
        PbEq([
            (path_variable[i][j], 1)
            for j, _ in enumerate(Paths[path])
        ], 1)
        for i, path in enumerate(Paths)
    ]

    path_selection = Optimize()

    path_selection.add(exactly_one_path)

    if used_paths != []:
        previous_paths = [
            Or([
                Not(path_variable[i[0]][i[1]])
                for i in solution
            ])
            for solution in used_paths
        ]
        path_selection.add(previous_paths)

    path_selection.minimize(
        Sum([
            If(
                path_variable[i][j],
                distance(one_path,edges),
                0
            )
            for i, path in enumerate(Paths)
            for j, one_path in enumerate(Paths[path])
        ])
    )

    PF = path_selection.check()
    path_buffer = []
    if PF == sat:
        m0 = path_selection.model()
        for i, path in enumerate(Paths):
            for j, _ in enumerate(Paths[path]):
                if m0[path_variable[i][j]] == True:
                    path_buffer.append([i,j])
    return PF, path_buffer