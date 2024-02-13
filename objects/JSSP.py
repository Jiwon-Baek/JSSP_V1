
import simpy
import pandas as pd
from collections import defaultdict
from scheduler import heuristics
from GUI.GUI import GUI
from GUI.Gantt import Gantt
from globals.GlobalVariable import *


class Job:
    def __init__(self, env, id, job_data, machine_list):
        self.env = env
        self.id = id
        # print('Job ',id,' generated!')
        self.n = len(job_data)
        self.m = [job_data[i][0] for i in range(len(job_data))]  # machine
        # print('Job %d Machine list : ' % self.id, self.m)
        self.d = [job_data[i][1] for i in range(len(job_data))]  # duration
        self.o = [Operation(env, self.id, i, self.m[i], machine_list[self.m[i]], self.d[i]) for i in range(self.n)]
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
            if i != self.n-1:
                self.o[i+1].machine_obj.ready_task_set.append(self.o[i+1])
            # print('%d Operation %d%d Finished!' % (self.env.now, self.id, self.completed))
        # print('%d Job %d All Operations Finished!' % (self.env.now, self.id))
        self.finished.succeed()


class Operation:
    def __init__(self, env, job_id, op_id, machine, machine_obj, duration):
        # print('Operation %d%d generated!' % (job_id, op_id))
        self.env = env
        self.job_id = job_id
        self.op_id = op_id
        self.machine = machine
        self.machine_obj = machine_obj
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
        self.idle = True  # Initially set as True, changes to False when being used
        self.ready_task_set = []

        self.available_num = 0
        self.waiting_operations = {}
        # self.availability = [self.env.event() for i in range(100)]
        # self.availability[0].succeed()
        self.availability = self.env.event()
        self.availability.succeed()
        self.next_idle_time = 0
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
            self.idle = False
            starting_time = self.env.now
            op.starting_time = starting_time
            self.next_idle_time = self.env.now + op.duration

            yield self.env.timeout(op.duration)
            self.idle = True
            finishing_time = self.env.now
            op.finishing_time = finishing_time
            op.finished.succeed()
            self.workingtime_log.append((op.job_id, starting_time, finishing_time))
            # self.ready_task_set.remove(op) 완료된 순간이 아니라 schedule된 순간에 없어졌어야 함


            # print('(t=%d) Operation %d%d Finished on M%d!' % (self.env.now, op.job_id, op.op_id, self.id))
            # self.availability[self.available_num].succeed()
            self.availability.succeed()


