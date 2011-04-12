from infra import clusto
import eventlet

from optparse import OptionParser

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

def info(args):
    parser = OptionParser(usage='usage: %prog <name, ip, or mac>')
    options, args = parser.parse_args(args)

    if not args:
        parser.print_help()
        return -1

    obj = clusto.get(args[0])
    if not obj:
        log.error('No entity named %s' % args[0])
        return -1

    obj = obj[0]

    def format_line(key, value, pad=20):
        if isinstance(value, list):
            value = ', '.join(value)
            key += ':'
        print key.ljust(pad, ' '), value

    print 'Name:'.ljust(20, ' '), obj.name
    print 'Type:'.ljust(20, ' '), obj.type

    ip = obj.attr_values(key='ip', subkey='ipstring')
    if ip:
        format_line('IP', ip)
    parents = obj.parents()
    if parents:
        format_line('Parents', [x.name for x in parents])
    contents = obj.contents()
    if contents:
        format_line('Contents', [x.name for x in contents])

    print '\n',

    serial = obj.attr_values(key='system', subkey='serial')
    if serial:
        format_line('Serial', [x.rstrip('\r\n') for x in serial if x])
    memory = obj.attr_value(key='system', subkey='memory')
    if memory:
        format_line('Memory', '%i GB' % (memory / 1000))
    disk = obj.attr_value(key='system', subkey='disk')
    if disk:
        format_line('Disk', '%i GB (%i)' % (disk, len(obj.attrs(key='disk', subkey='size'))))
    cpucount = obj.attr_value(key='system', subkey='cpucount')
    if cpucount:
        format_line('CPU Cores', cpucount)
    desc = obj.attr_values(key='description')
    if desc:
        format_line('Description', '\n                    '.join(desc))

    ifaces = [('nic-eth(%i)' % x.number).ljust(20, ' ') + ' %s = %s' % (x.subkey, x.value) for x in obj.attrs(key='port-nic-eth') 
if x.subkey.find('mac') != -1]
    if ifaces:
        print '\n', '\n'.join(ifaces)
