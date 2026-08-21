import sys
sys.path.append(sys.argv[1])
import python3_module


def run():
    msg = 'howdy'
    w = python3_module.World()

    w.set(msg)

    assert msg == w.greet()
    version_string = str(sys.version_info[0]) + "." + str(sys.version_info[1])
    assert version_string == w.version()

if __name__ == '__main__':
    run()
