import copy
import collections
import numpy as np
import simpy
import random
import matplotlib.pyplot as plt
import plotly
import plotly.express as px
import pandas as pd
from collections import defaultdict
import os
import pickle

# jobs_data = [  # task = (machine_id, processing_time).
#     [(0, 3), (1, 2), (2, 2)],  # Job0
#     [(0, 2), (2, 1), (1, 4)],  # Job1
#     [(1, 4), (2, 3)]  # Job2
# ]

random.seed(42)

# jobs_data = [  # task = (machine_id, processing_time).
#     [(0, 3), (1, 2), (3, 2), (2, 2), (4, 4)],  # Job0
#     [(4, 2), (1, 1), (2, 4), (0, 1), (3, 2)],  # Job1
#     [(2, 4), (3, 3), (0, 2), (1, 4), (4, 2)],  # Job2
#     [(3, 2), (1, 1), (2, 4), (4, 1), (0, 2)],  # Job3
#     [(2, 4), (3, 3), (1, 2), (0, 4), (4, 3)]  # Job4
# ]
#
# jobs_data = [  # task = (machine_id, processing_time).
#     [(0, 3), (1, 6), (2, 2), (3, 2), (4, 4)],  # Job0
#     [(1, 2), (2, 2), (3, 4), (4, 1), (5, 2)],  # Job1
#     [(2, 4), (3, 3),  (5, 4), (0, 1), (4, 2)],  # Job2
#     [(3, 2), (4, 4), (5, 4), (0, 1), (1, 2)],  # Job3
#     [(4, 2), (5, 9), (0, 4), (1, 2), (5, 4)],  # Job4
#     [(5, 4), (0, 2), (1, 2), (2, 4), (3, 2)],  # Job5
#     [(0, 2), (1, 3), (2, 6), (3, 1), (4, 4)],  # Job6
#     [(1, 2), (2, 1), (3, 4), (4, 3), (5, 2)]  # Job7
# ]

"""
FT10 Problem(Fisher and Thompson, 1963)
"""
jobs_data = [
    [(0, 29), (1, 78), (2, 9), (3, 36), (4, 49), (5, 11), (6, 62), (7, 56), (8, 44), (9, 21)],
    [(0, 43), (2, 90), (4, 75), (9, 11), (3, 69), (1, 28), (6, 46), (5, 46), (7, 72), (8, 30)],
    [(1, 91), (0, 85), (3, 39), (2, 74), (8, 90), (5, 10), (7, 12), (6, 89), (9, 45), (4, 33)],
    [(1, 81), (2, 95), (0, 71), (4, 99), (6, 9), (8, 52), (7, 85), (3, 98), (9, 22), (5, 43)],
    [(2, 14), (0, 6), (1, 22), (5, 61), (3, 26), (4, 69), (8, 21), (7, 49), (9, 72), (6, 53)],
    [(2, 84), (1, 2), (5, 52), (3, 95), (8, 48), (9, 72), (0, 47), (6, 65), (4, 6), (7, 25)],
    [(1, 46), (0, 37), (3, 61), (2, 13), (6, 32), (5, 21), (9, 32), (8, 89), (7, 30), (4, 55)],
    [(2, 31), (0, 86), (1, 46), (5, 74), (4, 32), (6, 88), (8, 19), (9, 48), (7, 36), (3, 79)],
    [(0, 76), (1, 69), (3, 76), (5, 51), (2, 85), (9, 11), (6, 40), (7, 89), (4, 26), (8, 74)],
    [(1, 85), (0, 13), (2, 61), (6, 7), (8, 64), (9, 76), (5, 47), (3, 52), (4, 90), (7, 45)]
]

NUM_MACHINE = 0
for i in range(len(jobs_data)):
    for j in range(len(jobs_data[i])):
        # print(jobs_data[i][j][0])
        max_machine = jobs_data[i][j][0]
        if max_machine > NUM_MACHINE:
            NUM_MACHINE = max_machine
NUM_MACHINE += 1

NUM_POPULATION = 500
P_CROSSOVER = 0.5
P_MUTATION = 0.9
N_JOBS = 10
N_OP_per_JOBS = 10
N_OPERATION = 100


