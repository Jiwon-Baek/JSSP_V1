import numpy as np
import simpy
import random


jobs_data = [  # task = (machine_id, processing_time).
    [(0, 3), (1, 2), (2, 2), (3, 2), (4, 4)],  # Job0
    [(1, 2), (2, 1), (3, 4), (4, 1), (5, 2)],  # Job1
    [(2, 4), (3, 3), (4, 2), (5, 4), (0, 2)],  # Job2
    [(3, 2), (4, 1), (5, 4), (0, 1), (1, 2)],  # Job3
    [(4, 2), (5, 1), (0, 4), (1, 1), (2, 2)],  # Job4
    [(5, 4), (0, 3), (1, 2), (2, 4), (3, 2)],  # Job5
    [(0, 2), (1, 1), (2, 4), (3, 1), (4, 2)],  # Job6
    [(1, 2), (2, 1), (3, 4), (4, 1), (5, 2)],  # Job7
]


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

        self.sequence = sequence.copy()

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

        if result[i][1]==min(makespan):
            print(result[i][0], 'makespan of ', result[i][1])
            optimal.append(result[i][0])

    return optimal




optimal = [[2, 5, 3, 7, 2, 6, 0, 7, 3, 4, 7, 1, 6, 2, 3, 0, 4, 5, 5, 1, 0, 3, 2, 0, 6, 5, 4, 0, 1, 7, 3, 7, 2, 5, 1, 4, 4, 1, 6, 6],
[5, 4, 2, 6, 3, 0, 4, 7, 6, 1, 5, 7, 3, 2, 3, 7, 6, 2, 1, 7, 1, 5, 7, 3, 0, 0, 6, 4, 2, 3, 4, 1, 1, 0, 6, 0, 5, 2, 4, 5],
[3, 3, 7, 2, 1, 5, 6, 4, 3, 0, 2, 4, 5, 6, 2, 0, 4, 3, 2, 1, 1, 5, 1, 7, 7, 6, 0, 7, 5, 4, 7, 1, 6, 4, 2, 0, 3, 5, 6, 0]]




# optimize_makespan()

def show_optimum_result(optimal):
    for sequence in optimal:
        print('-'*40)
        print('Sequence : ', sequence)

        env = simpy.Environment()
        scheduler = Scheduler(env, jobs_data, 6, sequence)
        scheduler.schedule()
        env.process(scheduler.evaluate())
        env.run()
        for i in range(len(scheduler.machine_list)):
            print('M%d ' % i, scheduler.machine_list[i].workingtime_log)

show_optimum_result(optimal)



"""
----------------------------------------
Sequence :  [2, 5, 3, 7, 2, 6, 0, 7, 3, 4, 7, 1, 6, 2, 3, 0, 4, 5, 5, 1, 0, 3, 2, 0, 6, 5, 4, 0, 1, 7, 3, 7, 2, 5, 1, 4, 4, 1, 6, 6]
M0  [(6, 0, 2), (0, 2, 5), (5, 5, 8), (3, 8, 9), (4, 9, 13), (2, 13, 15)]
M1  [(7, 0, 2), (1, 2, 4), (6, 4, 5), (0, 5, 7), (5, 8, 10), (3, 10, 12), (4, 13, 14)]
M2  [(2, 0, 4), (7, 4, 5), (1, 5, 6), (0, 7, 9), (6, 9, 13), (5, 13, 17), (4, 17, 19)]
M3  [(3, 0, 2), (2, 4, 7), (7, 7, 11), (0, 11, 13), (1, 13, 17), (5, 17, 19), (6, 19, 20)]
M4  [(3, 2, 3), (4, 3, 5), (2, 7, 9), (0, 13, 17), (7, 17, 18), (1, 18, 19), (6, 20, 22)]
M5  [(5, 0, 4), (3, 4, 8), (4, 8, 9), (2, 9, 13), (7, 18, 20), (1, 20, 22)]
----------------------------------------
Sequence :  [5, 4, 2, 6, 3, 0, 4, 7, 6, 1, 5, 7, 3, 2, 3, 7, 6, 2, 1, 7, 1, 5, 7, 3, 0, 0, 6, 4, 2, 3, 4, 1, 1, 0, 6, 0, 5, 2, 4, 5]
M0  [(6, 0, 2), (0, 2, 5), (5, 5, 8), (3, 9, 10), (4, 10, 14), (2, 18, 20)]
M1  [(7, 0, 2), (6, 2, 3), (1, 3, 5), (5, 8, 10), (0, 10, 12), (3, 12, 14), (4, 14, 15)]
M2  [(2, 0, 4), (7, 4, 5), (6, 5, 9), (1, 9, 10), (0, 12, 14), (5, 14, 18), (4, 18, 20)]
M3  [(3, 0, 2), (2, 4, 7), (7, 7, 11), (1, 11, 15), (6, 15, 16), (0, 16, 18), (5, 18, 20)]
M4  [(4, 0, 2), (3, 2, 3), (2, 7, 9), (7, 11, 12), (1, 15, 16), (6, 16, 18), (0, 18, 22)]
M5  [(5, 0, 4), (4, 4, 5), (3, 5, 9), (7, 12, 14), (2, 14, 18), (1, 18, 20)]
----------------------------------------
Sequence :  [3, 3, 7, 2, 1, 5, 6, 4, 3, 0, 2, 4, 5, 6, 2, 0, 4, 3, 2, 1, 1, 5, 1, 7, 7, 6, 0, 7, 5, 4, 7, 1, 6, 4, 2, 0, 3, 5, 6, 0]
M0  [(6, 0, 2), (0, 2, 5), (5, 5, 8), (4, 9, 13), (3, 13, 14), (2, 14, 16)]
M1  [(7, 0, 2), (1, 2, 4), (6, 4, 5), (0, 5, 7), (5, 8, 10), (4, 13, 14), (3, 14, 16)]
M2  [(2, 0, 4), (1, 4, 5), (7, 5, 6), (6, 6, 10), (0, 10, 12), (5, 12, 16), (4, 16, 18)]
M3  [(3, 0, 2), (2, 4, 7), (1, 7, 11), (7, 11, 15), (6, 15, 16), (0, 16, 18), (5, 18, 20)]
M4  [(3, 2, 3), (4, 3, 5), (2, 7, 9), (1, 11, 12), (7, 15, 16), (6, 16, 18), (0, 18, 22)]
M5  [(5, 0, 4), (3, 4, 8), (4, 8, 9), (2, 9, 13), (7, 16, 18), (1, 18, 20)]

"""