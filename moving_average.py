""" moving average

from: https://github.com/kamyu104/LeetCode/blob/master/Python/moving-average-from-data-stream.py
"""

from collections import deque


class MovingAverage(object):

    def __init__(self, size):
        """
        Initialize your data structure here.
        :type size: int
        """
        self.__size = size
        self.__sum = 0
        self.__q = deque([])

    def next(self, val):
        """
        :type val: float
        :rtype: float
        """
        if len(self.__q) == self.__size:
            self.__sum -= self.__q.popleft()
        self.__sum += val
        self.__q.append(val)
        return 1.0 * self.__sum / len(self.__q)


"""
obj = MovingAverage(4)
while True:
    val = float(raw_input("enter value "))

    average = obj.next(val)
    print "average=", average
"""
