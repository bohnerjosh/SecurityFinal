# Python3 implementation of Min Heap

import sys
from datetime import datetime
from bnp.diary import Entry
import time

class MinHeap:

    def __init__(self, maxsize):
        self.capacity = maxsize
        self.size = 0
        self.Heap = []
        self.clear()

    def clear(self):
        for i in range(self.capacity):
            d = datetime(2021, 10, 5, 18, 00)
            e = Entry(1, "a", d)
            self.Heap.append(e)

    def heapsort_bottom(self, index):
        parent_node = (index - 1) // 2
        print(parent_node)
        if parent_node < 0:
            parent_node = 0

        if self.Heap[parent_node].date > self.Heap[index].date:
            temp = self.Heap[parent_node]
            self.Heap[parent_node] = self.Heap[index]
            self.Heap[index] = temp

            self.heapsort_bottom(parent_node)

    def heapsort_top(self, parent_node):
        left = (parent_node * 2) + 1
        right = (parent_node * 2) + 2
        _min = 0
        temp = ""

        # check for balance
        if left >= self.size or left < 0:
            left = -1

        if right >= self.size or right < 0:
            right = -1

        # if not balanced, min is set
        if left != -1 and self.Heap[left].date < self.Heap[parent_node].date:
            _min = left

        else:
            _min = parent_node

        if right != -1 and self.Heap[right].date < self.Heap[_min].date:
            _min = right

        # recursive check for balance and sort
        if _min != parent_node:
            temp = self.Heap[_min]
            self.Heap[_min] = self.Heap[parent_node]
            self.Heap[parent_node] = temp

            self.heapsort_top(_min)

    def getMin(self):
        if self.size == 0:
            return
        
        pop = self.Heap[0]
        self.Heap[0] = self.Heap[self.size-1]
        self.size -= 1

        self.heapsort_top(0)
        return pop

    def insert(self, data):
        if self.size < self.capacity:
            self.Heap[self.size] = data
            self.heapsort_bottom(self.size)
            self.size += 1
