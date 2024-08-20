import copy

import numpy as np
import plotly.offline
import simpy
import random

import plotly
import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd
from itertools import chain
from collections import defaultdict


from plotly.offline import init_notebook_mode, iplot
init_notebook_mode(connected=True)


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
P_MUTATION = 0.05

num_jobs = len(jobs_data)  # 10
num_operation = 0
for i in range(len(jobs_data)):
    num_operation += len(jobs_data[i])


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
        sequence = [i for i in range(num_operation)]
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


def run_simulation(jobs_data_, sequence_):
    # sequence_ = np.array(sequence_)
    # cumul = 0
    # for i in range(len(jobs_data)):
    #     for j in range(len(jobs_data[i])):
    #         sequence_ = np.where((sequence_ >= cumul) & (sequence_ < cumul + len(jobs_data[i])), i, sequence_)
    #     cumul += len(jobs_data[i])
    # sequence_ = sequence_.tolist()
    env = simpy.Environment()
    scheduler_ = Scheduler(env, jobs_data, NUM_MACHINE, sequence_)  # sequence = list
    scheduler_.schedule()
    env.process(scheduler_.evaluate())
    env.run()
    makespan = scheduler_.c_max
    del env, scheduler_
    return makespan


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
        if i % 10 == 9:
            print()
        parents.append(popul[idx[i]])
        makespan.append(fitness[idx[i]])

    return parents, makespan

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
            temp = {'Machine' : i, 'Job' : j[0],
                    'Start' : j[1],
                    'Finish' : j[2]}
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


data = pd.read_csv('result94.csv', header=None)
data = data.astype(int)
# data = data.transpose()
data = data.values.tolist()
print(data[0])

POP = data


# POP = [[0,0,1,2,1,2,0,1], [0,0,0,1,1,1,2,2],[0,0,1,1,2,2,0,1],[0,1,2,0,1,2,0,1]]

# plotly.offline.init_notebook_mode()
gantt = visualize_gantt_chart(POP)