# N_JOBS = len(jobs_data)  # 10
# for i in range(len(jobs_data)):
#     N_OPERATION += len(jobs_data[i])

class Individual:
    def __init__(self, seq):
        self.seq = seq
        self.none_repetitive = None
        self.makespan = 0

    def repeatable(self):
        self.none_repetitive = []



class Job:
    def __init__(self, env, id, job_data):
        self.env = env
        self.id = id
        # print('Job ',id,' generated!')
        self.n = len(job_data)
        self.m = [job_data[i][0] for i in range(len(job_data))]  # machine
        # print('Job %d Machine list : ' % self.id, self.m)
        self.d = [job_data[i][1] for i in range(len(job_data))]  # duration
        self.o = [Operation(env, self.id, i, self.m[i], self.d[i]) for i in range(self.n)]
        self.completed = 0
        self.scheduled = 0
        # List to track waiting operations
        self.finished = env.event()

        self.execute()

    def execute(self):
        self.env.process(self.next_operation_ready())

    def next_operation_ready(self):
        for i in range(self.n):
            self.o[i].waiting.succeed()
            # print('%d Operation %d%d is completed, waiting for Operation %d%d to be completed ...' % (env.now, self.id, self.completed, self.id, self.completed+1))
            yield self.o[i].finished
            # print('%d Operation %d%d Finished!' % (self.env.now, self.id, self.completed))
        # print('%d Job %d All Operations Finished!' % (self.env.now, self.id))
        self.finished.succeed()


class Operation:
    def __init__(self, env, job_id, op_id, machine, duration):
        # print('Operation %d%d generated!' % (job_id, op_id))
        self.env = env
        self.job_id = job_id
        self.op_id = op_id
        self.machine = machine
        self.duration = duration
        self.starting_time = 0.0
        self.finishing_time = 0.0
        self.waiting = self.env.event()
        self.finished = self.env.event()


class Machine:
    def __init__(self, env, id):
        # print('Machine ',id,' generated!')
        self.id = id
        self.env = env
        self.machine = simpy.Resource(self.env, capacity=1)
        self.queue = simpy.Store(self.env)
        self.available_num = 0
        self.waiting_operations = {}
        # self.availability = [self.env.event() for i in range(100)]
        # self.availability[0].succeed()
        self.availability = self.env.event()
        self.availability.succeed()
        self.workingtime_log = []

        self.execute()

    def execute(self):
        self.env.process(self.processing())

    def processing(self):
        while True:
            op = yield self.queue.get()
            # print('%d : Job %d is waiting on M%d' % (self.env.now, job.id, self.id))

            # yield self.availability[self.available_num]
            self.available_num += 1
            yield self.availability
            self.availability = self.env.event()

            # print('M%d Usage Count : %d' %(self.id, self.available_num))

            yield op.waiting  # waiting이 succeed로 바뀔 떄까지 기다림
            starting_time = self.env.now
            op.starting_time = starting_time

            yield self.env.timeout(op.duration)
            finishing_time = self.env.now
            op.finishing_time = finishing_time
            op.finished.succeed()

            self.workingtime_log.append((op.job_id, starting_time, finishing_time))

            # print('%d Operation %d%d Finished on M%d!' % (self.env.now, op.job_id, op.op_id, self.id))
            # self.availability[self.available_num].succeed()
            self.availability.succeed()


class Scheduler:
    def __init__(self, env, jobs_data, num_machine, sequence):
        self.env = env
        self.job_list = []
        self.machine_list = []
        self.c_max = 0

        for i in range(len(jobs_data)):
            self.job_list.append(Job(self.env, i, jobs_data[i]))

        for i in range(num_machine):
            self.machine_list.append(Machine(self.env, i))

        self.sequence = sequence.copy()  # sequence = list

    def schedule(self):
        for i in self.sequence:  # 0 0 1 2 1 2 0 1
            o_ = self.job_list[i].scheduled  # 0 1 0 0 1 1 2 2
            m_ = self.job_list[i].m[o_]  # 0 1 0 1 2 2 2 1

            self.machine_list[m_].queue.put(self.job_list[i].o[o_])
            self.job_list[i].scheduled += 1
            # print('Operation %d%d scheduled on M%d!' % (i, o_, m_))

    def evaluate(self):
        finished_jobs = [self.job_list[i].finished for i in range(len(self.job_list))]
        yield simpy.AllOf(self.env, finished_jobs)
        self.c_max = self.env.now
        # print("Total Makespan : ", self.c_max)


