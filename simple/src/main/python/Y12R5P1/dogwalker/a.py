"""Google code jam 2012 round 3: problem A"""

# Always add higher probability of failure first

import unittest
import operator
import sys

def findFirstMax(pi, i):
    """Find lecographically first maximum element"""
    b = None
    for j in xrange(len(pi)):
        if pi[j] == None:
            continue
        if b == None:
            b = j
            continue
        if pi[j] > pi[b]:
            b = j
    return b

def solveIt(ti, pi):
    order = range(len(pi))
    for i in xrange(len(pi)):
        j = findFirstMax(pi, i)
        order[i] = j
        pi[j] = None
    return " ".join(map(lambda x: "%d" % x, order))

def solveProblems(filename):
    f = open(filename, "r")
    l = f.readlines()
    f.close()
    l = map(lambda x: x[:-1], l)
    numCases = int(l[0])
    l = l[1:]
    for i in xrange(numCases):
        print >> sys.stderr, "Computing case %d" % (i + 1)
        n = int(l[0])
        ti = map(int, l[1].split()[:n])
        pi = map(int, l[2].split()[:n])
        l = l[3:]
        print "Case #%d: %s" % ((i + 1),solveIt(ti, pi))
    f.close()


def _main():
    solveProblems("test_files/Y12R5P1/A.in")
 
if __name__ == "__main__":
    _main()

# In:  
# Out: 
