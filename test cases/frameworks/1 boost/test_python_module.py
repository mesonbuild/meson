import sys
sys.path.append(sys.argv[1])

# import compiled python module depending on version of python we are running with
if sys.version_info[0] == 2:
    import python2_module as pm

if sys.version_info[0] == 3:
    import python3_module as pm


def run():
    msg = 'howdy'
    w = pm.World()
    w.set(msg)

    assert(msg == w.greet())
    version_string = str(sys.version_info[0]) + "." + str(sys.version_info[1])
    assert(version_string == w.version())

if __name__ == '__main__':
    run()