# Global Search
def optimize_makespan():
    # Generate Sequence
    result = []
    for i in range(1000):
        sequence = [i for i in range(N_OPERATION)]
        sequence = np.array(random.sample(sequence, len(sequence)))

        # Generating Job sequence from the random numbers (i.e. 0~4 refers to Job0, 5~9 refers to Job1, and so on.)
        cumul = 0
        for i in range(len(jobs_data)):
            for j in range(len(jobs_data[i])):
                sequence = np.where((sequence >= cumul) & (sequence < cumul + len(jobs_data[i])), i, sequence)
            cumul += len(jobs_data[i])

        print('Sequence : ', sequence, end=', ')

        env = simpy.Environment()
        scheduler = Scheduler(env, jobs_data, 6, sequence)
        scheduler.schedule()
        env.process(scheduler.evaluate())
        env.run()
        print("Total Makespan : ", scheduler.c_max)
        result.append([sequence, scheduler.c_max])

    makespan = [result[i][1] for i in range(len(result))]
    optimal = []
    for i in range(len(result)):

        if result[i][1] == min(makespan):
            print(result[i][0], 'makespan of ', result[i][1])
            optimal.append(result[i][0])

    return optimal


# Validation of the result
def show_optimum_result(optimal):
    for sequence in optimal:
        # print('-' * 40)
        # # print('Sequence : ', sequence)
        # cumul = 0
        # for i in range(len(jobs_data)):
        #     for j in range(len(jobs_data[i])):
        #         sequence = np.where((sequence >= cumul) & (sequence < cumul + len(jobs_data[i])), i, sequence)
        #     cumul += len(jobs_data[i])
        # sequence = sequence.tolist()
        env = simpy.Environment()
        scheduler = Scheduler(env, jobs_data, NUM_MACHINE, sequence)  # sequence = list
        scheduler.schedule()
        env.process(scheduler.evaluate())
        env.run()
        for i in range(len(scheduler.machine_list)):
            print('M%d ' % i, scheduler.machine_list[i].workingtime_log)

        del env, scheduler


def generate_sequence(jobs_data_, num_operation_):
    sequence_ = [i for i in range(num_operation_)]  # sequence = list
    sequence_ = np.array(random.sample(sequence_, len(sequence_)))  # sequence = numpy array
    cumul = 0  # cumulative sum
    for i in range(len(jobs_data_)):
        for j in range(len(jobs_data_[i])):
            sequence_ = np.where((sequence_ >= cumul) &
                                 (sequence_ < cumul + len(jobs_data_[i])), i, sequence_)
        cumul += len(jobs_data_[i])
    # Generating Job sequence from random numbers
    sequence_ = sequence_.tolist()  # sequence = numpy array
    return sequence_  # sequence = list


def run_simulation(jobs_data_, sequence_):
    # Decoding the sequence into scheduling result
    # (i.e. 0~4 refers to Job0, 5~9 refers to Job1, and so on.)
    # cumul = 0 # cumulative sum
    # for i in range(len(jobs_data_)):
    #     for j in range(len(jobs_data_[i])):
    #         sequence_ = np.where((sequence_ >= cumul) &
    #                              (sequence_ < cumul + len(jobs_data_[i])), i, sequence_)
    #     cumul += len(jobs_data_[i])
    # sequence_ = sequence_.tolist()

    env = simpy.Environment()
    scheduler_ = Scheduler(env, jobs_data, NUM_MACHINE, sequence_)  # sequence = list
    scheduler_.schedule()
    env.process(scheduler_.evaluate())
    env.run()
    makespan = scheduler_.c_max
    del env, scheduler_
    return makespan


def initialize_population():  # return a list of sequence
    population = []
    for i in range(NUM_POPULATION):
        seq = generate_sequence(jobs_data, N_OPERATION)  # sequence = list
        population.append(seq)
    return population  # population = 2D list


