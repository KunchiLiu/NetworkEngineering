
'the lcx of my homework'

_author_ = 'My Teacher'

import argparse # 命令解析包
import asyncio  #协程模块
import logging #日志模块

client_data = b'ABCDEFG'
server_data = b'1234567'

# python b4lcxt.py -b 127.0.0.1:8001 -l 8002 -s c -t 10
# 127.0.0.1:8001 8002 s 10

async def client_do_listen(bind_host, bind_port):
    sock_port = '-----'
    try:
        # 绑定R的监听地址，127.0.0.1:8001
        reader, writer = await asyncio.open_connection(bind_host, bind_port, loop=loop)
        # 连接成功后，可以获取二者通信所用端口号
        sock_host, sock_port, = writer.get_extra_info('sockname')
        log.info('S L R<C open {:5} > {:5}'.format(sock_port, bind_port))
        log.info('S L R<C data {:5} > {:5} {}'.format(sock_port, bind_port, client_data))
        #发送S <- L <- R <- C
        writer.write(client_data)
        #接收S ->L -> R -> C
        data = await reader.readexactly(len(server_data))
        if data != server_data:
            log.error('S L R>C data {:5} > {:5} {} error server_data {}'.format(sock_port, bind_port, data, server_data))
            writer.close()
            return

        log.info('S L R>C data {:5} > {:5} {}'.format(sock_port, bind_port, data))

        # 如果是c模式，则打印如下信息，表示R < C 传递的数据没有了，这个socket可以关闭
        if args.shut_mode == 'c':
            log.info('S L R<C shut {:5} > {:5}'.format(sock_port, bind_port))
            writer.close()
            return

        data = await reader.read(1) #读取一个字节，如果没有数据了，则R > C 的数据以read完毕。
        if not data:
            log.info('S L R>C shut {:5} < {:5}'.format(sock_port, bind_port))

    except Exception as e:
        log.info('S L R>C shut {:5} < {:5} exc {}'.format(sock_port, bind_port, e.args))


async def server_do_slave(reader, writer):
    peer_host, peer_port, = writer.get_extra_info('peername')  #the remote address to which the socket is connected
    sock_host, sock_port, = writer.get_extra_info('sockname')  #socket's own address
    log.info('S<L R C open {:5} < {:5}'.format(sock_port, peer_port))

    try:
        log.info('S>L R C data {:5} > {:5} {}'.format(sock_port, peer_port, server_data))
        writer.write(server_data)
        data = await reader.readexactly(len(client_data))
        if data != client_data:
            log.error('S<L R C data {:5} > {:5} {} error client_data {}'.format(sock_port, peer_port, data, client_data))
            writer.close()
            return

        log.info('S<L R C data {:5} > {:5} {}'.format(sock_port, peer_port, data))

        # 如果是c模式，则打印如下信息，表示S > L传递的数据没有了，这个socket可以关闭
        if args.shut_mode == 's':
            log.info('S>L R C shut {:5} > {:5}'.format(sock_port, peer_port))
            writer.close()
            return
        data = await reader.read(1)# 读取一个字节，如果没有数据了，则S < L 的数据以read完毕。
        if not data:
            log.info('S<L R C shut {:5} < {:5}'.format(sock_port, peer_port))

    except Exception as e:
        log.info('S<L R C shut {:5} < {:5} exc {}'.format(sock_port, peer_port, e.args))


# log_fmt = logging.Formatter('%(lineno)-3d %(levelname)7s %(funcName)-16s %(message)s')
# Formatter对象设置日志信息最后的规则、结构和内容，默认的时间格式为%Y-%m-%d %H:%M:%S，   %(levelno)s:数字形式的日志级别，%(levelname)s：文本形式的日志却别，%(message)s用户输出的消息
log_fmt = logging.Formatter('%(lineno)-3d %(levelname)7s %(message)s')
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.DEBUG)
log_handler.setFormatter(log_fmt)
log = logging.getLogger(__file__)
log.addHandler(log_handler)
log.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser(description='asyncio lcx test.')
parser.add_argument('-b', dest='bind_addr', required=True, help='Bind address in remote-listen')
parser.add_argument('-l', dest='server_port', required=True, type=int, help='Local-server port')
parser.add_argument('-s', dest='shut_mode', required=True, help='Shut mode, c:client s:server')
parser.add_argument('-t', dest='test_times', type=int, default=10, help='Times for remote-client connect remote-listen')

args = parser.parse_args()
log.info('='*77)

loop = asyncio.get_event_loop()

coro = asyncio.start_server(server_do_slave, '0.0.0.0', args.server_port, loop=loop)
server = loop.run_until_complete(coro)
log.info('S:L R C bind {:5}'.format(args.server_port))

bind_host, bind_port = args.bind_addr.split(':', 1)

# task_list = []
# for t in range(args.test_times):
#     task = loop.create_task(client_do_listen(bind_host, bind_port))
#     task_list.append(task)

# loop.run_until_complete(asyncio.wait([client_do_listen(bind_host, bind_port) for i in range(args.test_times)]))

loop.run_until_complete(asyncio.gather(*[client_do_listen(bind_host, bind_port) for i in range(args.test_times)]))

log.info('all test over')

try:
    loop.run_forever()
except KeyboardInterrupt:
    pass
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
