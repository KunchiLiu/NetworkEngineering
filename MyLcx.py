#!/user/bin/env python3
# -*- coding: utf-8 -*-

'the lcx of my homework'

_author_ = 'Kunchi Liu'

import argparse
import sys
import asyncio
import random
import string
import hashlib
import struct
from queue import Queue

# Message Length |  Command  | Salt Length | Salt | Username Length | Username | Hash Length | Hash | Result | RequestID
#      h         |    b      |      b      |  Var |         b       |     Var  |      b      |  Var |    b   |     h
# ConnectionID   | ListenPort | Data Length | Data |
#      h         |    h       |     h       | Var  |

# c 表示Command 1：chap-salt 2：chap-hash 3:chap-result 4：bind-request 5：bind-reponse
# c 表示Command 6：connect-request 7：connect-response 8：data 9：disconnect
# ！网络字节序=big-endian
RequestID=0
ConnectionID=0
L_Rconnection=dict() # 注：cid:address   Slave 模式下存Local Slave 与 Local Server建立的连接  | Listen模式下存Remote Client 与 Remote Listen建立的连接
ClientReader=[]  # Remote Listen reader
ClientWriter=[]  # Remote Listen writer
ServerReader=[]
ServerWriter=[]
ConnectionidQueue = Queue()  # 仅在 Listen 模式下，

def PackChapsalt(salt):
    c=1
    sl=len(salt)
    ml = 4 + sl
    packet=struct.pack("!hbb"+str(sl)+"s",ml,c,sl,salt.encode())
    return packet
def PackChaphash(username,hash):
    ul=len(username)
    hl=len(hash)
    ml=5+ul+hl
    c=2
    packet = struct.pack("!hbb" + str(ul) + "sb"+str(hl)+"s", ml, c, ul,username.encode(),hl,hash.encode())
    return packet
def PackChapresult(result):
    ml=4
    c=3
    packet = struct.pack("!hbb", ml, c, result)
    return packet
def PackBindrequest(reid,lport):
    ml=7
    c=4
    packet = struct.pack("!hbhh", ml, c,reid,lport)
    return packet
def PackBindresponse(reid,result,lport):
    ml=8
    c=5
    packet = struct.pack("!hbhbh", ml, c,reid,result,lport)
    return packet
def PackConnectrequest(reid,lport):
    ml=7
    c=6
    packet = struct.pack("!hbhh", ml, c,reid,lport)
    return packet
def PackConnectresponse(reid,result,coid):
    ml=8
    c=7
    packet = struct.pack("!hbhbh", ml, c,reid,result,coid)
    return packet
def PackData(coid,data):
    c=8
    dl=len(data)
    ml=7+dl
    packet = struct.pack("!hbhh"+str(dl)+"s", ml,c,coid,dl,data.encode())
    return packet
def PackDisconnect(coid):
    ml=5
    c=9
    packet = struct.pack("!hbh", ml, c, coid)
    return packet
def UnpackChapsalt(ml,message):
    sl,salt=struct.unpack("!b"+str(ml-4)+"s",message)
    return salt
def UnpackChaphash(ml,message):
    ul,other=struct.unpack("!b"+str(ml-4)+"s",message)
    un=other[:ul]
    h=other[ul+1:]
    return un,h
def UnpackChapresult(message):
    result=struct.unpack("!b",message)
    return result
def UnpackBindrequest(message):
    rid,lport=struct.unpack("!hh",message)
    return rid,lport
def UnpackBindresponse(message):
    rid,res,lport = struct.unpack("!hbh", message)
    return rid,res,lport
def UnpackConnectrequest(message):
    rid, lport = struct.unpack("!hh", message)
    return rid, lport
def UnpackConnectresponse(message):
    rid, res, cid = struct.unpack("!hbh", message)
    return rid, res, cid
def UnpackData(ml,message):
    cid,dl,data=struct.unpack("!hh"+str(ml-7)+"s", message)
    return cid,data
def UnpackDisconnect(message):
    cid= struct.unpack("!h", message)
    return cid

# 打印异常类
class printException(Exception):
    pass