def crossover(p_1, p_2, n):  # p_1, p_2 = 1D list
    # p_1 = p_1.tolist()
    # p_2 = p_2.tolist()
    idx = sorted(random.sample(range(N_OP_per_JOBS), n))
    # print(idx)
    value = [p_1[idx[i]] for i in range(n)]  # 3 7
    # print(value)

    # possible indices of the value

    idx2 = [list(filter(lambda e: p_2[e] == value[i], range(len(p_2)))) for i in range(n)]
    temp = [idx2[i].pop() for i in range(n)]
    if n == 2:
        for i in range(len(temp)):
            if (temp[0] == temp[1]):
                temp[i] = idx2[i].pop()
        idx2 = sorted(temp)
        # print(idx2)
        value2 = [p_2[idx2[0]], p_2[idx2[1]]]
        # print(value2)
        c_1 = copy.deepcopy(p_1)
        c_2 = copy.deepcopy(p_2)
        for i in range(2):
            c_1[idx[i]] = value2.pop(0)
            c_2[idx2[i]] = value.pop(0)
    elif n == 3:
        for i in range(len(temp)):
            if (temp[0] == temp[1] or temp[1] == temp[2] or temp[2] == temp[0]):
                temp[i] = idx2[i].pop()
        idx2 = sorted(temp)
        # print(idx2)
        value2 = [p_2[idx2[0]], p_2[idx2[1]], p_2[idx2[2]]]
        # print(value2)
        c_1 = copy.deepcopy(p_1)
        c_2 = copy.deepcopy(p_2)
        for i in range(3):
            c_1[idx[i]] = value2.pop(0)
            c_2[idx2[i]] = value.pop(0)

    return c_1, c_2  # c_1, c_2 = 1D list


def repeatable_permuation(sequence_, n_job, n_operation):
    cumul = 0
    sequence_ = np.array(sequence_)
    for i in range(n_job):
        for j in range(n_operation):
            sequence_ = np.where((sequence_ >= cumul) &
                                 (sequence_ < cumul + n_operation), i, sequence_)
        cumul += n_operation
    # Generating Job sequence from random numbers
    sequence_ = sequence_.tolist()  # sequence = numpy array
    return sequence_


