# About MyLcx

## 关于协议设计和Packet

| Message Length | Command | Salt Length | Salt | Username Length | Username | Hash Length | Hash | Result | RequestID |
| :------------: | :-----: | :---------: | :--: | :-------------: | :------: | :---------: | :--: | :----: | :-------: |
|       h        |    b    |      b      | Var  |        b        |   Var    |      b      | Var  |   b    |     h     |

| ConnectionID | ListenPort | Data Length | Data |
| :----------: | :--------: | :---------: | :--: |
|      h       |     h      |      h      | Var  |

## 关于Command

**采用!网络字节序=big-endian**

|    c    |     1     |     2     |      3      |      4       |      5       |        6        |        7         |  8   |     9      |
| :-----: | :-------: | :-------: | :---------: | :----------: | :----------: | :-------------: | :--------------: | :--: | :--------: |
| Command | chap-salt | chap-hash | chap-result | bind-request | bind-reponse | connect-request | connect-response | data | disconnect |

## 关于命令行执行

有两种模式：listen模式和slave模式，终端运行即可

```
python MyLcx.py -m listen -p 8000 -u u1:p1,u2:p2
python MyLcx.py -m slave -r 127.0.0.1:8000 -u u1:p1 -p 8001 -l 127.0.0.1:8002
```

## 其他

KunchiLiu
2018/05/06