async def server_handler(reader,writer,cid):
    while True:
        data = await reader.read(100)
        if not data:
            print("S<L R C data : Local Server do not received data and the connect ID is %d from Remote Listen" % (cid))
            break
        packet = PackData(cid, data.decode())
        print("S<L R C data : Local Server received data %s and the connect ID is %d from Remote Listen" % (data.decode(),cid))
        slave.write(packet)
        print("S>L R C data : Local Server received data %s and the connect ID is %d from Remote Listen" % (data.decode(), cid))
    packet = PackDisconnect(cid)
    writer.close()
    print("S<>L R C disconnect : the disconnect ID is %d" % (cid))
    slave.write(packet)
    ServerWriter.remove(writer)
    ServerReader.remove(reader)

async def tcpslave(user,ip1,porta,ip2,loop):
    # Local slave chap认证，此函数里的reader、writer是Local Slave 连接 Remote listen产生
    # connectionid由Local Slave生成,用于后续双向数据流的标识
    global RequestID,ConnectionID,slave,listen,ServerReader,ServerWriter,L_Rconnection
    # [ip1 127.0.0.1,8000]
    ip=ip1[0]
    port=int(ip1[1])
    usermes=user.split(':',2)
    username=usermes[0]   # u1
    password=usermes[1]   # p1
    # Local Slave 连接 Remote Listen 127.0.0.1：8000
    reader, writer = await asyncio.open_connection(ip,port,loop=loop)
    print('S L>R C open : Succeed ')
    slave=writer
    listen=reader
    print('S L<R C chap_salt : begin ')
    message = await reader.readexactly(3)
    ml, c = struct.unpack("!hb", message)
    if c != 1:
        raise printException('Local Slave do not receive chapsalt')
    message = await reader.readexactly(ml-3)
    UnpackChapsalt(ml,message)
    salt=UnpackChapsalt(ml,message)
    print('S L<R C chap_salt : receive salt ')
    m = hashlib.md5()
    pas=password.encode()
    str = salt+pas
    m.update(str)
    md5=m.hexdigest()
    packet=PackChaphash(username,md5)
    writer.write(packet)
    print('S L>R C chap_hash : send hash ')
    await writer.drain()
    message = await reader.readexactly(4)
    ml, c ,result= struct.unpack("!hbb", message)
    if c != 3:
        raise printException("Local Slave do not receive chapresult")
    if result==1:
        print("S L<R C chap_result : receive result")
        print("S L<>R C chap_result : chap authentication succeed")
        # reid S L>R C bind_requestid
        reid =RequestID
        RequestID=RequestID+1
        packet=PackBindrequest(reid,int(porta)) # porta = 8001
        writer.write(packet)
        await writer.drain()
        print("S L>R C bind_request : send request")
        message = await reader.readexactly(3)
        ml, c = struct.unpack("!hb", message)
        if c != 5:
            raise printException('Local Slave do not receive bindresponse')
        message = await reader.readexactly(5)
        revrid, result, lport = UnpackBindresponse(message)
        if revrid==reid and result==1:
            # ip2 [127.0.0.1,8001]
            print("S L<R C bind_response : received response")
            print("S L<>R C bind : bind succeed")
            serveraddress = ip2[0]
            serverport = int(ip2[1])
            while True:
                message = await reader.readexactly(3)
                ml, c = struct.unpack("!hb", message)
                if c == 6:  # connectrequest
                    message = await reader.readexactly(4)
                    # 此处 rrid = 递增 lport = 8001 rrid = reid
                    rrid,lport=UnpackConnectrequest(message)
                    print("S L<R C connect_request : received request")
                    try:
                        # Local Slave 产生 connection id ,connecttionid 从0递增
                        cid=ConnectionID
                        ConnectionID=ConnectionID+1
                        packet=PackConnectresponse(rrid,1,cid)
                        writer.write(packet)
                        await writer.drain()
                        # Local Slave 连接 Local Server
                        reader2, writer2 = await asyncio.open_connection(serveraddress, serverport, loop=loop)
                        addr = writer2.get_extra_info("peername") # addr = 127.0.0.1：8002
                        print("S<L R C link_S_port : ",addr)
                        print("S L>R C connect_response : send response")
                        # connection 字典存储 cid ： addr
                        L_Rconnection[cid] = addr
                        ServerReader.append(reader2)
                        ServerWriter.append(writer2)
                        asyncio.ensure_future(server_handler(reader2,writer2,cid))
                    except:
                        packet = PackConnectresponse(rrid, 0, rrid)
                        writer.write(packet)
                        await writer.drain()
                        print("S L>R C connect_response : send response_failed")
                elif  c==9:  # disconnect 找到cid对应的serverwriter并关闭
                        message = await reader.readexactly(2)
                        cid=UnpackDisconnect(message)[0]
                        for server in ServerWriter:
                            if server.get_extra_info('peername') == L_Rconnection[cid]:
                                server.close()
                                print("S<>L R C disconnect : the disconnect ID is %d" % (cid))
                                break
                elif  c==8:   #data
                        message = await reader.readexactly(ml-3)
                        cid,data=UnpackData(ml,message)
                        print("S L<R C data : Local Slave received data %s and the connect ID is %d from Remote Listen" % (data.decode(), cid))
                        dflag=1
                        while dflag:
                            await asyncio.sleep(0.01)
                            if len(L_Rconnection)>cid:
                                    for server in ServerWriter:
                                        if server.get_extra_info('peername') == L_Rconnection[cid]:
                                            server.write(data)
                                            print("S<L R C data : Local Slave send data %s and the connect ID is %d to Local Server"
                                                  % (data.decode(), cid))
                                            # await server.drain()
                                            dflag=0
                                            break
                else:  # 没有data
                        message = await reader.readexactly(ml - 3)
                        print("S L<>R C disconnect : the disconnect ID is %d" % (cid))
                        packet=PackDisconnect(cid)
                        writer.write(packet)
    else:
        print("S L<>R C connect_failed : Local Slave and Remote Listen link failed")
    loop.stop()
