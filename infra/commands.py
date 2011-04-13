from infra import clusto
import eventlet

from optparse import OptionParser

gpool = eventlet.GreenPool()

def list_pool(args):
    parser = OptionParser(usage='usage: %prog [options] <pools...>')
    parser.add_option('-k', '--key', dest='key', default=None)
    parser.add_option('-s', '--subkey', dest='subkey', default=None)
    options, args = parser.parse_args(args)

    if not args:
        parser.print_help()
        return -1

    if options.key is None and options.subkey is None:
        options.key = 'ip'
        options.subkey = 'ipstring'

    def get_contents(name):
        obj = clusto.get_by_name(name)
        return set(obj.contents())

    pools = list(gpool.imap(get_contents, args))
    first = pools[0]
    pools = pools[1:]

    def print_attrs(entity):
        kwargs = {}
        if options.key is not None:
            kwargs['key'] = options.key
        if options.subkey is not None:
            kwargs['subkey'] = options.subkey
        print ' '.join(entity.attr_values(**kwargs))

    for entity in first.intersection(*pools):
        gpool.spawn_n(print_attrs, entity)
        eventlet.sleep()
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


class AttrQuery(object):
    def __init__(self, obj):
        self.obj = obj

    def __call__(self, **kwargs):
        if 'csv' in kwargs:
            output_csv = kwargs['csv']
            del kwargs['csv']
        else:
            output_csv = False

        result = self.obj.attrs(**kwargs)
        result.sort(key=lambda x: (x['key'], x['number'], x['subkey'], x['value']))

        if output_csv:
            for x in result:
                attr = [x['key'], x['number'], x['subkey'], x['value']]
                for i, val in enumerate(attr):
                    if val == None:
                        attr[i] = ''
                    attr[i] = str(attr[i])
                print ','.join(attr)
        else:
            maxkey = 3 + max([len(str(x['key'])) for x in result] + [0])
            maxsubkey = 6 + max([len(str(x['subkey'])) for x in result] + [0])
            maxnumber = 3 + max([len(str(x['number'])) for x in result] + [0])

            if maxkey < 5: maxkey = 5
            if maxsubkey < 8: maxsubkey = 8
            if maxnumber < 5: maxnumber = 5

            print ''.join(['KEY'.ljust(maxkey, ' '), 'SUBKEY'.ljust(maxsubkey, ' '), 'NUM'.ljust(maxnumber, ' '), 'VALUE'])
            for attr in result:
                print ''.join([str(x).ljust(maxsize, ' ') for x, maxsize in [
                    (attr['key'], maxkey),
                    (attr['subkey'], maxsubkey),
                    (attr['number'], maxnumber),
                    (attr['value'], 0),
                ]])


def attr(args):
    parser = OptionParser(usage='%prog (add|set|delete|show) [options] <object>')
    parser.add_option('-k', '--key', dest='key', default=None)
    parser.add_option('-s', '--subkey', dest='subkey', default=None)
    parser.add_option('-v', '--value', dest='value', default=None)
    parser.add_option('-n', '--number', dest='number', default=None)
    parser.add_option('-m', '--merge', dest='merge_container_attrs', action='store_true', help='Merge attributes from this object\'s parent objects')
    parser.add_option('-c', '--csv', dest='csv', action='store_true', help='Output from the show action will be comma-delimited, rather than pretty')
    options, args = parser.parse_args(args)

    if len(args) < 2:
        parser.print_help()
        return -1

    action, obj = args[:2]

    try:
        obj = clusto.get(obj)
    except LookupError:
        sys.stderr.write('%s does not exist\n' % object)
        return -1
    obj = obj[0]

    actions = {
        'add':  obj.addattr,
        'set':  obj.setattr,
        'delete': obj.delattr,
        'del': obj.delattr,
        'show': AttrQuery(obj),
    }

    func = actions.get(action.lower(), None)
    if not func:
        sys.stderr.write('Unknown action: %s\n' % action)
        return -1

    if options.number:
        options.number = int(options.number)

    if isinstance(options.value, str) and options.value.isdigit():
        options.value = int(options.value)

    opts = dict([(k, v) for k, v in options.__dict__.items() if v != None])
    func(**opts)

