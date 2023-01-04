import sched
import time

import functions

s = sched.scheduler(time.time, time.sleep)
s.enter(60, 1, functions.check_tasks, (s,))
s.run()