async def RemoteClient_handle(reader, writer):
    # 提供Remote Client 连接 Remote Listen = 127.0.0.1：8001
    global ClientReader,ClientWriter,L_Rconnection
    ClientReader.append(reader)
    ClientWriter.append(writer)
    addr=writer.get_extra_info('peername')  # Remote Client 的sockname
    # Remote Listen 向 Local Slave 发送 Connect Req
    # 第一个rid是0 lport = 8001
    packet = PackConnectrequest(rid, lport)
    # 此处slave是Remote Listen 与 Local Slave 通信所用
    slave.write(packet)
    print("S L R<C link_R_port : requestID %d and listenport %d"%(rid,lport))
    print("S L<R C cennect_request : send requestID %d and listenport %d" % (rid, lport))
    while True:
        await asyncio.sleep(0.1)
        if len(L_Rconnection)<=ConnectionID:
            cid=ConnectionidQueue.get()
            L_Rconnection[cid] = addr
            break
    while True:
        data=await reader.read(100)
        if not data:
            break
        print("S L R<C data : Remote Listen received data %s and the connect ID is %d" % (data.decode(),cid))
        packet = PackData(cid, data.decode())
        print("S L<R C data : Remote Listen send data %s and the connect ID is %d to Local Slave" % (data.decode(), cid))
        slave.write(packet)
    packet=PackDisconnect(cid)
    writer.close()
    print("S L R<>C disconnect : the disconnect ID is %d" % (cid))
    slave.write(packet)
    ClientWriter.remove(writer)
    ClientReader.remove(reader)

