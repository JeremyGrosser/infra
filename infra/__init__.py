import eventlet
eventlet.monkey_patch()

from optparse import OptionParser
from pprint import pprint
import sys

import clustohttp

clusto = clustohttp.ClustoProxy('http://clusto.simplegeo.com/api')
gpool = eventlet.GreenPool()

def list_pool(args):
    parser = OptionParser(usage='usage: %prog [options] <pools...>')
    parser.add_option('-k', '--key', dest='key', default='ip')
    parser.add_option('-s', '--subkey', dest='subkey', default='ipstring')
    options, args = parser.parse_args(args)

    if not args:
        parser.print_help()
        return -1

    def get_contents(name):
        obj = clusto.get_by_name(name)
        return set(obj.contents())

    pools = list(gpool.imap(get_contents, args))
    first = pools[0]
    pools = pools[1:]

    def print_attrs(entity):
        print ' '.join(entity.attr_values(key=options.key, subkey=options.subkey))

    entities = first.intersection(*pools)
    [gpool.spawn_n(print_attrs, x) for x in entities]
    gpool.waitall()

commands = {
    'list-pool': list_pool,
}

def main():
    if len(sys.argv) < 2:
        sys.stderr.write('Usage: %s <command>\n' % sys.argv[0])
        return -1

    func = commands.get(sys.argv[1], None)
    return func(sys.argv[2:])

if __name__ == '__main__':
    sys.exit(main())
