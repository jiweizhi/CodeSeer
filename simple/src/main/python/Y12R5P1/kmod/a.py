


def _main():
    def cmp(idx1, idx2):
        # print idx1, idx2, p, l
        # print p[idx1] * l[idx2], p[idx2] * l[idx1]
        if p[idx1] * l[idx2] > p[idx2] * l[idx1]:
            return -1
        if p[idx1] * l[idx2] < p[idx2] * l[idx1]:
            return 1
        return idx1 - idx2

    f = open("test_files/Y12R5P1/A.in")

    t = int(f.readline())
    for _t in xrange(t):
        n = int(f.readline())

        l = map(int, f.readline().split())
        p = map(int, f.readline().split())

        assert len(l) == n
        assert len(p) == n
        idx = range(n)
        idx.sort(cmp=cmp)
        print "Case #%d:" % (_t+1),
        for _i, ix in enumerate(idx):
            if _i != n-1:
                print ix,
            else:
                print ix
    f.close()

if __name__ == "__main__":
    _main()