async def tcpRemoteListen(reader, writer):
    # rid S L R<C 连接请求id
    # 当 S L>R C  连接时，R产生一对reader和writer和L通信，转给slave和listen
    global listen,slave,lport,rid,ConnectionID,L_Rconnection,ConnectionidQueue
    listen = reader
    slave = writer
    salt = ''.join(random.sample(string.ascii_letters + string.digits, 15))
    packet=PackChapsalt(salt)
    writer.write(packet)
    await writer.drain()
    print("S L<R C chap_salt : send salt")
    message = await reader.readexactly(3)
    ml,c=struct.unpack("!hb",message)
    if c!=2:
        raise printException("Remote Listen do not receive chaphash")
    message = await reader.readexactly(ml-3)
    username,rmd5= UnpackChaphash(ml,message)
    print("S L>R C chap_salt : received salt")
    for user in users:
        un = user.split(':')
        if username.decode() == un[0]:
            password = un[1]
        else:
            print("S L<>R C chap_result : chap authentication failed")
            break
    m = hashlib.md5()
    pas = password.encode()
    str = salt.encode() + pas
    m.update(str)
    md5 = m.hexdigest()
    if md5 == rmd5.decode():
        packet=PackChapresult(1)
        writer.write(packet)
        await  writer.drain()
        print("S L<R C chap_result : send result")
        print("S L<R C chap_result : authentication succeed")
        message = await reader.readexactly(3)
        ml, c = struct.unpack("!hb", message)
        if c != 4:
            raise printException('S L>R C bind_request : Remote Listen do not received bindrequest')
        message = await reader.readexactly(4)
        print('S L>R C bind_request : received bindrequest')
        rid,lport = UnpackBindrequest(message)
        if lport == "0":
            lport = random.randint(1, 65535)
        try:
            # Remote Listen 开启监听端口8001 等RemoteClient连接
            await asyncio.ensure_future(asyncio.start_server(RemoteClient_handle, '127.0.0.1', lport, loop=loop))
            result = 1
            packet = PackBindresponse(rid, result, lport)
            writer.write(packet)
            print("S L<R C bind_response : send response")
            print("S L<>R C bind : bind succeed")
            while True:
                message = await reader.readexactly(3)
                ml, c = struct.unpack("!hb", message)
                if c == 7: #connect response
                        message = await reader.readexactly(5)
                        rid, result, cid = UnpackConnectresponse(message)
                        print("S L>R C connect_response : received response from request ID is %d and connection ID is %d"%(rid,cid))
                        if result==0:
                            raise printException("S L>R C connect_response : Remote Listen do not received response")
                        # 连接成功，把cid放入ConnectionidQueue队列中
                        ConnectionidQueue.put(cid)
                        ConnectionID=cid
                elif c == 8:  # data
                    message = await reader.readexactly(ml - 3)
                    cid, data = UnpackData(ml, message)
                    dflag = 1
                    while dflag:
                        await asyncio.sleep(0.01)
                        if len(L_Rconnection) > cid:
                            for client in ClientWriter:
                                if client.get_extra_info('peername') == L_Rconnection[cid]:
                                    client.write(data)
                                    dflag = 0
                                    break
                elif c == 9: # disconnect
                        message = await reader.readexactly(2)
                        cid = UnpackDisconnect(message)[0]
                        for client in ClientWriter:
                            if client.get_extra_info('peername') == L_Rconnection[cid]:
                                client.close()
                                print("S L R<>C disconnect : the disconnect ID is %d" % (cid))
                else:
                    message = await reader.readexactly(ml - 3)
        except:
            print("Listen Port Failed!")
            result = 0
            packet = PackBindresponse(rid, result, lport)
            writer.write(packet)
            exit()
    else:
        packet = PackChapresult(0)
        writer.write(packet)
    loop.stop()

def main():
    parser = argparse.ArgumentParser(description='asyncio lcx.')
    parser.add_argument('-m', dest='mode', required=True, help='mode, slave or listen')
    parser.add_argument('-p', dest='port', required=True, type=int, help='RemoteListen port or Need it open port')
    parser.add_argument('-u', dest='user', required=True, help='user username:password')
    parser.add_argument('-r', dest='RL_address', required=True, help='RemoteListen listen address:port')
    parser.add_argument('-l', dest='LS_address', required=True, help='LocalServer listen address:port')
    print('=' * 77)
    if 'listen' in sys.argv:
            if '-p' in sys.argv:
                 index = sys.argv.index('-p')
                 try:
                    global users,port1,loop
                    # global tasks
                    port1 = int(sys.argv[index + 1])
                    allusers = str(sys.argv[index + 3])
                    users = allusers.split(',')
                    loop = asyncio.get_event_loop()
                    # asyncio.start_server（）会产生一对writer和reader，与所连接的客户端通信
                    # 开启Remote Listen 127.0.0.1：8000
                    coro=asyncio.start_server(tcpRemoteListen, '127.0.0.1', port1, loop=loop)
                    server = loop.run_until_complete(coro)
                    print('RemoteListen serving on {}'.format(server.sockets[0].getsockname()))
                    loop.run_forever()
                    server.close()
                    loop.run_until_complete(server.wait_closed())
                    loop.close()
                 except:
                    print("Something Wrong")
            else:
                  print("Input Wrong")
    elif 'slave' in sys.argv:
        if '-r' in sys.argv:
            index = sys.argv.index('-r')
            try:
                address1 = str(sys.argv[index + 1])
                ip1 = address1.split(':', 2)
                user = str(sys.argv[index + 3])
                port = str(sys.argv[index + 5])
                address2 = str(sys.argv[index + 7])
                ip2 = address2.split(':', 2)
                loop = asyncio.get_event_loop()
                loop.run_until_complete(tcpslave(user, ip1, port,ip2, loop))
                loop.close()
            except:
                print("Something Wrong")
        else:
             print("Input Wrong")

if __name__ == '__main__':
    main()
