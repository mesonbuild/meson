import dependencies
import mlog

import platform

try:
    import dnf
    import dnf.util
    DNF = True
except ImportError:
    DNF = False

def try_install(t, s):
    """Tries to install given dependency via package managers

    Args:
        t (type): type of dependency
        s (str): path or name of dependency

    Returns:
        bool: True if successful, False otherwise
    """
    if DNF:
        if not dnf.util.am_i_root():
            mlog.debug("Can't install because not root")
            return False
        b = dnf.Base()
        b.read_all_repos()
        b.fill_sack()
        q = b.sack.query()
        if t == dependencies.PkgConfigDependency:
            prov_str = "pkgconfig({})"
        else:
            mlog.debug("DNF can't handle this type of dependency")
            return False
        ret = q.available().filter(
            provides=prov_str.format(s),
            arch=platform.machine()).run()
        if len(ret) == 0:
            mlog.debug("Nothing to install")
            return False
        else:
            print(ret)
            return
            b.package_install(ret[0])
            if b.resolve():
                b.download_packages(b.transaction.install_set)
                b.do_transaction()
            return True
    else:
        return False