class Scheduler:
    def __init__(self, env, jobs_data, num_machine, schedule_limit):
        # Sequence가 빠지고 대신 jobs_data만으로 생성됨
        self.env = env
        self.job_list = []
        self.machine_list = []
        self.c_max = 0
        self.schedule_time = []
        self.schedule_n = 0
        self.schedule_limit = schedule_limit

        self.time_dict = {}

        self.done = True

        for i in range(num_machine):
            self.machine_list.append(Machine(self.env, i))
        for i in range(len(jobs_data)):
            self.job_list.append(Job(self.env, i, jobs_data[i], self.machine_list))


        # initial_schedule
        self.initial_schedule()

    def initial_schedule(self):
        # 일단 각 작업들의 첫번째 op들을 machine의 ready_task_set에 추가
        for i in range(len(self.job_list)):
            # initial_op = self.job_list[i].o[0]
            # initial_m = self.job_list[i].m[0]
            self.machine_list[self.job_list[i].m[0]].ready_task_set.append(self.job_list[i].o[0])

        # put in the queue
        for m_ in range(len(self.machine_list)):
            if self.machine_list[m_].ready_task_set:  # 만약에 ready_task_set에 작업이 있으면 실행
                if len(self.machine_list[m_].ready_task_set) == 1:
                    o_idx = 0
                else:
                    o_idx = self.picker(self.machine_list[m_].ready_task_set)
                o_ = self.machine_list[m_].ready_task_set[o_idx]
                self.machine_list[m_].queue.put(o_); self.schedule_n += 1
                self.machine_list[m_].ready_task_set.remove(o_)
                self.job_list[o_.job_id].scheduled += 1
                # print(f'(t={self.env.now}) Operation %d%d scheduled on M%d!' % (o_.job_id, o_.op_id, m_))

                # 시간별로 종료 예정인 machine의 목록은 dictionary로 관리
                lookup_time = self.env.now + o_.duration
                if lookup_time not in self.schedule_time:
                    self.schedule_time.append(lookup_time)
                    self.time_dict[lookup_time] = [self.machine_list[m_]]
                else:
                    self.time_dict[lookup_time].append(self.machine_list[m_])
        # print('-'*30)
        # print('Initial Schedule Result : ')
        # print('Schedule time : ', self.schedule_time)
        # print('Machine Completion List')
        # print(self.time_dict)
        # print('-' * 30)

    def picker(self, ready_task_set):  # machine의 ready_task_set 중에
        idx = heuristics.select_zero()
        # idx = heuristics.select_longest(ready_task_set)
        # idx = heuristics.select_shortest(ready_task_set)
        # idx = heuristics.select_manual(ready_task_set)

        return idx

    def logger(self):
        log_option = False
        while log_option:
            print('-'*10,'Remaining...','-'*10)
            print(f"(t={self.env.now})")
            print(self.schedule_time)
            print('-' * 35)
            yield self.env.timeout(1)


    def schedule(self):

        while self.schedule_time:
            """
            Scheduling Time Control
            """
            t_target = min(self.schedule_time)
            t_delta = t_target - self.env.now
            self.schedule_time.remove(t_target)
            # closest time instance approaching
            yield self.env.timeout(t_delta)
            # print()
            print(f"(t={self.env.now}) Requires scheduling")

            # list of machines : self.time_dict[self.env.now]
            schedule_target_machines = [m.availability for m in self.time_dict[self.env.now]]
            yield simpy.AllOf(self.env, schedule_target_machines)
            # print("All Target Machines have turned idle. Now it's time to schedule.")

            """
            Scheduling
            """

            # Scheduling is for those machine who are idle at this time
            for m_, machine in enumerate(self.machine_list):
                if machine.idle:  # True or False
                    if machine.ready_task_set:  # 만약에 ready_task_set에 작업이 있으면 실행
                        if len(machine.ready_task_set) == 1:
                            """
                            만약 대기열에 가능한 작업이 하나뿐이라면 굳이 고를 필요가 없이 자동으로 배정
                            """
                            o_idx = 0
                        else:
                            o_idx = self.picker(machine.ready_task_set)
                        o_ = machine.ready_task_set[o_idx]
                        # put과 remove는 항상 함께 다니도록
                        machine.queue.put(o_); self.schedule_n += 1
                        machine.ready_task_set.remove(o_)
                        self.job_list[o_.job_id].scheduled += 1
                        # print(f'(t={self.env.now}) Operation %d%d scheduled on M%d!' % (o_.job_id, o_.op_id, m_))

                        if self.schedule_n >= self.schedule_limit:
                            """
                            하나씩 schedule operation 개수를 보며 관찰하고 싶은 경우에 중간에 stop 시키는 코드
                            만약 전부 schedule하고 싶으면 schedule_limit을 매우 큰 값으로 하면 됨
                            """
                            break

                        """
                        self.env.now가 아니라 예상되는 시작시점 기준으로 했어야 함
                        machine.next_idle_time
                        애초에 한번씩 다 훑으면 안되고 그냥 그 시점에 idle 한 기계들만 스케줄링 대상으로 했어야 함
                        => 아니 근데 한번씩 다 훑지 않으면 오랫동안 쉬었다가 이제 다시 작동하기 시작하는 경우에 탐지를 못함
                        => idle 여부가 빠져있어서 생겼던 문제인걸로...
                        """
                        lookup_time = self.env.now + o_.duration
                        # lookup_time = machine.next_idle_time + o_.duration
                        if lookup_time not in self.schedule_time:
                            self.schedule_time.append(lookup_time)
                            self.time_dict[lookup_time] = [machine]
                        else:
                            self.time_dict[lookup_time].append(machine)

                    if self.schedule_n >= self.schedule_limit:
                        break
                if self.schedule_n >= self.schedule_limit:
                    break
            if self.schedule_n >= self.schedule_limit:
                break


    def evaluate(self):
        """
        마지막으로 모든 job들에게 finished됐다는 신호를 받으면 Scheduler를 멈추고 self.env.now를 makespan으로 저장하고 출력
        :return: None
        """
        finished_jobs = [self.job_list[i].finished for i in range(len(self.job_list))]
        yield simpy.AllOf(self.env, finished_jobs)
        self.done = False
        self.c_max = self.env.now
        print("Total Makespan : ", self.c_max)


if __name__ == "__main__":
    env = simpy.Environment()
    scheduler = Scheduler(env, jobs_data, NUM_MACHINE, 100) # 맨 뒤의 숫자는 해당 개수만큼의 operation을 schedule 한다는 것을 의미
    env.process(scheduler.schedule())
    env.process(scheduler.logger())
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

    data['Delta'] = data['Finish'] - data['Start']
    gantt = Gantt(data, True, True)
    gui = GUI(gantt)


