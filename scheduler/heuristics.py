
def select_zero():
    # print('Enter index of operation : ')
    # id = int(input())  # 수동으로 job 번호 입력
    print("Let's choose index 0.")
    return 0

def select_manual(ready_task_set):
    num = len(ready_task_set)
    print('Enter number up to',num)
    id = int(input())  # 수동으로 job 번호 입력
    return id

def select_longest(ready_task_set):
    duration = []
    for o in ready_task_set:
        duration.append(o.duration)

    idx = duration.index(max(duration))
    return idx


def select_shortest(ready_task_set):
    duration = []
    for o in ready_task_set:
        duration.append(o.duration)

    idx = duration.index(min(duration))
    return idx