def PMX_crossover(p1, p2):
    # print('P1 : ', p1)
    # print('P2 : ', p2)
    p_1 = copy.deepcopy(p1)
    p_2 = copy.deepcopy(p2)

    # p_1, p_2를 직접 참조해서 변형하다보니까 2번째 연산부터 숫자가 중복을 포함하지 않은 순열로 변형된 형태가 전달됨
    c_1 = [0 for i in range(len(p_1))]
    c_2 = [0 for i in range(len(p_1))]
    # print('C1 : ', c_1)
    # print('C2 : ', c_2)
    # select range
    r = [random.randint(0, len(p_1) - 1) for _ in range(2)]
    while (min(r) == max(r)):
        r = [random.randint(0, len(p_1) - 1) for _ in range(2)]

    r1 = min(r)  # left end
    r2 = max(r)  # right end

    # 중복을 허용하지 않는 순열로 재구성
    p1_idx_list = [list(filter(lambda e: p_1[e] == i, range(len(p_1)))) for i in
                   range(N_OP_per_JOBS)]  # 10 is the number of operations
    p2_idx_list = [list(filter(lambda e: p_2[e] == i, range(len(p_2)))) for i in range(N_OP_per_JOBS)]

    for k in range(N_JOBS):  # if k = 1,
        indices = p1_idx_list[k]  # indices where p_1 is 8
        t = 0
        for idx in indices:
            p_1[idx] = k * N_OP_per_JOBS + t  # the permutation [8, 8, 8, ... ] is converted to [80, 81, 82, ... ]
            t += 1

    for k in range(N_JOBS):  # if k = 1,
        indices = p2_idx_list[k]  # indices where p_1 is 8
        t = 0
        for idx in indices:
            p_2[idx] = k * N_OP_per_JOBS + t  # the permutation [8, 8, 8, ... ] is converted to [80, 81, 82, ... ]
            t += 1

    # c_1 = p1 + p2 + p1
    # c_2 = p2 + p1 + p2

    slice_1 = p_1[r1:r2]  # c_2에 들어갈 부분
    slice_2 = p_2[r1:r2]  # c_1에 들어갈 부분
    p1a = p_1[:r1] + p_1[r2:]
    p2a = p_2[:r1] + p_2[r2:]
    repeated_idx_1 = []  # p1의 leftover에 slice 2의 요소가 있음
    repeated_idx_2 = []  # p2의 leftover에 slice 1의 요소가 있음

    for e in slice_2:  # c_1에 들어가야 하는 slice 2의 요소가 이미 P1의 leftover에 있으면
        if e in p1a:  # p1a는 c2에게 전달될 예정
            # C1 입장에서, P1에서 반복되어 없어져야 하는 것들
            repeated_idx_1.append(p_1.index(e))  # 해당 중복원소들의 위치를 기록

    for e in slice_1:  # c_2에 들어가야 하는 slice 1의 요소가 이미 P2의 leftover에 있으면
        if e in p2a:
            repeated_idx_2.append(p_2.index(e))  # C2 입장에서, P2에서 반복되어 없어져야 하는 것들

    # 등장하는 index 순서대로 정렬
    repeated_idx_1 = sorted(repeated_idx_1)
    repeated_idx_2 = sorted(repeated_idx_2)

    repeated_p1 = [p_1[n] for n in repeated_idx_1]
    repeated_p2 = [p_2[n] for n in repeated_idx_2]

    left_1 = copy.deepcopy(repeated_p1)
    left_2 = copy.deepcopy(repeated_p2)
    for i in range(len(p_1)):
        if i not in range(r1, r2):
            if p_1[i] not in repeated_p1:
                c_1[i] = p_1[i]
            else:
                # print(p_1[i])
                c_1[i] = left_2.pop(0)
        else:
            c_1[i] = slice_2.pop(0)

    for i in range(len(p_1)):
        if i not in range(r1, r2):
            if p_2[i] not in repeated_p2:
                c_2[i] = p_2[i]
            else:
                c_2[i] = left_1.pop(0)
        else:
            c_2[i] = slice_1.pop(0)
    # print('C1 : ', c_1)
    # print('C2 : ', c_2)
    c_1 = repeatable_permuation(c_1, N_JOBS, N_OP_per_JOBS)
    c_2 = repeatable_permuation(c_2, N_JOBS, N_OP_per_JOBS)

    # dist_c1 = collections.Counter(c_1)
    # dist_c2 = collections.Counter(c_2)
    # # print('Swap Range : (%d, %d)' % (r1, r2))
    # # print('C1 : ', c_1)
    # # print('C2 : ', c_2)
    # c1_any = any([dist_c1[0] != 5, dist_c1[1] != 5, dist_c1[2] != 5, dist_c1[3] != 5, dist_c1[4] != 5])
    # c2_any = any([dist_c2[0] != 5, dist_c2[1] != 5, dist_c2[2] != 5, dist_c2[3] != 5, dist_c2[4] != 5])
    # if c1_any or c2_any:
    #     print('Warning! The number of elements do not match')

    return c_1, c_2


