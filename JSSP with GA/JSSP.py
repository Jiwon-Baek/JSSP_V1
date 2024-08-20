import numpy as np
import simpy


jobs_data = [  # task = (machine_id, processing_time).
    [(0, 3), (1, 2), (2, 2)],  # Job0
    [(0, 2), (2, 1), (1, 4)],  # Job1
    [(1, 4), (2, 3)]  # Job2
]


class Job:
    def __init__(self, env, id, job_data):
        self.id = id
        print('Job ',id,' generated!')
        self.n = len(job_data)
        self.m = [job_data[i][0] for i in range(len(job_data))] # machine
        print('Job %d Machine list : ' % self.id, self.m)
        self.d = [job_data[i][1] for i in range(len(job_data))] # duration
        # self.o = [Operation(env, self.id, i, self.m[i],self.d[i]) for i in range(self.n)]
        self.o = [(self.id, i, self.m[i], self.d[i]) for i in range(self.n)]
        self.completed = 0
        self.scheduled = 0
        self.current_time = 0.0
        self.ETA = 0.0
        self.available = simpy.Resource(env, capacity=1)
        self.waiting_operations = [env.event() for i in range(self.n)]  # List to track waiting operations
        self.finished_operations = [env.event() for i in range(self.n)]

        self.execute()

    def execute(self):
        env.process(self.next_operation_ready())

    def next_operation_ready(self):
        for i in range(self.n):
            self.waiting_operations[i].succeed()
            # print('%d Operation %d%d is completed, waiting for Operation %d%d to be completed ...' % (env.now, self.id, self.completed, self.id, self.completed+1))
            yield self.finished_operations[i]
            # print('%d Operation %d%d Finished!' % (env.now, self.id, self.completed))
        print('%d Job %d All Operations Finished!' % (env.now, self.id))


#
# class Operation:
#     def __init__(self, env, job_id, op_id, machine, duration):
#         print('Operation %d%d generated!' % (job_id, op_id))
#         self.job_id = job_id
#         self.op_id = op_id
#         self.machine = machine
#         self.duration = duration
#         self.starting_time = 0.0
#         self.finishing_time = 0.0


class Machine:
    def __init__(self, env, id):
        print('Machine ',id,' generated!')
        self.id = id
        self.env = env
        self.machine = simpy.Resource(env, capacity=1)
        self.queue = simpy.Store(self.env)
        self.available_num = 0
        self.waiting_operations = {}
        self.availability = [env.event() for i in range(5)]
        self.availability[0].succeed()

        self.execute()

    def execute(self):
        env.process(self.processing())


    def processing(self):
        while True:
            job = yield self.queue.get()
            # print('%d : Job %d is waiting on M%d' % (env.now, job.id, self.id))

            yield self.availability[self.available_num]
            self.available_num += 1

            # print('M%d Usage Count : %d' %(self.id, self.available_num))

            yield job.waiting_operations[job.completed] # waiting이 succeed로 바뀔 떄까지 기다림
            yield self.env.timeout(job.d[job.completed])
            job.finished_operations[job.completed].succeed()
            print('%d Operation %d%d Finished on M%d!' % (env.now, job.id, job.completed, self.id))
            job.completed += 1
            self.availability[self.available_num].succeed()

sequence = [0, 0, 1, 2, 1, 2, 0, 1]

class Scheduler:
    def __init__(self, env, jobs_data, sequence):
        self.job_list = []
        self.machine_list = []

        for i in range(3):
            self.job_list.append(Job(env, i, jobs_data[i]))
            self.machine_list.append(Machine(env, i))

        self.sequence = sequence.copy()

    def schedule(self):
        for i in self.sequence:             # 0 0 1 2 1 2 0 1
            o_ = self.job_list[i].scheduled # 0 1 0 0 1 1 2 2
            m_ = self.job_list[i].m[o_]     # 0 1 0 1 2 2 2 1

            self.machine_list[m_].queue.put(self.job_list[i])
            self.job_list[i].scheduled += 1
            print('Operation %d%d scheduled on M%d!' % (i, o_, m_))

env = simpy.Environment()
scheduler = Scheduler(env, jobs_data, sequence)
scheduler.schedule()
env.run()

# Store에 Operation이 아닌 Job을 넣어서 문제가 생김
# Store에는 호출되는 순서가 훼손되지 않도록 절대 같은 객체를 넣지 말 것