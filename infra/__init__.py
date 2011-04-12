import eventlet
eventlet.monkey_patch()

import clustohttp
clusto = clustohttp.ClustoProxy('http://clusto.simplegeo.com/api')

import infra.commands
import sys

commands = {
    'list-pool': infra.commands.list_pool,
    'info': infra.commands.info,
}

def main():
    if len(sys.argv) < 2:
        sys.stderr.write('Usage: %s <command>\n' % sys.argv[0])
        sys.stderr.write('  commands: %s\n' % ', '.join(commands.keys()))
        return -1

    func = commands.get(sys.argv[1], None)
    if func is None:
        sys.stderr.write('Unknown command %s\n' % sys.argv[1])
        return -1

    return func(sys.argv[2:])

if __name__ == '__main__':
    sys.exit(main())