def cycle_crossover(p_1, p_2):
    # p_1 = p_1.tolist()
    # p_2 = p_2.tolist()
    leftovers = copy.deepcopy(p_1)
    c_1 = [0 for i in range(len(p_1))]
    c_2 = [0 for i in range(len(p_1))]
    direction = True

    while len(leftovers) != 0:
        if direction:
            starting_index = p_1.index(leftovers[0])
            c_1[starting_index] = p_1[starting_index]
            # print("child1 : ", c_1, ", removed item : ", c_1[starting_index])
            leftovers.remove(c_1[starting_index])
            next_index = p_1.index(p_2[starting_index])
        else:
            starting_index = p_2.index(leftovers[0])
            c_1[starting_index] = p_2[starting_index]
            # print("child1 : ", c_1, ", removed item : ", c_1[starting_index])
            leftovers.remove(c_1[starting_index])
            next_index = p_2.index(p_1[starting_index])

        while next_index != starting_index:
            if direction:
                c_1[next_index] = p_1[next_index]
                # print("child1 : ", c_1, ", removed item : ", c_1[next_index])
                leftovers.remove(c_1[next_index])
                next_index = p_1.index(p_2[next_index])
            else:
                c_1[next_index] = p_2[next_index]
                # print("child1 : ", c_1, ", removed item : ", c_1[next_index])
                leftovers.remove(c_1[next_index])
                next_index = p_2.index(p_1[next_index])

        direction = not direction
    leftovers = copy.deepcopy(p_2)
    direction = False
    while len(leftovers) != 0:
        if direction:
            starting_index = p_1.index(leftovers[0])
            c_2[starting_index] = p_1[starting_index]
            # print("child2 : ", c_2, ", removed item : ", c_2[starting_index])
            leftovers.remove(c_2[starting_index])
            next_index = p_1.index(p_2[starting_index])
        else:
            starting_index = p_2.index(leftovers[0])
            c_2[starting_index] = p_2[starting_index]
            # print("child2 : ", c_2, ", removed item : ", c_2[starting_index])
            leftovers.remove(c_2[starting_index])
            next_index = p_2.index(p_1[starting_index])

        while next_index != starting_index:
            if direction:
                c_2[next_index] = p_1[next_index]
                # print("child2 : ", c_2, ", removed item : ", c_2[next_index])
                leftovers.remove(c_2[next_index])
                next_index = p_1.index(p_2[next_index])
            else:
                c_2[next_index] = p_2[next_index]
                # print("child2 : ", c_2, ", removed item : ", c_2[next_index])
                leftovers.remove(c_2[next_index])
                next_index = p_2.index(p_1[next_index])

        direction = not direction
    # c_1 = np.array(c_1)
    # c_2 = np.array(c_2)
    return c_1, c_2


def roulette_wheel_selection(num_parents, popul, printmode=False):
    c = []
    for i in range(len(popul)):
        c.append(run_simulation(jobs_data, popul[i]))
    fitness = np.array(c)

    denominator = np.max(fitness) - np.min(fitness)
    if denominator == 0:
        denominator = 1
    p = abs(np.power((np.max(fitness) - fitness) / denominator, 3))
    p = p.tolist()
    if sum(p) < 0:
        print('warning!')
    print('Top %d Populations : ' % num_parents)
    parents = []
    makespan = []
    for i in range(num_parents):
        idx = random.choices(range(len(p)), weights=p)
        print(fitness[idx[0]], end=' ')
        if i % 10 == 9:
            print()
        parents.append(popul[idx[0]])
        makespan.append(fitness[idx[0]])

    if printmode:
        print('Probabilities : ')
        p = np.array(p)
        print(np.round(p, 2))

    return parents, makespan


def elite_selection(num_parents, popul):
    c = []
    for i in range(len(popul)):
        c.append(run_simulation(jobs_data, popul[i]))
    fitness = np.array(c)
    idx = np.argsort(fitness)
    print('Top %d Populations : ' % num_parents)
    parents = []
    makespan = []
    for i in range(num_parents):
        print(fitness[idx[i]], end=' ')
        if i % 20 == 19:
            print()
        parents.append(popul[idx[i]])
        makespan.append(fitness[idx[i]])

    return parents, makespan


def modify_population_parameters(num_popul, n_family):  # 500, 10
    num_parents = n_family * 2  # 20
    num_child_per_family = num_popul / n_family  # 50
    num_reproduce = num_child_per_family / 2  # 25
    return int(num_parents), int(num_reproduce)


# N_PARENTS, N_REPRODUCE = modify_population_parameters(NUM_POPULATION, 10)
N_PARENTS, N_REPRODUCE = modify_population_parameters(NUM_POPULATION, 50)


# 50 family, 100 parents, 10 chiled, 5 reproduce

def evaluate(popul):  # population = 2D list -
    # c = []
    # for i in range(len(popul)):
    #     c.append(run_simulation(jobs_data, popul[i]))
    # fitness = np.array(c)

    if random.random() < 0.9:
        parents, makespan = elite_selection(N_PARENTS, popul)
        # parents, makespan = roulette_wheel_selection(N_PARENTS, popul, False)
    else:
        parents, makespan = elite_selection(N_PARENTS, popul)
        # parents, makespan = roulette_wheel_selection(N_PARENTS, popul, True)
    # parents, makespan = elite_selection(N_PARENTS, popul)

    return parents, makespan


def reproduce(parents):
    # Cycle Crossover
    new_population = []

    for i in range(10):

        p1 = parents[2 * i]
        p2 = parents[2 * i + 1]
        # print('P1 : ', p1)
        # print('P2 : ', p2)

        for j in range(N_REPRODUCE):  # n_reproduce = 25
            c1, c2 = PMX_crossover(p1, p2)
            # c1, c2 = crossover(p1, p2, 2)
            # if i % 10 == 1 & j % 25 == 1:
            #     print("P1 : ", p1)
            #     print("P2 : ", p2)
            #     print("C1 : ", c1)
            #     print("C2 : ", c2)
            # c1, c2 = cycle_crossover(p1, p2)
            # print('Child %d of fitness %f was born!' % ((20 * i + 2 * j + 0) , run_simulation(jobs_data, c1)))
            # print('Child %d of fitness %f was born!' % ((20 * i + 2 * j + 1) , run_simulation(jobs_data, c2)))

            if random.random() < P_MUTATION:
                # c1 = c1.tolist()
                a = random.randint(0, N_OPERATION)
                b = random.randint(0, N_OPERATION)
                while abs(a - b) < 2:
                    a = random.randint(0, N_OPERATION)
                left = min(a, b)
                right = max(a, b)
                slice = c1[left:right]
                random.shuffle(slice)
                c1 = c1[:left] + slice + c1[right:]
                # c1 = np.array(c1)
                # print("Oops! Mutation occurred. Child %d is now of fitness %f" % ((20 * i + 2 * j + 0), run_simulation(jobs_data, c1)))

            new_population.append(c1)
            new_population.append(c2)

    return new_population


def visualize_gantt_chart(popul):
    opt_schedule, opt_makespan = elite_selection(1, popul)
    env = simpy.Environment()
    scheduler = Scheduler(env, jobs_data, NUM_MACHINE, opt_schedule[0])  # sequence = list
    scheduler.schedule()
    env.process(scheduler.evaluate())
    env.run()

    data = defaultdict(list)
    print()
    for i in range(len(scheduler.machine_list)):
        print('M%d ' % i, scheduler.machine_list[i].workingtime_log)
        for j in scheduler.machine_list[i].workingtime_log:
            temp = {'Machine': i, 'Job': j[0],
                    'Start': j[1],
                    'Finish': j[2]}
            for k, v in temp.items():
                data[k].append(v)

    data = pd.DataFrame(data)

    data['delta'] = data['Finish'] - data['Start']
    fig = px.timeline(data, x_start="Start", x_end="Finish", y="Machine", color="Job")
    fig.update_yaxes(autorange="reversed")  # otherwise tasks are listed from the bottom up
    fig.layout.xaxis.type = 'linear'
    fig.data[0].x = data.delta.tolist()

    fig.show()

    del env, scheduler
    return data


POP = initialize_population()

TERMINATION = 500

convergence = []
for i in range(TERMINATION):
    print('-'*15,'GENERATION %d' % i, '-'*15)
    parents, makespan = evaluate(POP)
    convergence.append(makespan)
    POP = reproduce(parents)

plt.figure()
for i in range(TERMINATION):
    for j in range(5):
        plt.scatter(i, convergence[i][j], c='red', s=2, alpha=0.1)

plt.title('FT10, N_POPULATION=%d, N_PARENTS=%d, GENERATION=%d' % (NUM_POPULATION, N_PARENTS, TERMINATION))
plt.show()

for i in range(3):
    show_optimum_result(parents)

path = os.getcwd()

filepath = './result%s.txt' % str(random.randint(1, 1000))

with open(filepath, 'wb') as fp:
    pickle.dump(POP, fp)

result = pd.DataFrame(POP)
filename = "./result%s.csv" % str(random.randint(1, 100))
result.to_csv(filename, sep=',', header=None, index=None)

print('File saved as ' + filename)
